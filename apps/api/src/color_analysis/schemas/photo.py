from typing import Literal

from pydantic import BaseModel, Field

PhotoRejectionReason = Literal[
    "session_not_pending",
    "photo_limit_exceeded",
    "invalid_filename",
    "unsupported_mime_type",
]


class PhotoRegisterRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=64)
    size_bytes: int = Field(gt=0, le=25_000_000)


class PhotoRegisterResponse(BaseModel):
    id: str
    accepted: bool
    reasons: list[PhotoRejectionReason]
    upload_url: str | None = None
    upload_fields: dict[str, str] | None = None
