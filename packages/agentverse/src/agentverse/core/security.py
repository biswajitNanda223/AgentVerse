import hashlib
import hmac
import re
from dataclasses import dataclass

_SECRET_PATTERN = re.compile(r"(?i)(api[_-]?key|authorization|password|secret)\s*[:=]\s*[^\s,;]+")


def constant_time_key_match(provided: str, expected: str) -> bool:
    """Compare credentials without an early-exit timing leak."""

    return bool(provided) and hmac.compare_digest(provided.encode(), expected.encode())


def redact(text: str, *, max_length: int = 2_000) -> str:
    """Best-effort log redaction; prevention at source remains mandatory."""

    bounded = text[:max_length]
    return _SECRET_PATTERN.sub(lambda m: f"{m.group(1)}=[REDACTED]", bounded)


def stable_tenant_key(tenant_id: str, value: str) -> str:
    """Build a cache/idempotency namespace that cannot collide across tenants."""

    return hashlib.sha256(f"{tenant_id}\0{value}".encode()).hexdigest()


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    tenant_id: str
    scopes: frozenset[str]

    def require(self, scope: str) -> None:
        if scope not in self.scopes:
            raise PermissionError(f"missing required scope: {scope}")
