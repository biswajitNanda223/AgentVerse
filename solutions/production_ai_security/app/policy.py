from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from solutions.production_ai_security.app.models import Identity, RiskLevel


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    requires_approval: bool
    reason: str


class PolicyEngine:
    """Deterministic authorization. The model never grants its own permissions."""

    def decide(
        self,
        identity: Identity,
        *,
        required_scope: str,
        risk: RiskLevel,
        arguments: dict[str, Any],
    ) -> PolicyDecision:
        if required_scope not in identity.scopes:
            return PolicyDecision(False, False, f"missing scope: {required_scope}")
        if risk is RiskLevel.IRREVERSIBLE_WRITE:
            return PolicyDecision(True, True, "irreversible side effect requires human approval")
        if risk is RiskLevel.REVERSIBLE_WRITE:
            amount = float(arguments.get("amount", 0))
            if amount >= 100:
                return PolicyDecision(True, True, "write exceeds autonomous limit")
        return PolicyDecision(True, False, "authorized by explicit scope and risk policy")
