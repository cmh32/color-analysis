from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from color_analysis.api.admin import router as admin_router
from color_analysis.api.analysis import router as analysis_router
from color_analysis.api.errors import register_error_handlers
from color_analysis.api.photos import router as photos_router
from color_analysis.api.sessions import router as sessions_router
from color_analysis.config import get_settings

app = FastAPI(title="Color Analysis API", version="0.1.0")

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
