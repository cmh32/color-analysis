import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from color_analysis.schemas.error import ApiErrorCode, ProblemDetail

logger = logging.getLogger(__name__)

PROBLEM_DETAIL_RESPONSE: dict[str, object] = {
    "model": ProblemDetail,
    "description": "Error response with stable error_code for client handling.",
}

DEFAULT_ERROR_RESPONSES: dict[int, dict[str, object]] = {
    400: PROBLEM_DETAIL_RESPONSE,
    403: PROBLEM_DETAIL_RESPONSE,
    404: PROBLEM_DETAIL_RESPONSE,
    409: PROBLEM_DETAIL_RESPONSE,
    410: PROBLEM_DETAIL_RESPONSE,
    422: PROBLEM_DETAIL_RESPONSE,
    429: PROBLEM_DETAIL_RESPONSE,
    500: PROBLEM_DETAIL_RESPONSE,
}


class ApiError(Exception):
    def __init__(self, status_code: int, title: str, detail: str, error_code: ApiErrorCode) -> None:
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.error_code = error_code
        super().__init__(detail)


def problem_response_dict(
    *,
    status_code: int,
    title: str,
    detail: str,
    error_code: ApiErrorCode,
) -> dict[str, str | int]:
    payload = ProblemDetail(
        type=f"https://errors.color-analysis.local/{error_code}",
        title=title,
        status=status_code,
        detail=detail,
        error_code=error_code,
    )
    return payload.model_dump()


def problem_response(*, status_code: int, title: str, detail: str, error_code: ApiErrorCode) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content=problem_response_dict(
            status_code=status_code,
            title=title,
            detail=detail,
            error_code=error_code,
        ),
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return problem_response(
            status_code=exc.status_code,
            title=exc.title,
            detail=exc.detail,
            error_code=exc.error_code,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first_error = exc.errors()[0] if exc.errors() else {}
        location = ".".join(str(part) for part in first_error.get("loc", []))
        message = str(first_error.get("msg", "Request payload is invalid"))
        detail = f"{message} ({location})" if location else message
        return problem_response(
            status_code=422,
            title="Invalid Request",
            detail=detail,
            error_code="invalid_request",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception for %s %s", request.method, request.url.path, exc_info=exc)
        return problem_response(
            status_code=500,
            title="Internal Server Error",
            detail="Unexpected server error. Please retry.",
            error_code="internal_error",
        )
