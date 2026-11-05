from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class TriageSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="SYSTEM_ONE_", extra="ignore")

    # "local" is an offline stand-in so the example runs with no key; "jev" calls TypeSafe.
    backend: Literal["local", "jev"] = "local"
    api_key: SecretStr | None = Field(default=None, repr=False)
    base_url: str = "https://api.typesafe.ai"
    model: str = "jev-latest"
    timeout_seconds: float = Field(default=5.0, gt=0, le=60)
    agent_model: str = "gemini-2.5-flash"


@lru_cache
def get_settings() -> TriageSettings:
    return TriageSettings()
