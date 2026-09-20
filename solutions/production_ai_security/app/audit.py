from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class AuditEvent:
    sequence: int
    timestamp: str
    event_type: str
    actor: str
    tenant_id: str
    details: dict[str, Any]
    previous_hash: str
    event_hash: str


class AuditLog:
    """Append-only, hash-chained audit log suitable for exporting to durable storage."""

    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(
        self,
        event_type: str,
        *,
        actor: str,
        tenant_id: str,
        details: dict[str, Any],
    ) -> AuditEvent:
        previous_hash = self._events[-1].event_hash if self._events else "GENESIS"
        sequence = len(self._events) + 1
        timestamp = datetime.now(UTC).isoformat()
        payload = json.dumps(
            {
                "sequence": sequence,
                "timestamp": timestamp,
                "event_type": event_type,
                "actor": actor,
                "tenant_id": tenant_id,
                "details": details,
                "previous_hash": previous_hash,
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        event_hash = hashlib.sha256(payload.encode()).hexdigest()
        event = AuditEvent(
            sequence,
            timestamp,
            event_type,
            actor,
            tenant_id,
            details,
            previous_hash,
            event_hash,
        )
        self._events.append(event)
        return event

    def for_tenant(self, tenant_id: str) -> tuple[AuditEvent, ...]:
        return tuple(event for event in self._events if event.tenant_id == tenant_id)

    def verify_chain(self) -> bool:
        previous_hash = "GENESIS"
        for event in self._events:
            payload = asdict(event)
            event_hash = payload.pop("event_hash")
            encoded = json.dumps(
                payload, sort_keys=True, separators=(",", ":"), default=str
            ).encode()
            if event.previous_hash != previous_hash:
                return False
            if hashlib.sha256(encoded).hexdigest() != event_hash:
                return False
            previous_hash = event.event_hash
        return True
