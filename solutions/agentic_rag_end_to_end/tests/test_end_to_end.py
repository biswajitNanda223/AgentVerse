from fastapi.testclient import TestClient

from agentverse.rag.models import Chunk
from agentverse.rag.strategies import GraphEdge
from solutions.agentic_rag_end_to_end.app.api import create_app
from solutions.agentic_rag_end_to_end.app.models import RetrievalMode
from solutions.agentic_rag_end_to_end.app.orchestrator import AgenticRagOrchestrator


def corpus() -> list[Chunk]:
    return [
        Chunk(
            "s", "d", "Semantic RAG retrieves meaning with embeddings.", 0, "memory://s", "t", 0, 45
        ),
        Chunk(
            "g", "d", "Graph RAG connects entities through relations.", 1, "memory://g", "t", 46, 90
        ),
    ]


def test_all_routes_and_tenant_isolation() -> None:
    runtime = AgenticRagOrchestrator(
        corpus(), [GraphEdge("Graph RAG", "connects", "entities", "g")]
    )
    assert runtime.ask("hello", "t").mode is RetrievalMode.RAGLESS
    assert runtime.ask("semantic meaning", "t", RetrievalMode.SEMANTIC).citations
    assert runtime.ask("How are Graph RAG entities connected?", "t", RetrievalMode.GRAPH).citations
    assert runtime.ask("compare semantic and graph", "t", RetrievalMode.AGENTIC).citations
    assert not runtime.ask("semantic meaning", "other", RetrievalMode.SEMANTIC).citations


def test_http_ingest_to_answer() -> None:
    with TestClient(create_app()) as client:
        headers = {"x-api-key": "local-only", "x-tenant-id": "demo"}
        ingested = client.post(
            "/v1/documents",
            headers=headers,
            json={
                "documents": [
                    {
                        "id": "guide",
                        "text": (
                            "Semantic retrieval matches meaning. "
                            "Graph retrieval follows relationships."
                        ),
                        "source_uri": "memory://guide",
                    }
                ]
            },
        )
        assert ingested.status_code == 202
        response = client.post(
            "/v1/ask",
            headers=headers,
            json={"question": "semantic meaning", "mode": "semantic"},
        )
        assert response.status_code == 200
        assert response.json()["citations"][0]["source_uri"] == "memory://guide"
