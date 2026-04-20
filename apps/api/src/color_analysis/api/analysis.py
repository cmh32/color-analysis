import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from color_analysis.api.deps import db_session_dep, get_session_or_404
from color_analysis.api.errors import ApiError
from color_analysis.core.analysis_service import AnalysisService
from color_analysis.core.result_formatter import format_result
from color_analysis.core.session_service import SessionService
from color_analysis.db.models.analysis_session import AnalysisSession
from color_analysis.schemas.analysis import AnalyzeRequest, AnalyzeResponse, AnalysisResult, StatusResponse

router = APIRouter(prefix="/v1/sessions/{session_id}", tags=["analysis"])


@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze(
    _: AnalyzeRequest,
    session: AnalysisSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(db_session_dep),
) -> AnalyzeResponse:
    session_service = SessionService(db)
    photos = await session_service.list_photos(session.id)
    if len(photos) < 6:
        raise ApiError(400, "Insufficient Photos", "At least 6 photos are required", "insufficient_photos")

    service = AnalysisService(db)
    return await service.enqueue(session)


@router.get("/status", response_model=StatusResponse)
async def status(
    session_id: str,
    session: AnalysisSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(db_session_dep),
) -> StatusResponse:
    del session
    parsed = uuid.UUID(session_id)
    service = AnalysisService(db)
    return await service.get_status(parsed)


@router.get("/result", response_model=AnalysisResult)
async def result(
    session_id: str,
    session: AnalysisSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(db_session_dep),
) -> AnalysisResult:
    del session
    parsed = uuid.UUID(session_id)
    service = AnalysisService(db)
    classification = await service.get_classification(parsed)
    if classification is None:
        raise ApiError(404, "Not Found", "Result not ready", "result_not_ready")

    return format_result(classification)
