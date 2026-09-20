from functools import lru_cache

from agentverse.rag.chunking import FixedWindowChunker
from agentverse.rag.models import Document
from agentverse.rag.retrieval import InMemoryLexicalRetriever


@lru_cache
def _demo_retriever() -> InMemoryLexicalRetriever:
    document = Document(
        id="agentverse-guide",
        text=(
            "Hybrid RAG combines lexical and semantic retrieval. Corrective RAG grades "
            "retrieved evidence against the original query and rewrites weak queries. "
            "Production agents need idempotency, bounded tools, evaluation and telemetry."
        ),
        source_uri="docs://agentverse/rag-handbook",
        tenant_id="demo",
    )
    return InMemoryLexicalRetriever(FixedWindowChunker(size=30, overlap=5).split(document))


def search_knowledge(query: str) -> dict[str, object]:
    """Search the bounded AgentVerse demo corpus and return evidence with citations."""

    hits = _demo_retriever().search(query, tenant_id="demo", k=3)
    return {
        "evidence": [hit.chunk.text for hit in hits],
        "citations": [hit.chunk.source_uri for hit in hits],
    }


def assess_risk(action: str) -> dict[str, str | bool]:
    """Classify whether a proposed action needs explicit human approval."""

    normalized = action.lower()
    sensitive = ("delete", "pay", "send", "publish", "permission", "execute")
    requires_approval = any(word in normalized for word in sensitive)
    return {
        "requires_approval": requires_approval,
        "reason": "consequential side effect" if requires_approval else "read-only/low impact",
    }
