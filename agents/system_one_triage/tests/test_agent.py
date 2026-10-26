import pytest

from system_one_triage.adk_agent import root_agent, triage_ticket
from system_one_triage.client import build_client
from system_one_triage.errors import SystemOneError
from system_one_triage.settings import TriageSettings


def test_agent_exposes_the_triage_tool_and_read_only_search() -> None:
    assert root_agent.name == "system_one_triage_agent"
    names = {tool.__name__ for tool in root_agent.tools}  # type: ignore[union-attr]
    assert names == {"triage_ticket", "search_knowledge"}


async def test_triage_tool_returns_a_json_ready_decision() -> None:
    result = await triage_ticket("I cannot log in, my password reset email never arrives")
    assert result["route"] in {"auto", "system_two", "security_escalation"}
    assert set(result) == {"route", "queue", "priority", "contains_pii", "reasons", "facts"}


def test_jev_backend_requires_an_api_key() -> None:
    with pytest.raises(SystemOneError, match="SYSTEM_ONE_API_KEY"):
        build_client(TriageSettings(backend="jev", api_key=None))


def test_http_endpoint_returns_a_decision_and_validates_input() -> None:
    from fastapi.testclient import TestClient

    from system_one_triage.app import create_app
    from system_one_triage.local import HeuristicSystemOne

    client = TestClient(create_app(HeuristicSystemOne()))
    ok = client.post("/v1/triage", json={"text": "I need a refund for the wrong invoice"})
    assert ok.status_code == 200
    assert ok.json()["queue"] == "billing"
    assert client.post("/v1/triage", json={"text": ""}).status_code == 422
    assert client.get("/health/live").status_code == 200
