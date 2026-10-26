"""Atomic questions in, routing decision out. All weighting and thresholds live in this file.

Each question is one gut-check on the same state, answered in parallel by a single System One
request. Combining them (priority, routing) is ordinary code, so changing behaviour means
changing a coefficient or threshold here, not rewriting a prompt.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, TypeVar

from system_one_triage.client import SystemOneClient
from system_one_triage.errors import SystemOneError
from system_one_triage.questions import (
    Answer,
    Choice,
    ChoiceAnswer,
    Noul,
    NoulAnswer,
    Question,
    Score,
    ScoreAnswer,
)

T = TypeVar("T", ChoiceAnswer, ScoreAnswer, NoulAnswer)

CATEGORIES = {
    "billing": "Charges, invoices, refunds, plans",
    "bug": "Something in the product is broken or erroring",
    "how_to": "A question about how to use the product",
    "account_access": "Cannot log in, locked out, password or 2FA problems",
    "other": "None of the above, or unclear",
}
URGENCY_LEVELS = (
    "No time pressure",
    "Minor inconvenience",
    "Blocks the customer's work",
    "Business-critical impact",
    "Production outage or data loss",
)


def build_questions() -> dict[str, Question]:
    return {
        "category": Choice("Which category best describes this support ticket?", CATEGORIES),
        "urgency": Score("How urgent is this ticket for the customer?", URGENCY_LEVELS),
        "security_incident": Noul(
            "The ticket reports or suggests a security incident such as a breach, leaked "
            "credentials, phishing or unauthorized access."
        ),
        "contains_pii": Noul(
            "The ticket text contains personal data such as an email address, government id "
            "or payment card number."
        ),
    }


class Route(StrEnum):
    AUTO = "auto"  # confident, low-risk: hand to the category queue without an LLM
    SYSTEM_TWO = "system_two"  # needs reasoning: hand to the ADK agent
    SECURITY_ESCALATION = "security_escalation"  # never automated: page the security on-call


@dataclass(frozen=True)
class TriagePolicy:
    min_category_confidence: float = 0.7
    security_threshold: float = 0.5
    pii_threshold: float = 0.5
    # priority = urgency_weight * urgency (0..1) + security_weight * P(security incident)
    urgency_weight: float = 0.7
    security_weight: float = 0.3


@dataclass(frozen=True)
class Decision:
    route: Route
    queue: str | None
    priority: float
    contains_pii: bool
    reasons: tuple[str, ...]
    facts: Mapping[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return {
            "route": self.route.value,
            "queue": self.queue,
            "priority": round(self.priority, 3),
            "contains_pii": self.contains_pii,
            "reasons": list(self.reasons),
            "facts": dict(self.facts),
        }


async def triage(
    state: str | Mapping[str, Any],
    client: SystemOneClient,
    policy: TriagePolicy | None = None,
) -> Decision:
    policy = policy or TriagePolicy()
    try:
        answers = await client.evaluate(state, build_questions())
    except SystemOneError as exc:
        # Fail safe: when the fast model is unavailable or unreadable, never auto-handle.
        return Decision(
            Route.SYSTEM_TWO, None, 0.5, False, ("system_one_unavailable",), {"error": str(exc)}
        )
    return decide(answers, policy)


def decide(answers: Mapping[str, Answer], policy: TriagePolicy) -> Decision:
    category = _expect(answers["category"], ChoiceAnswer)
    urgency = _expect(answers["urgency"], ScoreAnswer)
    security = _expect(answers["security_incident"], NoulAnswer)
    pii = _expect(answers["contains_pii"], NoulAnswer)

    urgency_fraction = urgency.score / urgency.top
    priority = policy.urgency_weight * urgency_fraction + policy.security_weight * security.noul
    contains_pii = pii.noul >= policy.pii_threshold
    facts = {
        "category": category.choice,
        "category_confidence": round(category.confidence, 3),
        "urgency": round(urgency.score, 2),
        "security_incident": round(security.noul, 3),
        "contains_pii": round(pii.noul, 3),
    }

    if security.noul >= policy.security_threshold:
        return Decision(
            Route.SECURITY_ESCALATION,
            "security",
            max(priority, 0.9),
            contains_pii,
            ("security_incident_suspected",),
            facts,
        )
    reasons: list[str] = []
    if category.confidence < policy.min_category_confidence:
        reasons.append("low_category_confidence")
    if category.choice == "other":
        reasons.append("unclassified")
    if reasons:
        return Decision(Route.SYSTEM_TWO, None, priority, contains_pii, tuple(reasons), facts)
    return Decision(
        Route.AUTO, category.choice, priority, contains_pii, ("confident_category",), facts
    )


def _expect(answer: Answer, kind: type[T]) -> T:
    if not isinstance(answer, kind):
        raise SystemOneError(f"expected {kind.__name__}, got {type(answer).__name__}")
    return answer


__all__ = ["Decision", "Question", "Route", "TriagePolicy", "build_questions", "decide", "triage"]
