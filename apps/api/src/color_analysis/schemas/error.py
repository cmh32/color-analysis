from typing import Literal

from pydantic import BaseModel

ApiErrorCode = Literal[
    "invalid_session",
    "session_not_found",
    "session_deleted",
    "insufficient_photos",
    "already_running",
    "already_complete",
    "result_not_ready",
    "forbidden",
    "invalid_request",
    "internal_error",
    "rate_limit_exceeded",
]


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    error_code: ApiErrorCode
