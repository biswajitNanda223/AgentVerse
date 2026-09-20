from __future__ import annotations

import hashlib
import inspect
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from solutions.production_ai_security.app.models import RiskLevel

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
    registry.register(
        origin="com.agentverse.orders",
        name="read_orders",
        required_scope="orders:read",
        risk=RiskLevel.READ,
        handler=read_orders,
    )
    registry.register(
        origin="com.agentverse.customers",
        name="read_customer",
        required_scope="customers:read",
        risk=RiskLevel.READ,
        handler=read_customer,
    )
    registry.register(
        origin="com.agentverse.payments",
        name="issue_refund_lt_100",
        required_scope="refunds:write",
        risk=RiskLevel.IRREVERSIBLE_WRITE,
        handler=issue_refund_lt_100,
    )
    return registry
