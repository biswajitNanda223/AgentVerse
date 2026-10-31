from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class DecisionRagSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="DECISION_RAG_", extra="ignore")

    # "local" is an offline lexical stand-in; "jev" calls TypeSafe's hosted decision model.
    backend: Literal["local", "jev"] = "local"
    judgement: Literal["joint", "independent"] = "joint"
    api_key: SecretStr | None = Field(default=None, repr=False)
    base_url: str = "https://api.typesafe.ai"
    model: str = "jev-latest"
    timeout_seconds: float = Field(default=10.0, gt=0, le=120)
    agent_model: str = "gemini-2.5-flash"
    corpus_dir: str | None = None  # Markdown folder; unset uses the built-in sample corpus

    beam_width: int = Field(default=3, ge=1, le=20)
    min_probability: float = Field(default=0.2, ge=0, le=1)
    abstain_below: float = Field(default=0.3, ge=0, le=1)
    max_candidates_per_call: int = Field(default=40, ge=2, le=500)
    top_k: int = Field(default=3, ge=1, le=20)


@lru_cache
def get_settings() -> DecisionRagSettings:
    return DecisionRagSettings()
