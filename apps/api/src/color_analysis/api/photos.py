from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from color_analysis.api.deps import db_session_dep, get_session_or_404, r2_dep, redis_dep
from color_analysis.api.errors import DEFAULT_ERROR_RESPONSES
from color_analysis.config import get_settings
from color_analysis.core.session_service import SessionService
from color_analysis.db.models.analysis_session import AnalysisSession
from color_analysis.schemas.photo import PhotoRegisterRequest, PhotoRegisterResponse, PhotoRejectionReason
from color_analysis.storage.r2 import R2Client
from color_analysis.storage.redis import RedisQueue

router = APIRouter(prefix="/v1/sessions/{session_id}/photos", tags=["photos"])

_ALLOWED_MIME_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/heic", "image/heif"}


def _is_safe_filename(filename: str) -> bool:
    if not filename or filename in {".", ".."}:
        return False
    if any(char in filename for char in ("/", "\\")):
        return False
    return all(ord(char) >= 32 and ord(char) != 127 for char in filename)


@router.post(
    "",
    response_model=PhotoRegisterResponse,
    status_code=status.HTTP_201_CREATED,
    responses=DEFAULT_ERROR_RESPONSES,
)
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
    normalized_filename = payload.filename.strip()
    normalized_mime_type = payload.mime_type.strip().lower()

    reasons: list[PhotoRejectionReason] = []
    accepted = True

    if session.status != "pending":
        accepted = False
        reasons.append("session_not_pending")

    if len(photos) >= settings.max_photo_uploads:
        accepted = False
        reasons.append("photo_limit_exceeded")

    if not _is_safe_filename(normalized_filename):
        accepted = False
        reasons.append("invalid_filename")

    if normalized_mime_type not in _ALLOWED_MIME_TYPES:
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

    canonical_mime_type = "image/jpeg" if normalized_mime_type == "image/jpg" else normalized_mime_type
    photo = await service.add_photo(session, normalized_filename, canonical_mime_type, payload.size_bytes)
    try:
        presigned = r2.put_presigned_post(photo.storage_key)
        await db.commit()
    except Exception:
        await db.rollback()
        raise

    await db.refresh(photo)
    upload_url = str(presigned.get("url", ""))
    fields_raw = presigned.get("fields", {})
    upload_fields = {str(key): str(value) for key, value in fields_raw.items() if isinstance(key, str)}

    return PhotoRegisterResponse(
        id=str(photo.id), accepted=accepted, reasons=reasons, upload_url=upload_url, upload_fields=upload_fields
    )
