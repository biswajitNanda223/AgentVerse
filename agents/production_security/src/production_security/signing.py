from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from dataclasses import asdict, dataclass
from typing import Any


def _encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode().rstrip("=")


def _decode(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


class SignedTokenService:
    """Issue short-lived HMAC tokens; use KMS-backed asymmetric keys in production."""

    def __init__(self, secret: str) -> None:
        if len(secret) < 32:
            raise ValueError("signing secret must be at least 32 characters")
        self._secret = secret.encode()

    def issue(self, claims: dict[str, Any], *, ttl_seconds: int = 300) -> str:
        payload = {**claims, "exp": int(time.time()) + ttl_seconds}
        encoded = _encode(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode())
        signature = _encode(hmac.new(self._secret, encoded.encode(), hashlib.sha256).digest())
        return f"{encoded}.{signature}"

    def verify(self, token: str) -> dict[str, Any]:
        try:
            encoded, supplied = token.split(".", maxsplit=1)
            expected = _encode(hmac.new(self._secret, encoded.encode(), hashlib.sha256).digest())
            if not hmac.compare_digest(supplied, expected):
                raise PermissionError("invalid token signature")
            claims = json.loads(_decode(encoded))
        except (ValueError, json.JSONDecodeError) as exc:
            raise PermissionError("malformed signed token") from exc
        if int(claims["exp"]) < int(time.time()):
            raise PermissionError("signed token expired")
        return dict(claims)


@dataclass(frozen=True, slots=True)
class ToolManifest:
    origin: str
    name: str
    version: str
    digest: str
    publisher: str


class ManifestVerifier:
    """Bind tool bytes to publisher, origin, name, and version."""

    def __init__(self, publisher_keys: dict[str, str]) -> None:
        self._publisher_keys = publisher_keys

    def sign(self, manifest: ToolManifest) -> str:
        key = self._publisher_keys[manifest.publisher].encode()
        payload = json.dumps(asdict(manifest), sort_keys=True, separators=(",", ":")).encode()
        return _encode(hmac.new(key, payload, hashlib.sha256).digest())

    def verify(self, manifest: ToolManifest, signature: str) -> bool:
        try:
            expected = self.sign(manifest)
        except KeyError:
            return False
        return hmac.compare_digest(expected, signature)
