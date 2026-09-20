from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from solutions.production_ai_security.app.audit import AuditLog

_SECRET = re.compile(r"(?i)(api[_-]?key|password|authorization|secret)\s*[:=]")
_INJECTION = re.compile(r"(?i)ignore .*instructions|reveal .*prompt|exfiltrate")


@dataclass(frozen=True, slots=True)
class MemoryItem:
    memory_id: str
    tenant_id: str
    subject: str
    text: str
    source: str
    confidence: float
    created_at: datetime
    expires_at: datetime


class SecureMemory:
    """Tenant-scoped memory with write-time and read-time gates."""

    def __init__(self, audit: AuditLog) -> None:
        self._items: list[MemoryItem] = []
        self._audit = audit

    def remember(
        self,
        *,
        tenant_id: str,
        subject: str,
        text: str,
        source: str,
        confidence: float,
        ttl: timedelta = timedelta(days=7),
    ) -> MemoryItem:
        if confidence < 0.75:
            raise ValueError("memory confidence below write threshold")
        if _SECRET.search(text):
            raise ValueError("secrets must not be stored in agent memory")
        if _INJECTION.search(text):
            raise ValueError("untrusted instruction-like content rejected")
        now = datetime.now(UTC)
        item = MemoryItem(
            memory_id=f"mem-{len(self._items) + 1}",
            tenant_id=tenant_id,
            subject=subject,
            text=text.strip(),
            source=source,
            confidence=confidence,
            created_at=now,
            expires_at=now + ttl,
        )
        self._items.append(item)
        self._audit.append(
            "memory.written",
            actor=subject,
            tenant_id=tenant_id,
            details={"memory_id": item.memory_id, "source": source},
        )
        return item

    def recall(self, *, tenant_id: str, query: str, limit: int = 3) -> tuple[MemoryItem, ...]:
        now = datetime.now(UTC)
        query_terms = set(query.lower().split())
        candidates = [
            item
            for item in self._items
            if item.tenant_id == tenant_id
            and item.expires_at > now
            and item.confidence >= 0.75
            and query_terms.intersection(item.text.lower().split())
        ]
        candidates.sort(key=lambda item: (item.confidence, item.created_at), reverse=True)
        return tuple(candidates[:limit])

    def forget(self, *, tenant_id: str, subject: str) -> int:
        before = len(self._items)
        self._items = [
            item
            for item in self._items
            if not (item.tenant_id == tenant_id and item.subject == subject)
        ]
        removed = before - len(self._items)
        self._audit.append(
            "memory.forgotten",
            actor=subject,
            tenant_id=tenant_id,
            details={"removed": removed},
        )
        return removed
