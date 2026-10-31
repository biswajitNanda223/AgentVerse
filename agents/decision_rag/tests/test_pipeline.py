import json

from decision_rag.factory import build_model, build_pipeline
from decision_rag.local import LexicalDecisionModel
from decision_rag.mermaid import trace_to_mermaid
from decision_rag.models import DecisionModelError
from decision_rag.pipeline import DecisionRagPipeline
from decision_rag.sample_corpus import sample_tree
from decision_rag.settings import DecisionRagSettings
from decision_rag.testing import ScriptedModel


async def test_answers_with_the_best_passage_and_cited_paths() -> None:
    pipeline = DecisionRagPipeline(sample_tree(), LexicalDecisionModel())
    answer = await pipeline.answer("Which actions need human approval and an idempotency key?")
    assert not answer.abstained
    assert "explicit human approval" in answer.text
    assert answer.citations[0].path.startswith("Agents > Human approval > Risky actions")


async def test_abstains_instead_of_answering_from_weak_evidence() -> None:
    pipeline = DecisionRagPipeline(sample_tree(), ScriptedModel(lambda c: 0.1))
    answer = await pipeline.answer("what is the airspeed of a swallow")
    assert answer.abstained and answer.reason == "low_relevance"
    assert answer.citations == ()


async def test_decision_model_outage_fails_safe() -> None:
    class Down:
        async def judge(self, query, candidates):  # type: ignore[no-untyped-def]
            raise DecisionModelError("decision model returned HTTP 503")

    answer = await DecisionRagPipeline(sample_tree(), Down()).answer("q")
    assert answer.abstained
    assert answer.reason is not None and answer.reason.startswith("decision_model_unavailable")
    assert answer.navigation is None


async def test_mermaid_trace_is_valid_looking_and_marks_kept_pruned_and_answer_nodes() -> None:
    pipeline = DecisionRagPipeline(sample_tree(), LexicalDecisionModel())
    answer = await pipeline.answer("How do Kafka clients authenticate to Event Hubs?")
    assert answer.navigation is not None
    diagram = trace_to_mermaid(answer.navigation)
    assert diagram.startswith("flowchart TD")
    assert "4 joint judgments, 4 levels" in diagram
    for needle in ("classDef kept", "classDef pruned", "classDef answer", "p=0."):
        assert needle in diagram
    assert "-.->" in diagram and "-->" in diagram  # pruned edges dotted, kept edges solid
    assert (
        '"' not in diagram.split("flowchart TD\n", 1)[1].split("\n", 1)[0][14:-4]
    )  # query escaped


def test_jev_backend_requires_a_key() -> None:
    import pytest

    with pytest.raises(DecisionModelError, match="DECISION_RAG_API_KEY"):
        build_model(DecisionRagSettings(backend="jev", api_key=None))


async def test_agent_tool_returns_json_ready_evidence() -> None:
    from decision_rag.adk_agent import navigate_corpus, root_agent

    assert {t.__name__ for t in root_agent.tools} == {"navigate_corpus"}  # type: ignore[union-attr]
    result = await navigate_corpus("How do peers discover an A2A agent and delegate tasks?")
    json.dumps(result)
    assert result["abstained"] is False
    assert result["model_calls"] == 4
    assert "agent card" in result["evidence"].lower()


def test_pipeline_builds_from_settings_with_the_sample_corpus() -> None:
    assert isinstance(build_pipeline(DecisionRagSettings()), DecisionRagPipeline)


def test_http_endpoint_answers_traces_and_validates_input() -> None:
    from fastapi.testclient import TestClient

    from decision_rag.app import create_app
    from decision_rag.local import LexicalDecisionModel

    client = TestClient(create_app(DecisionRagPipeline(sample_tree(), LexicalDecisionModel())))
    ok = client.post(
        "/v1/ask", json={"query": "How do peers discover an A2A agent?", "trace": True}
    )
    assert ok.status_code == 200
    body = ok.json()
    assert body["abstained"] is False and body["model_calls"] == 4
    assert len(body["steps"]) == 4
    assert "steps" not in client.post("/v1/ask", json={"query": "A2A agent card"}).json()
    assert client.post("/v1/ask", json={"query": ""}).status_code == 422
    assert client.get("/health/live").status_code == 200
