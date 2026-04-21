import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status_code: int, title: str, detail: str, error_type: str) -> None:
        self.status_code = status_code
        self.title = title
        self.detail = detail
        self.error_type = error_type
        super().__init__(detail)


def _problem_response(status_code: int, title: str, detail: str, error_type: str) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        media_type="application/problem+json",
        content={
            "type": f"https://errors.color-analysis.local/{error_type}",
            "title": title,
            "status": status_code,
            "detail": detail,
        },
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return _problem_response(
            status_code=exc.status_code,
            title=exc.title,
            detail=exc.detail,
            error_type=exc.error_type,
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        first_error = exc.errors()[0] if exc.errors() else {}
        location = ".".join(str(part) for part in first_error.get("loc", []))
        message = str(first_error.get("msg", "Request payload is invalid"))
        detail = f"{message} ({location})" if location else message
        return _problem_response(
            status_code=422,
            title="Invalid Request",
            detail=detail,
            error_type="invalid_request",
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception for %s %s", request.method, request.url.path, exc_info=exc)
        return _problem_response(
            status_code=500,
            title="Internal Server Error",
            detail="Unexpected server error. Please retry.",
            error_type="internal_error",
        )
