from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings. Secrets are never printed by this class."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "local"
    log_level: str = "INFO"
    api_key: str = Field(default="change-me", repr=False)
    model_name: str = "gemini-2.5-flash"
    otel_service_name: str = "agentverse-api"
    otel_exporter_otlp_endpoint: str | None = None
    max_request_bytes: int = Field(default=10_485_760, ge=1024, le=52_428_800)
    rag_top_k: int = Field(default=5, ge=1, le=50)
    rag_min_score: float = Field(default=0.15, ge=0.0, le=1.0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
