import logging
from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="COLOR_ANALYSIS_")

    app_env: str = "development"
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    postgres_dsn: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/color_analysis"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_region: str = "us-east-1"
    s3_bucket: str = "color-analysis"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin"

    cors_allowed_origins: list[str] = Field(default=["http://localhost:3000"])
    admin_trace_token: str = Field(default="dev-admin-token", repr=False)

    max_photo_uploads: int = 15
    min_photo_uploads: int = 6
    photo_ttl_hours: int = 24
    thumbnail_ttl_days: int = 7

    @field_validator("admin_trace_token", mode="after")
    @classmethod
    def warn_insecure_admin_token(cls, v: str) -> str:
        if v == "dev-admin-token":
            logger.warning(
                "COLOR_ANALYSIS_ADMIN_TRACE_TOKEN is using the insecure default. "
                "Set it to a secret value in production."
            )
        return v


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
