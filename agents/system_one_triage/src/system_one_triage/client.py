from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from system_one_triage.errors import SystemOneError
from system_one_triage.http_client import JevHttpClient
from system_one_triage.local import HeuristicSystemOne
from system_one_triage.questions import Answer, Question
from system_one_triage.settings import TriageSettings


class SystemOneClient(Protocol):
    async def evaluate(
        self, state: str | Mapping[str, Any], questions: Mapping[str, Question]
    ) -> dict[str, Answer]: ...


def build_client(settings: TriageSettings) -> SystemOneClient:
    if settings.backend == "local":
        return HeuristicSystemOne()
    if settings.api_key is None:
        raise SystemOneError("SYSTEM_ONE_API_KEY is required when SYSTEM_ONE_BACKEND=jev")
    return JevHttpClient(
        settings.api_key,
        base_url=settings.base_url,
        model=settings.model,
        timeout=settings.timeout_seconds,
    )
