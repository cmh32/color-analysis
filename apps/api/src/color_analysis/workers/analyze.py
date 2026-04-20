import asyncio
import io
import uuid
from collections import defaultdict

from PIL import Image
from sqlalchemy import select

from color_analysis.cv.pipeline import run
from color_analysis.cv.types import PhotoInput
from color_analysis.db.base import SessionLocal
from color_analysis.db.models.aggregated_feature import AggregatedFeature
from color_analysis.db.models.analysis_session import AnalysisSession
from color_analysis.db.models.audit_trace import AuditTrace
from color_analysis.db.models.classification import Classification
from color_analysis.db.models.extracted_feature import ExtractedFeature
from color_analysis.db.models.photo import Photo
from color_analysis.db.models.photo_quality import PhotoQuality
from color_analysis.storage.r2 import R2Client


async def _run(session_id: str) -> None:
    parsed = uuid.UUID(session_id)
    r2 = R2Client()

    async with SessionLocal() as db:
        session_obj = await db.get(AnalysisSession, parsed)
        if session_obj is None:
            raise ValueError(f"Session not found: {session_id}")

        photo_rows = list(
            await db.scalars(select(Photo).where(Photo.session_id == parsed).order_by(Photo.created_at.asc()))
        )

        inputs: list[PhotoInput] = []
        for photo in photo_rows:
            try:
                payload = r2.get_object_bytes(photo.storage_key)
            except Exception:
                payload = b""
            inputs.append(PhotoInput(id=str(photo.id), filename=photo.filename, payload=payload))

        try:
            result = run(inputs)

            for photo in photo_rows:
                report = result.quality_reports.get(str(photo.id))
                if report is not None:
                    db.add(
                        PhotoQuality(
                            photo_id=photo.id,
                            accepted=report.accepted,
                            blur_score=report.blur_score,
                            exposure_score=report.exposure_score,
                            face_count=report.face_count,
                            yaw_degrees=report.yaw_degrees,
                            pitch_degrees=report.pitch_degrees,
                            reasons=", ".join(report.reasons),
                        )
                    )

            for feat in result.per_photo_features:
                db.add(
                    ExtractedFeature(
                        photo_id=uuid.UUID(feat.photo_id),
                        region=feat.region,
                        l_star=feat.l_star,
                        a_star=feat.a_star,
                        b_star=feat.b_star,
                        c_star=feat.c_star,
                        h_deg=feat.h_deg,
                        ita_deg=feat.ita_deg,
                    )
                )

            spread_acc: dict[str, list[float]] = defaultdict(list)
            for feat in result.per_photo_features:
                for metric in ("l_star", "a_star", "b_star", "c_star", "h_deg", "ita_deg"):
                    spread_acc[f"{feat.region}.{metric}"].append(getattr(feat, metric))

            for feature_name, feature_value in result.aggregated_features.items():
                vals = spread_acc.get(feature_name, [])
                spread = max(vals) - min(vals) if vals else 0.0
                db.add(
                    AggregatedFeature(
                        session_id=parsed,
                        feature_name=feature_name,
                        feature_value=feature_value,
                        spread=spread,
                    )
                )

            db.add(
                Classification(
                    session_id=parsed,
                    primary_season=result.classification.top_2[0],
                    secondary_season=result.classification.top_2[1],
                    scorecard={
                        "warmth": result.scorecard.warmth,
                        "value": result.scorecard.value,
                        "chroma": result.scorecard.chroma,
                        "contrast": result.scorecard.contrast,
                    },
                    probabilities=result.classification.probabilities,
                    reliability=result.reliability.score,
                    reliability_bucket=result.reliability.bucket,
                    result_state=result.result_state,
                )
            )

            db.add(
                AuditTrace(
                    session_id=parsed,
                    stage="pipeline",
                    payload={"trace": list(result.trace), "result_state": result.result_state},
                )
            )

            thumb_prefix = f"sessions/{session_id}/thumbnails"
            for photo in photo_rows:
                image = Image.new("RGB", (256, 256), color=(20, 120, 100))
                buff = io.BytesIO()
                image.save(buff, format="JPEG")
                r2.put_object_bytes(
                    key=f"{thumb_prefix}/{photo.id}.jpg",
                    payload=buff.getvalue(),
                    content_type="image/jpeg",
                )

            session_obj.status = "complete"
            session_obj.result_state = result.result_state
            session_obj.reliability = result.reliability.score
            session_obj.reliability_bucket = result.reliability.bucket
            await db.commit()
        except Exception:
            session_obj.status = "failed"
            session_obj.result_state = "failed"
            await db.commit()
            raise


def run_analysis(session_id: str) -> None:
    asyncio.run(_run(session_id))
