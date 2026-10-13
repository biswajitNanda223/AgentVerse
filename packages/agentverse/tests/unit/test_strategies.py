import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from agentverse.rag.advanced_chunking import ParentChildChunker
from agentverse.rag.models import Chunk, Document
from agentverse.rag.pipeline import CorrectiveRag
from agentverse.rag.retrieval import InMemoryLexicalRetriever
from agentverse.rag.strategies import (
    AdaptiveRag,
    AgenticRag,
    DenseRetriever,
    FederatedRetriever,
    GraphEdge,
    GraphRetriever,
    HybridRetriever,
    HyDERetriever,
    MultiQueryRetriever,
    ParentDocumentRetriever,
    RerankingRetriever,
    RetrievalDecision,
    SelfRag,
    SqlRag,
    TemporalRetriever,
)


def items() -> list[Chunk]:
    return [
        Chunk("a", "d", "hybrid vector keyword retrieval", 0, "memory://a", "t", 0, 31),
        Chunk("b", "d", "corrective grading evidence", 1, "memory://b", "t", 32, 59),
    ]


def test_dense_hybrid_reranking_multiquery_and_hyde() -> None:
    data = items()
    dense = DenseRetriever(data)
    lexical = InMemoryLexicalRetriever(data)
    assert dense.search("vector", "t", 1)[0].chunk.id == "a"
    assert HybridRetriever(dense, lexical).search("keyword", "t")
    reranked = RerankingRetriever(dense, lambda _query, chunk: float(chunk.id == "b"))
    assert reranked.search("retrieval evidence", "t")[0].chunk.id == "b"
    assert MultiQueryRetriever(dense, lambda _query: ["evidence"]).search("unknown", "t")
    assert HyDERetriever(dense, lambda _query: "corrective evidence").search("unknown", "t")


def test_parent_self_adaptive_and_federated_agentic() -> None:
    source = Document("d", " ".join(chunk.text for chunk in items()), "memory://d", "t")
    parents, children = ParentChildChunker(20, 5, 1).split(source)
    child_retriever = DenseRetriever(children)
    assert ParentDocumentRetriever(
        child_retriever, {parent.id: parent for parent in parents}
    ).search("evidence", "t")
    base = InMemoryLexicalRetriever(items())
    self_rag = SelfRag(
        base, lambda _query: RetrievalDecision(True, "test"), lambda _query, hits: hits
    )
    assert self_rag.retrieve("evidence", "t").citations
    adaptive = AdaptiveRag(base, CorrectiveRag(base), lambda _query: "simple")
    assert adaptive.retrieve("evidence", "t").citations
    sources = {"one": base, "two": base}
    assert FederatedRetriever(sources).search("evidence", "t")
    result = AgenticRag(sources, lambda query, names: [(query, name) for name in names]).retrieve(
        "evidence", "t"
    )
    assert len(result.steps) == 2 and result.answer.citations


def test_graph_sql_and_temporal_security() -> None:
    data = items()
    graph = GraphRetriever(
        {chunk.id: chunk for chunk in data}, [GraphEdge("CRAG", "grades", "evidence", "b")]
    )
    assert graph.search("CRAG evidence", "t")[0].chunk.id == "b"
    connection = sqlite3.connect(":memory:")
    connection.execute("CREATE TABLE facts(name TEXT)")
    connection.execute("INSERT INTO facts VALUES ('rag')")
    sql = SqlRag(connection, {"facts": "SELECT name FROM facts WHERE name=:name"})
    assert sql.execute("facts", {"name": "rag"}) == [{"name": "rag"}]
    with pytest.raises(PermissionError):
        sql.execute("missing", {})
    connection.close()
    old = replace_metadata(data[0], (datetime.now(UTC) - timedelta(days=365)).isoformat())
    fresh = replace_metadata(data[1], datetime.now(UTC).isoformat())
    temporal = TemporalRetriever(DenseRetriever([old, fresh]))
    hits = temporal.search("retrieval evidence", "t", 2)
    assert hits


def replace_metadata(chunk: Chunk, effective_at: str) -> Chunk:
    return Chunk(
        chunk.id,
        chunk.document_id,
        chunk.text,
        chunk.ordinal,
        chunk.source_uri,
        chunk.tenant_id,
        chunk.start_char,
        chunk.end_char,
        metadata={"effective_at": effective_at},
    )
