import json

import httpx
import pytest
from pydantic import SecretStr

from decision_rag.jev import JevDecisionModel
from decision_rag.models import Candidate, DecisionModelError

CANDIDATES = [Candidate(f"id{i}", f"T{i}", f"text {i}", 1) for i in range(3)]


def model(handler: httpx.MockTransport, mode: str = "joint") -> JevDecisionModel:
    return JevDecisionModel(SecretStr("sk-test"), mode=mode, transport=handler)  # type: ignore[arg-type]


def answer_all(request: httpx.Request) -> httpx.Response:
    questions = json.loads(request.content)["questions"]
    return httpx.Response(200, json={n: {"noul": 0.1 * (i + 1)} for i, n in enumerate(questions)})


async def test_joint_mode_is_one_request_with_one_noul_question_per_candidate() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return answer_all(request)

    scores = await model(httpx.MockTransport(handler)).judge("the query", CANDIDATES)
    assert len(seen) == 1
    body = json.loads(seen[0].content)
    assert seen[0].headers["authorization"] == "Bearer sk-test"
    assert str(seen[0].url) == "https://api.typesafe.ai/v1/systemone"
    assert body["state"]["query"] == "the query"
    assert list(body["state"]["candidates"]) == ["C0", "C1", "C2"]  # shared context
    assert {q["type"] for q in body["questions"].values()} == {"noul"}
    assert len(body["questions"]) == 3
    assert scores == pytest.approx([0.1, 0.2, 0.3])


async def test_independent_mode_sends_one_request_per_candidate_with_only_that_candidate() -> None:
    bodies: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        bodies.append(json.loads(request.content))
        return answer_all(request)

    scores = await model(httpx.MockTransport(handler), "independent").judge("q", CANDIDATES)
    assert len(bodies) == 3
    for body in bodies:
        assert len(body["state"]["candidates"]) == 1  # type: ignore[index]
    assert len(scores) == 3


async def test_accepts_answers_nested_and_the_probability_alias() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"answers": {"c0": {"probability": 0.7}}})

    assert await model(httpx.MockTransport(handler)).judge("q", CANDIDATES[:1]) == [0.7]


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(500, text="boom 4242"),
        httpx.Response(200, text="<html>"),
        httpx.Response(200, json=[]),
        httpx.Response(200, json={"c0": {"noul": 1.4}}),
        httpx.Response(200, json={"c0": {"noul": True}}),
        httpx.Response(200, json={"c0": {}}),
        httpx.Response(200, json={}),
    ],
)
async def test_bad_responses_fail_closed_without_leaking_the_body(response: httpx.Response) -> None:
    transport = httpx.MockTransport(lambda request: response)
    with pytest.raises(DecisionModelError) as info:
        await model(transport).judge("q", CANDIDATES[:1])
    assert "4242" not in str(info.value)


async def test_timeouts_become_decision_model_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(DecisionModelError, match="ReadTimeout"):
        await model(httpx.MockTransport(handler)).judge("q", CANDIDATES[:1])


async def test_no_candidates_makes_no_request() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("must not call the API")

    assert await model(httpx.MockTransport(handler)).judge("q", []) == []
