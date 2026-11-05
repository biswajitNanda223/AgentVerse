import copy

import pytest

from system_one_triage.errors import WireFormatError
from system_one_triage.questions import (
    ChoiceAnswer,
    NoulAnswer,
    ScoreAnswer,
)
from system_one_triage.triage import build_questions
from system_one_triage.wire import decode_response, encode_request

QUESTIONS = build_questions()


def good_payload() -> dict[str, object]:
    return {
        "category": {
            "choice": "bug",
            "probabilities": {
                "billing": 0.02,
                "bug": 0.9,
                "how_to": 0.02,
                "account_access": 0.03,
                "other": 0.03,
            },
            "confidence": 0.9,
        },
        "urgency": {
            "score": 3.2,
            "probabilities": {"0": 0.0, "1": 0.05, "2": 0.15, "3": 0.6, "4": 0.2},
            "confidence": 0.8,
        },
        "security_incident": {"type": "noul", "noul": 0.02},
        "contains_pii": {"type": "noul", "noul": 0.01},
    }


def test_encode_request_lists_every_question_with_its_type() -> None:
    body = encode_request("jev-latest", "ticket text", QUESTIONS)
    assert body["model"] == "jev-latest"
    assert body["state"] == "ticket text"
    q = body["questions"]
    assert q["category"]["type"] == "choice"
    assert set(q["category"]["criteria"]) == {"billing", "bug", "how_to", "account_access", "other"}
    assert q["urgency"]["type"] == "score"
    assert len(q["urgency"]["criteria"]) == 5
    assert q["security_incident"] == {
        "type": "noul",
        "instructions": QUESTIONS["security_incident"].instructions,  # type: ignore[union-attr]
    }


def test_decode_reads_all_three_question_types() -> None:
    answers = decode_response(good_payload(), QUESTIONS)
    assert isinstance(answers["category"], ChoiceAnswer)
    assert isinstance(answers["urgency"], ScoreAnswer)
    assert isinstance(answers["security_incident"], NoulAnswer)
    assert answers["urgency"].top == 4  # type: ignore[union-attr]


def test_decode_accepts_answers_nested_under_a_key_and_the_probability_alias() -> None:
    payload = good_payload()
    payload["security_incident"] = {"probability": 0.4}
    answers = decode_response({"answers": payload}, QUESTIONS)
    assert answers["security_incident"].noul == 0.4  # type: ignore[union-attr]


@pytest.mark.parametrize(
    "mutate",
    [
        lambda p: p.pop("urgency"),
        lambda p: p["category"].update(choice="refund"),
        lambda p: p["category"].update(confidence=1.4),
        lambda p: p["category"].update(probabilities={"bug": 0.5, "billing": 0.1}),
        lambda p: p["category"]["probabilities"].update(unknown=0.0),
        lambda p: p["urgency"].update(score=7),
        lambda p: p["urgency"].update(score="high"),
        lambda p: p["security_incident"].update(noul=1.5),
        lambda p: p["security_incident"].update(noul=True),
        lambda p: p["contains_pii"].update(noul=float("nan")),
    ],
)
def test_decode_fails_closed_on_bad_answers(mutate) -> None:  # type: ignore[no-untyped-def]
    payload = copy.deepcopy(good_payload())
    mutate(payload)
    with pytest.raises(WireFormatError):
        decode_response(payload, QUESTIONS)


@pytest.mark.parametrize("payload", [[], "ok", None, {"answers": []}])
def test_decode_rejects_non_object_payloads(payload: object) -> None:
    with pytest.raises(WireFormatError):
        decode_response(payload, QUESTIONS)
