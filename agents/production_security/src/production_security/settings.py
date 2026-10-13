from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class SecuritySettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    api_key: str = "local-development-only"
    approval_signing_secret: str = "local-approval-secret-change-me-123456789"  # noqa: S105 - local-only default
    security_db_path: str = "security.db"
    postgres_dsn: str = "postgresql://agentverse:agentverse@localhost:5432/agentverse"
    redis_url: str = "redis://localhost:6379/0"
    model_name: str = "gemini-2.5-flash"


@lru_cache
def settings() -> SecuritySettings:
    return SecuritySettings()
