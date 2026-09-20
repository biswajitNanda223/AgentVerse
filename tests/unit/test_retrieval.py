from agentverse.rag.models import Chunk
from agentverse.rag.retrieval import InMemoryLexicalRetriever, reciprocal_rank_fusion


def _chunk(chunk_id: str, text: str, tenant: str = "a") -> Chunk:
    return Chunk(chunk_id, "doc", text, 0, f"memory://{chunk_id}", tenant, 0, len(text))


def test_retrieval_enforces_tenant_before_scoring() -> None:
    retriever = InMemoryLexicalRetriever(
        [_chunk("allowed", "secret retrieval answer"), _chunk("denied", "secret", "b")]
    )
    hits = retriever.search("secret", tenant_id="a", k=10)
    assert [hit.chunk.id for hit in hits] == ["allowed"]


def test_rrf_favors_repeated_candidate() -> None:
    retriever = InMemoryLexicalRetriever([_chunk("a", "alpha"), _chunk("b", "alpha beta")])
    first = retriever.search("alpha", "a", 2)
    fused = reciprocal_rank_fusion([first, list(reversed(first))], limit=2)
    assert {candidate.chunk.id for candidate in fused} == {"a", "b"}
    assert all(0 < candidate.score <= 1 for candidate in fused)
