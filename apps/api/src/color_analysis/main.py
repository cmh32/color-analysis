from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from color_analysis.api.admin import router as admin_router
from color_analysis.api.analysis import router as analysis_router
from color_analysis.api.errors import problem_response_dict, register_error_handlers
from color_analysis.api.limiter import limiter
from color_analysis.api.photos import router as photos_router
from color_analysis.api.sessions import router as sessions_router
from color_analysis.config import get_settings
from color_analysis.storage.r2 import R2Client
from color_analysis.storage.redis import RedisQueue


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    app.state.r2 = R2Client()
    app.state.r2.ensure_bucket_exists()
    app.state.redis = RedisQueue()
    yield


app = FastAPI(title="Color Analysis API", version="0.1.0", lifespan=lifespan)
app.state.limiter = limiter


async def _rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    detail = str(exc.detail) if exc.detail else "Too many requests"
    return JSONResponse(
        status_code=429,
        media_type="application/problem+json",
        content=problem_response_dict(
            status_code=429,
            title="Too Many Requests",
            detail=detail,
            error_code="rate_limit_exceeded",
        ),
    )


app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_allowed_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_error_handlers(app)

app.include_router(sessions_router)
app.include_router(photos_router)
app.include_router(analysis_router)
app.include_router(admin_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
