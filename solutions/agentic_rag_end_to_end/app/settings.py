from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class SolutionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="E2E_", extra="ignore")

    api_key: str = Field(default="local-only", repr=False)
    model_name: str = "gemini-2.5-flash"
    max_agent_steps: int = Field(default=6, ge=1, le=20)
    retrieval_k: int = Field(default=5, ge=1, le=20)
    min_relevance: float = Field(default=0.12, ge=0, le=1)
    a2a_peer_url: str | None = None
    tool_timeout_seconds: float = Field(default=8.0, gt=0, le=60)


@lru_cache
def settings() -> SolutionSettings:
    return SolutionSettings()
