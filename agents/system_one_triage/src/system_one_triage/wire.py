"""The only module that knows the JSON shape of the System One HTTP API.

CONTRACT STATUS: the endpoint, bearer auth, `model`, `state`, `questions`, the `noul` type with
`instructions`, and answers keyed by question name are taken from TypeSafe's public docs. The
`criteria` field names for choice (label -> description) and score (ordered list), and the
answer fields (`choice`, `score`, `noul`, `probabilities`, `confidence`), come from secondary
write-ups and must be confirmed against https://docs.typesafe.ai/api/system-one. If the real
shape differs, change this file and `tests/test_wire.py`; nothing else depends on it.

Decoding fails closed: any answer that does not match the question raises WireFormatError so the
router falls back to a safe path instead of acting on a misread value.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from system_one_triage.errors import WireFormatError
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

PROBABILITY_SUM_TOLERANCE = 0.05


def encode_request(
    model: str, state: str | Mapping[str, Any], questions: Mapping[str, Question]
) -> dict[str, Any]:
    encoded: dict[str, Any] = {}
    for name, question in questions.items():
        match question:
            case Choice():
                encoded[name] = {
                    "type": "choice",
                    "instructions": question.instructions,
                    "criteria": dict(question.options),
                }
            case Score():
                encoded[name] = {
                    "type": "score",
                    "instructions": question.instructions,
                    "criteria": list(question.levels),
                }
            case Noul():
                encoded[name] = {"type": "noul", "instructions": question.instructions}
    return {"model": model, "state": state, "questions": encoded}


def decode_response(payload: object, questions: Mapping[str, Question]) -> dict[str, Answer]:
    if not isinstance(payload, dict):
        raise WireFormatError("response is not a JSON object")
    answers = payload.get("answers", payload)  # some deployments nest under "answers"
    if not isinstance(answers, dict):
        raise WireFormatError("answers is not a JSON object")
    decoded: dict[str, Answer] = {}
    for name, question in questions.items():
        raw = answers.get(name)
        if not isinstance(raw, dict):
            raise WireFormatError(f"missing answer for question {name!r}")
        try:
            decoded[name] = _decode_one(raw, question)
        except (KeyError, TypeError, ValueError) as exc:
            raise WireFormatError(f"invalid answer for {name!r}: {exc}") from exc
    return decoded


def _unit(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError(f"{field} is not a number")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{field} must be within 0..1")
    return number


def _distribution(raw: object, allowed: set[str]) -> dict[str, float]:
    if not isinstance(raw, dict) or not raw:
        raise ValueError("probabilities missing")
    unknown = set(raw) - allowed
    if unknown:
        raise ValueError(f"probabilities for unknown labels: {sorted(unknown)}")
    probabilities = {str(label): _unit(value, "probability") for label, value in raw.items()}
    if abs(sum(probabilities.values()) - 1.0) > PROBABILITY_SUM_TOLERANCE:
        raise ValueError("probabilities do not sum to 1")
    return probabilities


def _decode_one(raw: dict[str, Any], question: Question) -> Answer:
    match question:
        case Choice():
            choice = raw["choice"]
            if choice not in question.options:
                raise ValueError(f"unknown option {choice!r}")
            return ChoiceAnswer(
                choice=choice,
                probabilities=_distribution(raw["probabilities"], set(question.options)),
                confidence=_unit(raw["confidence"], "confidence"),
            )
        case Score():
            top = len(question.levels) - 1
            score = raw["score"]
            if isinstance(score, bool) or not isinstance(score, int | float):
                raise ValueError("score is not a number")
            if not math.isfinite(score) or not -1e-6 <= score <= top + 1e-6:
                raise ValueError(f"score must be within 0..{top}")
            allowed = {str(i) for i in range(top + 1)} | set(question.levels)
            return ScoreAnswer(
                score=float(score),
                probabilities=_distribution(raw["probabilities"], allowed),
                confidence=_unit(raw["confidence"], "confidence"),
                top=top,
            )
        case Noul():
            value = raw["noul"] if "noul" in raw else raw["probability"]  # gateway alias
            confidence = raw.get("confidence")
            return NoulAnswer(
                noul=_unit(value, "noul"),
                confidence=None if confidence is None else _unit(confidence, "confidence"),
            )
