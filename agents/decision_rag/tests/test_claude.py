import json
from types import SimpleNamespace
from typing import Any

import pytest

from decision_rag.claude import ClaudeDecisionModel
from decision_rag.factory import build_model
from decision_rag.models import Candidate, DecisionModelError
from decision_rag.navigator import DecisionNavigator
from decision_rag.sample_corpus import sample_tree
from decision_rag.settings import DecisionRagSettings

CANDIDATES = [Candidate(f"id{i}", f"T{i}", f"text {i}", 1) for i in range(3)]


def reply(payload: object, stop_reason: str = "end_turn") -> SimpleNamespace:
    text = payload if isinstance(payload, str) else json.dumps(payload)
    return SimpleNamespace(
        stop_reason=stop_reason, content=[SimpleNamespace(type="text", text=text)]
    )


class FakeClient:
    """Stands in for anthropic.AsyncAnthropic: records requests, returns a canned reply."""

    def __init__(self, response: Any = None, error: Exception | None = None) -> None:
        self.requests: list[dict[str, Any]] = []
        self._response, self._error = response, error
        self.messages = SimpleNamespace(create=self._create)

    async def _create(self, **kwargs: Any) -> Any:
        self.requests.append(kwargs)
        if self._error:
            raise self._error
        return self._response


def scores(*values: float) -> dict[str, list[dict[str, float]]]:
    return {"scores": [{"candidate": i, "probability": v} for i, v in enumerate(values)]}


async def test_all_candidates_go_in_one_request_with_a_json_schema_and_low_effort() -> None:
    client = FakeClient(reply(scores(0.9, 0.1, 0.4)))
    model = ClaudeDecisionModel(client=client)
    assert await model.judge("the query", CANDIDATES) == [0.9, 0.1, 0.4]
    [request] = client.requests
    assert request["model"] == "claude-opus-5-5"
    assert request["output_config"]["effort"] == "low"
    assert request["output_config"]["format"]["type"] == "json_schema"
    prompt = request["messages"][0]["content"]
    assert "the query" in prompt and all(f"[{i}] text {i}" in prompt for i in range(3))
    assert "untrusted" in request["system"]
    assert "thinking" not in request and "tool_choice" not in request  # not valid on this model


async def test_scores_are_matched_by_candidate_number_not_order() -> None:
    shuffled = {
        "scores": [
            {"candidate": 2, "probability": 0.2},
            {"candidate": 0, "probability": 0.8},
            {"candidate": 1, "probability": 0.5},
        ]
    }
    model = ClaudeDecisionModel(client=FakeClient(reply(shuffled)))
    assert await model.judge("q", CANDIDATES) == [0.8, 0.5, 0.2]


@pytest.mark.parametrize(
    "bad",
    [
        reply("not json"),
        reply({"other": []}),
        reply({"scores": "x"}),
        reply(scores(0.5, 0.5)),  # missing a candidate
        reply({"scores": [{"candidate": 5, "probability": 0.5}] * 3}),  # unknown candidate
        reply({"scores": [{"candidate": 0, "probability": 0.5}] * 3}),  # scored twice
        reply(scores(0.5, 1.4, 0.2)),
        reply(scores(0.5, -0.1, 0.2)),
        reply(
            {
                "scores": [
                    {"candidate": 0, "probability": True},
                    {"candidate": 1, "probability": 0.1},
                    {"candidate": 2, "probability": 0.1},
                ]
            }
        ),
        reply({"scores": [{"candidate": 0}]}),
        reply(scores(0.5, 0.5, 0.5), stop_reason="refusal"),
        reply(scores(0.5, 0.5, 0.5), stop_reason="max_tokens"),
    ],
)
async def test_invalid_or_early_stopped_replies_fail_closed(bad: SimpleNamespace) -> None:
    with pytest.raises(DecisionModelError):
        await ClaudeDecisionModel(client=FakeClient(bad)).judge("q", CANDIDATES)


async def test_sdk_errors_become_decision_model_errors_without_leaking_the_prompt() -> None:
    client = FakeClient(error=RuntimeError("confidential-query-text"))
    with pytest.raises(DecisionModelError) as info:
        await ClaudeDecisionModel(client=client).judge("confidential-query-text", CANDIDATES)
    assert "confidential" not in str(info.value)
    assert "RuntimeError" in str(info.value)


async def test_no_candidates_makes_no_request() -> None:
    client = FakeClient(reply(scores()))
    assert await ClaudeDecisionModel(client=client).judge("q", []) == []
    assert client.requests == []


async def test_navigator_runs_end_to_end_with_a_claude_style_judge() -> None:
    """Score by id prefix through the fake client; the navigator must reach the right passage."""

    class Judge(FakeClient):
        async def _create(self, **kwargs: Any) -> Any:
            prompt = kwargs["messages"][0]["content"]
            lines = [line for line in prompt.splitlines() if line.startswith("[")]
            probs = [
                0.95 if "Dead-letter" in line or "dead-letter" in line else 0.05 for line in lines
            ]
            return reply(scores(*probs))

    model = ClaudeDecisionModel(client=Judge())
    result = await DecisionNavigator(sample_tree(), model).navigate("poison message")
    assert result.passages[0].node.id.startswith("messaging/dead-letter-queues/")


def test_factory_builds_the_claude_backend_without_credentials_until_first_use() -> None:
    model = build_model(DecisionRagSettings(backend="claude", claude_model="claude-sonnet-5-5"))
    assert isinstance(model, ClaudeDecisionModel)
