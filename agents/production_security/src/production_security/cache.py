from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class CacheEntry:
    value: Any
    expires_at: float


class TenantCache:
    """TTL cache whose keys include tenant, policy version, and source version."""

    def __init__(self, *, ttl_seconds: int = 300) -> None:
        self._ttl_seconds = ttl_seconds
        self._entries: dict[str, CacheEntry] = {}

    @staticmethod
    def key(
        tenant_id: str,
        purpose: str,
        value: str,
        *,
        policy_version: str,
        source_version: str,
    ) -> str:
        raw = "\0".join((tenant_id, purpose, value, policy_version, source_version))
        return hashlib.sha256(raw.encode()).hexdigest()

    def get(self, key: str) -> Any | None:
        entry = self._entries.get(key)
        if entry is None:
            return None
        if entry.expires_at <= time.monotonic():
            self._entries.pop(key, None)
            return None
        return entry.value

    def put(self, key: str, value: Any) -> None:
        self._entries[key] = CacheEntry(value, time.monotonic() + self._ttl_seconds)

    def invalidate_tenant(self, tenant_id: str) -> None:
        # Keys are intentionally opaque; production adapters maintain a tenant-key index.
        self._entries.clear()
