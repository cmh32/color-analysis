import uuid

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from color_analysis.db.models.aggregated_feature import AggregatedFeature
from color_analysis.db.models.analysis_session import AnalysisSession
from color_analysis.db.models.audit_trace import AuditTrace
from color_analysis.db.models.classification import Classification
from color_analysis.db.models.extracted_feature import ExtractedFeature
from color_analysis.db.models.photo import Photo
from color_analysis.db.models.photo_quality import PhotoQuality
from color_analysis.schemas.analysis import AnalyzeResponse, StatusResponse
from color_analysis.storage.redis import RedisQueue


class AnalysisService:
    def __init__(self, db: AsyncSession, redis: RedisQueue) -> None:
        self.db = db
        self.redis = redis

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

        return StatusResponse(status=session.status, result_state=session.result_state)

    async def get_classification(self, session_id: uuid.UUID) -> Classification | None:
        query = select(Classification).where(Classification.session_id == session_id)
        return await self.db.scalar(query)

    async def clear_results(self, session_id: uuid.UUID) -> None:
        photo_ids = select(Photo.id).where(Photo.session_id == session_id)
        await self.db.execute(delete(PhotoQuality).where(PhotoQuality.photo_id.in_(photo_ids)))
        await self.db.execute(delete(ExtractedFeature).where(ExtractedFeature.photo_id.in_(photo_ids)))
        await self.db.execute(delete(AggregatedFeature).where(AggregatedFeature.session_id == session_id))
        await self.db.execute(delete(Classification).where(Classification.session_id == session_id))
        await self.db.execute(delete(AuditTrace).where(AuditTrace.session_id == session_id))
        await self.db.commit()
