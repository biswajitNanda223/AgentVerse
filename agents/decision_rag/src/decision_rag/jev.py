"""Decision model backed by TypeSafe's Jev (a System One model), one noul question per candidate.

Joint mode (default, the point of the technique): ONE request carries the query and every
candidate as the shared state, with one yes/no question per candidate. Independent mode sends
one request per candidate with only that candidate in context. It exists to measure how much
judging in a shared context helps on your data.

Only the `noul` question type is used, because it is the one documented by TypeSafe:
`{"type": "noul", "instructions": ...}` answered by a probability. Everything else about the
HTTP shape is in this file; see docs/jev-integration.md for what is and is not verified.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any, Literal

import httpx
from pydantic import SecretStr

from decision_rag.models import Candidate, DecisionModelError


class JevDecisionModel:
    def __init__(
        self,
        api_key: SecretStr,
        *,
        mode: Literal["joint", "independent"] = "joint",
        base_url: str = "https://api.typesafe.ai",
        model: str = "jev-latest",
        timeout: float = 10.0,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self._key = api_key
        self._mode = mode
        self._url = base_url.rstrip("/") + "/v1/systemone"
        self._model = model
        self._timeout = timeout
        self._transport = transport

    async def judge(self, query: str, candidates: Sequence[Candidate]) -> list[float]:
        if not candidates:
            return []
        if self._mode == "joint":
            return await self._request(query, candidates)
        scores: list[float] = []
        for candidate in candidates:
            scores.extend(await self._request(query, [candidate]))
        return scores

    async def _request(self, query: str, candidates: Sequence[Candidate]) -> list[float]:
        names = [f"c{i}" for i in range(len(candidates))]
        body: dict[str, Any] = {
            "model": self._model,
            "state": {
                "query": query,
                "candidates": {f"C{i}": c.text for i, c in enumerate(candidates)},
            },
            "questions": {
                name: {
                    "type": "noul",
                    "instructions": (
                        f"Candidate C{i} contains information needed to answer the query."
                    ),
                }
                for i, name in enumerate(names)
            },
        }
        headers = {
            "Authorization": f"Bearer {self._key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=self._timeout, transport=self._transport) as http:
                response = await http.post(self._url, json=body, headers=headers)
        except httpx.HTTPError as exc:
            raise DecisionModelError(f"transport error: {type(exc).__name__}") from exc
        if response.status_code != 200:
            raise DecisionModelError(f"decision model returned HTTP {response.status_code}")
        try:
            payload = response.json()
        except ValueError as exc:
            raise DecisionModelError("response is not valid JSON") from exc
        return _decode(payload, names)


def _decode(payload: object, names: list[str]) -> list[float]:
    if not isinstance(payload, dict):
        raise DecisionModelError("response is not a JSON object")
    answers = payload.get("answers", payload)
    if not isinstance(answers, dict):
        raise DecisionModelError("answers is not a JSON object")
    scores: list[float] = []
    for name in names:
        raw = answers.get(name)
        if not isinstance(raw, dict):
            raise DecisionModelError(f"missing answer for {name!r}")
        value = raw["noul"] if "noul" in raw else raw.get("probability")
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise DecisionModelError(f"answer for {name!r} is not a number")
        if not math.isfinite(value) or not 0 <= value <= 1:
            raise DecisionModelError(f"answer for {name!r} is outside 0..1")
        scores.append(float(value))
    return scores
