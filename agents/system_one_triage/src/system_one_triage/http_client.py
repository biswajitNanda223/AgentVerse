from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import httpx
from pydantic import SecretStr

from system_one_triage.errors import SystemOneError, WireFormatError
from system_one_triage.questions import Answer, Question
from system_one_triage.wire import decode_response, encode_request


class JevHttpClient:
    """Calls TypeSafe's hosted Jev: one request carries the state and every question."""

    def __init__(
        self,
        api_key: SecretStr,
        *,
        base_url: str = "https://api.typesafe.ai",
        model: str = "jev-latest",
        timeout: float = 5.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._key = api_key
        self._url = base_url.rstrip("/") + "/v1/systemone"
        self._model = model
        self._timeout = timeout
        self._transport = transport

    async def evaluate(
        self, state: str | Mapping[str, Any], questions: Mapping[str, Question]
    ) -> dict[str, Answer]:
        body = encode_request(self._model, state, questions)
        headers = {
            "Authorization": f"Bearer {self._key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as http:
                response = await http.post(self._url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            # Never include the request: the state may contain personal data.
            raise SystemOneError(f"transport error: {type(exc).__name__}") from exc
        if response.status_code != 200:
            raise SystemOneError(f"System One returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise WireFormatError("response is not valid JSON") from exc
        return decode_response(payload, questions)
