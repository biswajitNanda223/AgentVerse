"""Offline stand-in for System One so the example runs with no key or network.

It is a keyword heuristic, NOT Jev: it only understands the four question names used by
`triage.build_questions()` and its probabilities are not calibrated. It exists to exercise the
routing code and tests deterministically. Use `JevHttpClient` for real decisions.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

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

CATEGORY_WORDS: dict[str, tuple[str, ...]] = {
    "billing": ("invoice", "charge", "refund", "payment", "billing", "subscription"),
    "bug": ("error", "crash", "bug", "broken", "exception", "fails", "failing"),
    "how_to": ("how do i", "how to", "where can i", "is it possible", "documentation"),
    "account_access": ("password", "login", "log in", "locked", "2fa", "sign in"),
}
URGENT_WORDS = ("outage", "down", "urgent", "asap", "production", "data loss", "cannot", "can't")
SECURITY_WORDS = ("breach", "leaked", "unauthorized", "compromised", "phishing", "stolen")
PII = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+|\b\d{3}-\d{2}-\d{4}\b|\b(?:\d[ -]?){13,16}\b")


def _text(state: str | Mapping[str, Any]) -> str:
    return (state if isinstance(state, str) else " ".join(map(str, state.values()))).lower()


def _normalise(weights: Mapping[str, float]) -> dict[str, float]:
    total = sum(weights.values())
    return {label: value / total for label, value in weights.items()}


class HeuristicSystemOne:
    async def evaluate(
        self, state: str | Mapping[str, Any], questions: Mapping[str, Question]
    ) -> dict[str, Answer]:
        text = _text(state)
        return {name: self._answer(name, question, text) for name, question in questions.items()}

    def _answer(self, name: str, question: Question, text: str) -> Answer:
        match (name, question):
            case ("category", Choice()):
                hits = {
                    label: float(sum(word in text for word in CATEGORY_WORDS.get(label, ())))
                    for label in question.options
                }
                probabilities = _normalise({k: v + 0.1 for k, v in hits.items()})
                best = max(probabilities, key=lambda k: probabilities[k])
                if max(hits.values()) == 0:
                    best = "other" if "other" in probabilities else best
                return ChoiceAnswer(best, probabilities, probabilities[best])
            case ("urgency", Score()):
                top = len(question.levels) - 1
                level = min(top, 1 + sum(word in text for word in URGENT_WORDS))
                weights = {str(i): 0.05 for i in range(top + 1)}
                weights[str(level)] = 0.8
                probabilities = _normalise(weights)
                return ScoreAnswer(float(level), probabilities, probabilities[str(level)], top)
            case ("security_incident", Noul()):
                return NoulAnswer(0.95 if any(w in text for w in SECURITY_WORDS) else 0.03)
            case ("contains_pii", Noul()):
                return NoulAnswer(0.9 if PII.search(text) else 0.05)
        raise SystemOneError(f"stand-in does not know question {name!r}")
