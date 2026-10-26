from collections.abc import Mapping
from typing import Any

import pytest

from system_one_triage.errors import SystemOneError
from system_one_triage.local import HeuristicSystemOne
from system_one_triage.questions import Answer, ChoiceAnswer, NoulAnswer, Question, ScoreAnswer
from system_one_triage.triage import Route, TriagePolicy, build_questions, decide, triage


def answers(
    *,
    category: str = "billing",
    confidence: float = 0.95,
    urgency: float = 1.0,
    security: float = 0.02,
    pii: float = 0.02,
) -> dict[str, Answer]:
    options = list(build_questions()["category"].options)  # type: ignore[union-attr]
    rest = (1 - confidence) / (len(options) - 1)
    return {
        "category": ChoiceAnswer(
            category, {o: (confidence if o == category else rest) for o in options}, confidence
        ),
        "urgency": ScoreAnswer(urgency, {"0": 0.2, "1": 0.2, "2": 0.2, "3": 0.2, "4": 0.2}, 0.8, 4),
        "security_incident": NoulAnswer(security),
        "contains_pii": NoulAnswer(pii),
    }


def test_confident_low_risk_ticket_is_handled_automatically() -> None:
    decision = decide(answers(), TriagePolicy())
    assert decision.route is Route.AUTO
    assert decision.queue == "billing"


def test_security_incident_is_never_automated_even_when_category_is_confident() -> None:
    decision = decide(answers(security=0.8, category="bug"), TriagePolicy())
    assert decision.route is Route.SECURITY_ESCALATION
    assert decision.queue == "security"
    assert decision.priority >= 0.9


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"confidence": 0.5}, "low_category_confidence"),
        ({"category": "other", "confidence": 0.9}, "unclassified"),
    ],
)
def test_uncertain_or_unclassified_tickets_go_to_the_agent(
    kwargs: dict[str, Any], reason: str
) -> None:
    decision = decide(answers(**kwargs), TriagePolicy())
    assert decision.route is Route.SYSTEM_TWO
    assert reason in decision.reasons


def test_confidence_threshold_is_a_coefficient_not_a_prompt() -> None:
    borderline = answers(confidence=0.75)
    assert decide(borderline, TriagePolicy(min_category_confidence=0.7)).route is Route.AUTO
    assert decide(borderline, TriagePolicy(min_category_confidence=0.9)).route is Route.SYSTEM_TWO


def test_priority_is_the_weighted_combination_computed_in_code() -> None:
    a = answers(urgency=4.0, security=0.2)
    assert decide(
        a, TriagePolicy(urgency_weight=0.7, security_weight=0.3)
    ).priority == pytest.approx(0.76)
    assert decide(
        a, TriagePolicy(urgency_weight=0.5, security_weight=0.0)
    ).priority == pytest.approx(0.5)


def test_pii_is_flagged_without_changing_the_route() -> None:
    decision = decide(answers(pii=0.9), TriagePolicy())
    assert decision.contains_pii is True
    assert decision.route is Route.AUTO


class BrokenClient:
    async def evaluate(
        self, state: str | Mapping[str, Any], questions: Mapping[str, Question]
    ) -> dict[str, Answer]:
        raise SystemOneError("System One returned HTTP 503")


async def test_when_system_one_is_down_work_falls_back_to_the_agent() -> None:
    decision = await triage("anything", BrokenClient())
    assert decision.route is Route.SYSTEM_TWO
    assert decision.reasons == ("system_one_unavailable",)
    assert decision.queue is None


@pytest.mark.parametrize(
    ("text", "route", "queue"),
    [
        ("I was charged twice, please refund the invoice", Route.AUTO, "billing"),
        ("Our API crashes with an exception on every call", Route.AUTO, "bug"),
        (
            "We think credentials were leaked, unauthorized logins",
            Route.SECURITY_ESCALATION,
            "security",
        ),
        ("hello there", Route.SYSTEM_TWO, None),
    ],
)
async def test_offline_stand_in_end_to_end(text: str, route: Route, queue: str | None) -> None:
    decision = await triage(text, HeuristicSystemOne())
    assert decision.route is route
    assert decision.queue == queue


async def test_structured_state_and_pii_detection() -> None:
    state = {"subject": "Refund", "body": "invoice wrong, reach me at ana@example.com"}
    decision = await triage(state, HeuristicSystemOne())
    assert decision.contains_pii is True
    assert decision.queue == "billing"
