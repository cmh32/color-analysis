import uuid
from collections import Counter
from collections.abc import Iterable

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from color_analysis.config import get_settings
from color_analysis.cv.decode import decode_photo
from color_analysis.cv.landmarks import detect_landmarks
from color_analysis.cv.regions import build_overlay_regions
from color_analysis.cv.types import PhotoInput
from color_analysis.db.models.aggregated_feature import AggregatedFeature
from color_analysis.db.models.analysis_session import AnalysisSession
from color_analysis.db.models.audit_trace import AuditTrace
from color_analysis.db.models.classification import Classification
from color_analysis.db.models.extracted_feature import ExtractedFeature
from color_analysis.db.models.photo import Photo
from color_analysis.db.models.photo_quality import PhotoQuality
from color_analysis.schemas.analysis import (
    AnalyzeResponse,
    MeasurementOverlay,
    MeasurementPhoto,
    RejectedPhotoReview,
    RejectionSummaryItem,
    SessionReviewResponse,
    StatusResponse,
)
from color_analysis.storage.r2 import R2Client
from color_analysis.storage.redis import RedisQueue

_SUMMARY_ORDER = ("no_face_detected", "multiple_subjects", "blurry", "bad_exposure", "decode_failed")
_SUMMARY_STATES = {"insufficient_photos", "no_face_detected", "multiple_subjects"}


def _build_rejection_summary(rows: Iterable[PhotoQuality]) -> list[RejectionSummaryItem]:
    counts: Counter[str] = Counter()
    for row in rows:
        if row.accepted or not row.reasons:
            continue
        for reason in (part.strip() for part in row.reasons.split(",")):
            if reason in _SUMMARY_ORDER:
                counts[reason] += 1
    return [RejectionSummaryItem(code=code, count=counts[code]) for code in _SUMMARY_ORDER if counts[code] > 0]


class AnalysisService:
    def __init__(self, db: AsyncSession, redis: RedisQueue, r2: R2Client | None = None) -> None:
        self.db = db
        self.redis = redis
        self.r2 = r2

    async def enqueue(self, session: AnalysisSession) -> AnalyzeResponse:
        self.redis.enqueue_analysis(str(session.id))
        session.status = "running"
        await self.db.commit()
        return AnalyzeResponse(accepted=True)

    async def get_status(self, session_id: uuid.UUID) -> StatusResponse:
        query = select(AnalysisSession).where(AnalysisSession.id == session_id)
        session = await self.db.scalar(query)
        if session is None:
            return StatusResponse(status="failed", result_state="failed")

        rejection_summary: list[RejectionSummaryItem] | None = None
        if session.status == "complete" and session.result_state in _SUMMARY_STATES:
            photo_ids = select(Photo.id).where(Photo.session_id == session_id)
            rows = await self.db.scalars(
                select(PhotoQuality).where(PhotoQuality.photo_id.in_(photo_ids), PhotoQuality.accepted.is_(False))
            )
            rejection_summary = _build_rejection_summary(rows)

        return StatusResponse(
            status=session.status,
            result_state=session.result_state,
            rejection_summary=rejection_summary or None,
        )

    async def get_classification(self, session_id: uuid.UUID) -> Classification | None:
        query = select(Classification).where(Classification.session_id == session_id)
        return await self.db.scalar(query)

    async def get_aggregated_features(self, session_id: uuid.UUID) -> list[AggregatedFeature]:
        rows = await self.db.scalars(
            select(AggregatedFeature).where(AggregatedFeature.session_id == session_id)
        )
        return list(rows)

    async def get_measurement_photos(self, session: AnalysisSession) -> list[MeasurementPhoto]:
        if self.r2 is None:
            return []

        preview_ttl_seconds = get_settings().thumbnail_ttl_days * 24 * 60 * 60
        rows = (
            await self.db.execute(
                select(Photo, PhotoQuality)
                .join(PhotoQuality, PhotoQuality.photo_id == Photo.id)
                .where(Photo.session_id == session.id, PhotoQuality.accepted.is_(True))
                .order_by(Photo.created_at.asc())
            )
        ).all()

        photos: list[tuple[MeasurementPhoto, float, bool]] = []
        for photo, quality in rows:
            preview_key = f"sessions/{session.id}/thumbnails/{photo.id}.jpg"
            preview_url = self.r2.get_presigned_get_url(preview_key, expires_in_seconds=preview_ttl_seconds)
            overlays, width, height = self._build_measurement_overlays(photo, preview_key)
            score = (min(1.0, quality.blur_score / 120.0) * 0.6) + (quality.exposure_score * 0.4)
            photos.append(
                (
                    MeasurementPhoto(
                        photo_id=str(photo.id),
                        filename=photo.filename,
                        preview_url=preview_url,
                        width=width,
                        height=height,
                        is_default=False,
                        overlays=overlays,
                    ),
                    score,
                    bool(overlays),
                )
            )

        if not photos:
            return []

        default_index = next((idx for idx, (_, _, has_overlays) in enumerate(photos) if has_overlays), 0)
        for idx, (_, score, has_overlays) in enumerate(photos):
            if has_overlays and score > photos[default_index][1]:
                default_index = idx

        result: list[MeasurementPhoto] = []
        for idx, (photo, _, _) in enumerate(photos):
            result.append(photo.model_copy(update={"is_default": idx == default_index}))
        return result

    async def get_review(self, session: AnalysisSession) -> SessionReviewResponse:
        if self.r2 is None:
            raise RuntimeError("R2 client is required to build review preview URLs")

        preview_ttl_seconds = get_settings().thumbnail_ttl_days * 24 * 60 * 60
        query = (
            select(Photo, PhotoQuality)
            .join(PhotoQuality, PhotoQuality.photo_id == Photo.id)
            .where(Photo.session_id == session.id, PhotoQuality.accepted.is_(False))
            .order_by(Photo.created_at.asc())
        )
        rows = (await self.db.execute(query)).all()
        rejected_photos: list[RejectedPhotoReview] = []
        for photo, quality in rows:
            reasons = [reason.strip() for reason in quality.reasons.split(",") if reason.strip()]
            if not reasons:
                continue
            preview_key = photo.storage_key if "decode_failed" in reasons else f"sessions/{session.id}/thumbnails/{photo.id}.jpg"
            preview_url = self.r2.get_presigned_get_url(preview_key, expires_in_seconds=preview_ttl_seconds)
            rejected_photos.append(
                RejectedPhotoReview(
                    photo_id=str(photo.id),
                    filename=photo.filename,
                    reasons=reasons,
                    preview_url=preview_url,
                )
            )
        return SessionReviewResponse(rejected_photos=rejected_photos)

    def _build_measurement_overlays(
        self,
        photo: Photo,
        preview_key: str,
    ) -> tuple[list[MeasurementOverlay], int, int]:
        if self.r2 is None:
            return [], 256, 256
        try:
            payload = self.r2.get_object_bytes(preview_key)
            decoded = decode_photo(PhotoInput(id=str(photo.id), filename=photo.filename, payload=payload))
            detection = detect_landmarks(decoded)
            overlays = []
            if detection.landmarks is not None:
                overlays = [MeasurementOverlay(**item) for item in build_overlay_regions(decoded.rgb.shape, detection.landmarks)]
            return overlays, int(decoded.rgb.shape[1]), int(decoded.rgb.shape[0])
        except Exception:
            return [], 256, 256

    async def clear_results(self, session_id: uuid.UUID) -> None:
        photo_ids = select(Photo.id).where(Photo.session_id == session_id)
        await self.db.execute(delete(PhotoQuality).where(PhotoQuality.photo_id.in_(photo_ids)))
        await self.db.execute(delete(ExtractedFeature).where(ExtractedFeature.photo_id.in_(photo_ids)))
        await self.db.execute(delete(AggregatedFeature).where(AggregatedFeature.session_id == session_id))
        await self.db.execute(delete(Classification).where(Classification.session_id == session_id))
        await self.db.execute(delete(AuditTrace).where(AuditTrace.session_id == session_id))
        await self.db.commit()
