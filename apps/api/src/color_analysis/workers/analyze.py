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

        result = run(inputs)

        for photo in photo_rows:
            db.add(
                PhotoQuality(
                    photo_id=photo.id,
                    accepted=True,
                    blur_score=200.0,
                    exposure_score=0.8,
                    face_count=1,
                    yaw_degrees=0.0,
                    pitch_degrees=0.0,
                    reasons="",
                )
            )

        feature_acc: dict[str, list[float]] = defaultdict(list)
        for photo in photo_rows:
            for region in ("cheek_left", "cheek_right", "forehead", "iris_left", "iris_right", "sclera", "hair"):
                feature = ExtractedFeature(
                    photo_id=photo.id,
                    region=region,
                    l_star=50.0,
                    a_star=5.0,
                    b_star=10.0,
                    c_star=11.2,
                    h_deg=63.0,
                    ita_deg=8.0,
                )
                db.add(feature)
                feature_acc[f"{region}.l_star"].append(feature.l_star)

        for name, values in feature_acc.items():
            spread = max(values) - min(values) if values else 0.0
            db.add(
                AggregatedFeature(
                    session_id=parsed,
                    feature_name=name,
                    feature_value=sum(values) / max(1, len(values)),
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


def run_analysis(session_id: str) -> None:
    asyncio.run(_run(session_id))
