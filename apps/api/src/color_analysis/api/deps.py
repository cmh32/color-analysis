import hmac
import uuid
from collections.abc import AsyncGenerator

from fastapi import Depends, Header, Request
from sqlalchemy.ext.asyncio import AsyncSession

from color_analysis.api.errors import ApiError
from color_analysis.config import get_settings
from color_analysis.core.session_service import SessionService
from color_analysis.db.base import get_db_session
from color_analysis.db.models.analysis_session import AnalysisSession
from color_analysis.storage.r2 import R2Client
from color_analysis.storage.redis import RedisQueue


async def db_session_dep() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def r2_dep(request: Request) -> R2Client:
    return request.app.state.r2


def redis_dep(request: Request) -> RedisQueue:
    return request.app.state.redis


def require_admin_token(x_admin_token: str = Header(default="")) -> None:
    settings = get_settings()
    if not hmac.compare_digest(x_admin_token, settings.admin_trace_token):
        raise ApiError(403, "Forbidden", "Invalid admin token", "forbidden")


async def get_session_or_404(
    session_id: str,
    db: AsyncSession = Depends(db_session_dep),
) -> AnalysisSession:
    try:
        parsed = uuid.UUID(session_id)
    except ValueError as exc:
        raise ApiError(400, "Invalid Session", "Session ID is invalid", "invalid_session") from exc

    session_service = SessionService(db)
    session = await session_service.get_session_or_none(parsed)
    if session is None:
        raise ApiError(404, "Not Found", "Session not found", "session_not_found")
    return session
