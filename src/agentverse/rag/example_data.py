"""Small deterministic corpus shared by standalone examples."""

from agentverse.rag.models import Chunk, Document

DOCUMENT = Document(
    "guide",
    "Hybrid RAG combines semantic vectors with exact lexical matching. "
    "Corrective RAG grades evidence against the original query. "
    "Agentic RAG decomposes multi-hop questions and searches bounded sources.",
    "memory://guide",
    "demo",
)


def chunks() -> list[Chunk]:
    return [
        Chunk(
            "c1",
            "guide",
            "Hybrid RAG combines vectors and keywords.",
            0,
            "memory://guide",
            "demo",
            0,
            42,
        ),
        Chunk(
            "c2",
            "guide",
            "CRAG grades evidence and rewrites weak queries.",
            1,
            "memory://guide",
            "demo",
            43,
            90,
        ),
        Chunk(
            "c3",
            "guide",
            "Agentic RAG performs bounded multi-hop retrieval.",
            2,
            "memory://guide",
            "demo",
            91,
            140,
        ),
    ]
