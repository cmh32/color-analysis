import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from color_analysis.config import get_settings
from color_analysis.db.models.analysis_session import AnalysisSession
from color_analysis.db.models.audit_trace import AuditTrace
from color_analysis.db.models.classification import Classification
from color_analysis.db.models.photo import Photo
from color_analysis.storage.r2 import R2Client
from color_analysis.storage.redis import RedisQueue


class SessionService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()
        self.r2 = R2Client()
        self.redis = RedisQueue()

    async def create_session(self) -> AnalysisSession:
        session = AnalysisSession(
            id=uuid.uuid4(),
            status="pending",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=self.settings.photo_ttl_hours),
        )
        self.db.add(session)
        await self.db.commit()
        await self.db.refresh(session)
        return session

    async def get_session_or_none(self, session_id: uuid.UUID) -> AnalysisSession | None:
        query = select(AnalysisSession).where(AnalysisSession.id == session_id)
        return await self.db.scalar(query)

    async def add_photo(
        self,
        session: AnalysisSession,
        filename: str,
        mime_type: str,
        size_bytes: int,
    ) -> Photo:
        storage_key = f"sessions/{session.id}/photos/{uuid.uuid4()}-{filename}"
        photo = Photo(
            id=uuid.uuid4(),
            session_id=session.id,
            storage_key=storage_key,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
        )
        self.db.add(photo)
        await self.db.commit()
        await self.db.refresh(photo)
        return photo

    async def list_photos(self, session_id: uuid.UUID) -> list[Photo]:
        query = select(Photo).where(Photo.session_id == session_id)
        rows = await self.db.scalars(query)
        return list(rows)

    async def mark_deleted(self, session: AnalysisSession) -> None:
        session.status = "deleted"
        session.deleted_at = datetime.now(timezone.utc)
        await self.db.commit()

    async def hard_delete(self, session_id: uuid.UUID) -> None:
        photos = await self.list_photos(session_id)
        for photo in photos:
            try:
                self.r2.delete_object(photo.storage_key)
            except Exception:
                continue

        for key in self.r2.list_by_session_prefix(str(session_id)):
            try:
                self.r2.delete_object(key)
            except Exception:
                continue

        await self.db.execute(delete(Classification).where(Classification.session_id == session_id))
        await self.db.execute(delete(AuditTrace).where(AuditTrace.session_id == session_id))
        await self.db.execute(delete(Photo).where(Photo.session_id == session_id))
        await self.db.execute(delete(AnalysisSession).where(AnalysisSession.id == session_id))
        await self.db.commit()
        self.redis.delete_session_keys(str(session_id))

    async def sweep_expired_sessions(self) -> int:
        now = datetime.now(timezone.utc)
        query = select(AnalysisSession.id).where(AnalysisSession.expires_at <= now)
        expired_ids = [row for row in await self.db.scalars(query)]
        for session_id in expired_ids:
            await self.hard_delete(session_id)
        return len(expired_ids)
