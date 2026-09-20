from __future__ import annotations

import re
from collections.abc import Iterable

from solutions.production_ai_security.app.models import Evidence

_INJECTION = re.compile(r"(?i)ignore .*instructions|reveal .*prompt|system message|exfiltrate")


class SecureRetriever:
    """Retrieve, tenant-filter, injection-screen, rerank, dedupe, then cap context."""

    def __init__(self, evidence: Iterable[Evidence]) -> None:
        self._evidence = tuple(evidence)

    def search(
        self,
        query: str,
        *,
        tenant_id: str,
        min_score: float = 0.2,
        token_budget: int = 120,
    ) -> tuple[Evidence, ...]:
        terms = set(re.findall(r"\w+", query.lower()))
        ranked: list[Evidence] = []
        seen: set[str] = set()
        for item in self._evidence:
            if item.tenant_id != tenant_id or _INJECTION.search(item.text):
                continue
            words = set(re.findall(r"\w+", item.text.lower()))
            score = len(terms & words) / max(len(terms), 1)
            if score < min_score or item.text in seen:
                continue
            seen.add(item.text)
            ranked.append(
                Evidence(
                    item.document_id,
                    item.text,
                    item.source,
                    item.tenant_id,
                    score,
                    item.trusted,
                )
            )
        ranked.sort(key=lambda item: (item.score, item.trusted), reverse=True)
        selected: list[Evidence] = []
        used = 0
        for item in ranked:
            approximate_tokens = len(item.text.split())
            if used + approximate_tokens > token_budget:
                continue
            selected.append(item)
            used += approximate_tokens
        return tuple(selected)
