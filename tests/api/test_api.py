from fastapi.testclient import TestClient

from agentverse.api.app import create_app
from agentverse.core.config import get_settings


def test_health_and_tenant_isolation() -> None:
    get_settings.cache_clear()
    headers_a = {"x-api-key": "change-me", "x-tenant-id": "a"}
    headers_b = {"x-api-key": "change-me", "x-tenant-id": "b"}
    with TestClient(create_app()) as client:
        assert client.get("/health/live").status_code == 200
        ingest = client.post(
            "/v1/rag/documents",
            headers=headers_a,
            json={
                "documents": [
                    {"id": "d", "text": "private alpha knowledge", "source_uri": "memory://d"}
                ]
            },
        )
        assert ingest.status_code == 202
        own = client.post("/v1/rag/query", headers=headers_a, json={"query": "alpha"})
        other = client.post("/v1/rag/query", headers=headers_b, json={"query": "alpha"})
        assert own.json()["citations"] == ["memory://d"]
        assert other.json()["citations"] == []


def test_authentication_is_required() -> None:
    with TestClient(create_app()) as client:
        response = client.post("/v1/rag/query", json={"query": "anything"})
        assert response.status_code == 401
