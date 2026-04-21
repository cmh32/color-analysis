from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from color_analysis.api.deps import db_session_dep, get_session_or_404, r2_dep, redis_dep
from color_analysis.config import get_settings
from color_analysis.core.session_service import SessionService
from color_analysis.db.models.analysis_session import AnalysisSession
from color_analysis.schemas.photo import PhotoRegisterRequest, PhotoRegisterResponse
from color_analysis.storage.r2 import R2Client
from color_analysis.storage.redis import RedisQueue

router = APIRouter(prefix="/v1/sessions/{session_id}/photos", tags=["photos"])


@router.post("", response_model=PhotoRegisterResponse, status_code=status.HTTP_201_CREATED)
async def register_photo(
    payload: PhotoRegisterRequest,
    session: AnalysisSession = Depends(get_session_or_404),
    db: AsyncSession = Depends(db_session_dep),
    r2: R2Client = Depends(r2_dep),
    redis: RedisQueue = Depends(redis_dep),
) -> PhotoRegisterResponse:
    service = SessionService(db, r2, redis)
    photos = await service.list_photos(session.id)
    settings = get_settings()

    reasons: list[str] = []
    accepted = True

    if len(photos) >= settings.max_photo_uploads:
        accepted = False
        reasons.append("photo_limit_exceeded")

    if payload.mime_type not in {"image/jpeg", "image/png", "image/heic", "image/heif"}:
        accepted = False
        reasons.append("unsupported_mime_type")

    if not accepted:
        return PhotoRegisterResponse(
            id="",
            accepted=False,
            reasons=reasons,
            upload_url=None,
            upload_fields=None,
        )

    photo = await service.add_photo(session, payload.filename, payload.mime_type, payload.size_bytes)
    presigned = r2.put_presigned_post(photo.storage_key)
    upload_url = str(presigned.get("url", ""))
    fields_raw = presigned.get("fields", {})
    upload_fields = {str(key): str(value) for key, value in fields_raw.items() if isinstance(key, str)}

    return PhotoRegisterResponse(
        id=str(photo.id), accepted=accepted, reasons=reasons, upload_url=upload_url, upload_fields=upload_fields
    )
