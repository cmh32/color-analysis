from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from color_analysis.api.deps import db_session_dep, get_session_or_404
from color_analysis.core.session_service import SessionService
from color_analysis.db.models.analysis_session import AnalysisSession
from color_analysis.schemas.session import SessionCreateResponse

router = APIRouter(prefix="/v1/sessions", tags=["sessions"])


@router.post("", response_model=SessionCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_session(db: AsyncSession = Depends(db_session_dep)) -> SessionCreateResponse:
    service = SessionService(db)
    session = await service.create_session()
    return SessionCreateResponse(id=str(session.id), status=session.status)


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_session(
    session: AnalysisSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(db_session_dep),
) -> Response:
    service = SessionService(db)
    await service.hard_delete(session.id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
