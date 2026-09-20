from __future__ import annotations

import hashlib
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from solutions.production_ai_security.app.models import RiskLevel
from solutions.production_ai_security.app.signing import ManifestVerifier, ToolManifest

ToolHandler = Callable[[dict[str, Any], bool], dict[str, Any]]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    origin: str
    name: str
    required_scope: str
    risk: RiskLevel
    handler: ToolHandler
    digest: str

    @property
    def tool_id(self) -> str:
        return f"{self.origin}::{self.name}"


class ToolRegistry:
    """Resolve tools by origin + name and verify code integrity before execution."""

    def __init__(self) -> None:
        self._tools: dict[tuple[str, str], ToolSpec] = {}

    @staticmethod
    def handler_digest(handler: ToolHandler) -> str:
        return hashlib.sha256(inspect.getsource(handler).encode()).hexdigest()

    def register(
        self,
        *,
        origin: str,
        name: str,
        required_scope: str,
        risk: RiskLevel,
        handler: ToolHandler,
    ) -> ToolSpec:
        key = (origin, name)
        if key in self._tools:
            raise ValueError(f"duplicate tool identity: {origin}::{name}")
        spec = ToolSpec(origin, name, required_scope, risk, handler, self.handler_digest(handler))
        self._tools[key] = spec
        return spec

    def register_signed(
        self,
        *,
        manifest: ToolManifest,
        signature: str,
        verifier: ManifestVerifier,
        required_scope: str,
        risk: RiskLevel,
        handler: ToolHandler,
    ) -> ToolSpec:
        if manifest.digest != self.handler_digest(handler):
            raise PermissionError("manifest digest does not match tool code")
        if not verifier.verify(manifest, signature):
            raise PermissionError("tool manifest signature rejected")
        return self.register(
            origin=manifest.origin,
            name=manifest.name,
            required_scope=required_scope,
            risk=risk,
            handler=handler,
        )

    def resolve(self, origin: str, name: str) -> ToolSpec:
        try:
            spec = self._tools[(origin, name)]
        except KeyError as exc:
            raise LookupError(f"unknown tool: {origin}::{name}") from exc
        if self.handler_digest(spec.handler) != spec.digest:
            raise PermissionError(f"integrity check failed: {spec.tool_id}")
        return spec


def read_orders(arguments: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    customer_id = str(arguments["customer_id"])
    return {
        "dry_run": dry_run,
        "orders": [{"order_id": "ord-100", "customer_id": customer_id, "total": 79.0}],
    }


def read_customer(arguments: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    return {
        "dry_run": dry_run,
        "customer": {"customer_id": str(arguments["customer_id"]), "status": "active"},
    }


def issue_refund_lt_100(arguments: dict[str, Any], dry_run: bool) -> dict[str, Any]:
    amount = float(arguments["amount"])
    if amount >= 100:
        raise ValueError("tool contract only permits refunds below 100")
    return {
        "dry_run": dry_run,
        "order_id": str(arguments["order_id"]),
        "amount": amount,
        "status": "preview" if dry_run else "refunded",
    }


def build_default_registry() -> ToolRegistry:
    registry = ToolRegistry()
    verifier = ManifestVerifier({"agentverse": "local-publisher-key-change-in-production"})
    definitions = (
        ("com.agentverse.orders", "read_orders", "orders:read", RiskLevel.READ, read_orders),
        (
            "com.agentverse.customers",
            "read_customer",
            "customers:read",
            RiskLevel.READ,
            read_customer,
        ),
        (
            "com.agentverse.payments",
            "issue_refund_lt_100",
            "refunds:write",
            RiskLevel.IRREVERSIBLE_WRITE,
            issue_refund_lt_100,
        ),
    )
    for origin, name, scope, risk, handler in definitions:
        manifest = ToolManifest(
            origin, name, "1.0.0", registry.handler_digest(handler), "agentverse"
        )
        registry.register_signed(
            manifest=manifest,
            signature=verifier.sign(manifest),
            verifier=verifier,
            required_scope=scope,
            risk=risk,
            handler=handler,
        )
    return registry
