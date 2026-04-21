from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from color_analysis.api.deps import db_session_dep, get_session_or_404, r2_dep, redis_dep
from color_analysis.api.errors import ApiError, DEFAULT_ERROR_RESPONSES
from color_analysis.core.analysis_service import AnalysisService
from color_analysis.core.result_formatter import format_result
from color_analysis.core.session_service import SessionService
from color_analysis.db.models.analysis_session import AnalysisSession
from color_analysis.schemas.analysis import AnalyzeRequest, AnalyzeResponse, AnalysisResult, StatusResponse
from color_analysis.storage.r2 import R2Client
from color_analysis.storage.redis import RedisQueue

router = APIRouter(prefix="/v1/sessions/{session_id}", tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse, responses=DEFAULT_ERROR_RESPONSES)
async def analyze(
    body: AnalyzeRequest,
    session: AnalysisSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(db_session_dep),
    r2: R2Client = Depends(r2_dep),
    redis: RedisQueue = Depends(redis_dep),
) -> AnalyzeResponse:
    session_service = SessionService(db, r2, redis)
    photos = await session_service.list_photos(session.id)
    if session.status == "deleted":
        raise ApiError(410, "Gone", "Session has been deleted", "session_deleted")
    if len(photos) < 6:
        raise ApiError(400, "Insufficient Photos", "At least 6 photos are required", "insufficient_photos")

    if session.status == "running":
        raise ApiError(409, "Conflict", "Analysis already in progress", "already_running")
    if session.status == "complete" and not body.force_recompute:
        raise ApiError(409, "Conflict", "Analysis already complete. Pass force_recompute=true to re-run.", "already_complete")

    service = AnalysisService(db, redis)
    if session.status == "complete":
        await service.clear_results(session.id)
    return await service.enqueue(session)


@router.get("/status", response_model=StatusResponse, responses=DEFAULT_ERROR_RESPONSES)
async def status(
    session_id: str,
    session: AnalysisSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(db_session_dep),
    redis: RedisQueue = Depends(redis_dep),
) -> StatusResponse:
    del session_id
    service = AnalysisService(db, redis)
    return await service.get_status(session.id)


@router.get("/result", response_model=AnalysisResult, responses=DEFAULT_ERROR_RESPONSES)
async def result(
    session_id: str,
    session: AnalysisSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(db_session_dep),
    redis: RedisQueue = Depends(redis_dep),
) -> AnalysisResult:
    del session_id
    service = AnalysisService(db, redis)
    classification = await service.get_classification(session.id)
    if classification is None:
        raise ApiError(404, "Not Found", "Result not ready", "result_not_ready")

    return format_result(classification)
