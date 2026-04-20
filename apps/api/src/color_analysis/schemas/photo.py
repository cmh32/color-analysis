from pydantic import BaseModel, Field


class PhotoRegisterRequest(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    mime_type: str = Field(min_length=1, max_length=64)
    size_bytes: int = Field(gt=0, le=25_000_000)


class PhotoRegisterResponse(BaseModel):
    id: str
    accepted: bool
    reasons: list[str]
    upload_url: str | None = None
    upload_fields: dict[str, str] | None = None
