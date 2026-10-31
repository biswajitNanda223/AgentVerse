"""Compare navigation with a flat lexical retriever on the built-in golden set.

`python -m decision_rag.evaluate`. With the offline stand-in this is a consistency check of the
machinery, NOT evidence about DecisionRAG's accuracy; both sides are word-matchers. Point it at
a real decision model (DECISION_RAG_BACKEND=jev) to measure what the technique buys you.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from agentverse.rag.models import Chunk
from agentverse.rag.retrieval import InMemoryLexicalRetriever
from decision_rag.corpus import CorpusTree
from decision_rag.factory import build_config, build_model
from decision_rag.navigator import DecisionNavigator
from decision_rag.sample_corpus import GOLDEN, sample_tree
from decision_rag.settings import DecisionRagSettings, get_settings


@dataclass(frozen=True)
class Report:
    queries: int
    navigator_hit1: float
    flat_hit1: float
    mean_model_calls: float
    mean_seconds: float


def flat_retriever(tree: CorpusTree) -> InMemoryLexicalRetriever:
    chunks = [
        Chunk(
            id=p.id,
            document_id=p.id.rsplit("/", 2)[0],
            text=p.text or "",
            ordinal=i,
            source_uri=p.id,
            tenant_id="eval",
            start_char=0,
            end_char=len(p.text or ""),
        )
        for i, p in enumerate(tree.passages())
    ]
    return InMemoryLexicalRetriever(chunks)


async def evaluate(settings: DecisionRagSettings | None = None) -> Report:
    settings = settings or get_settings()
    tree = sample_tree()
    navigator = DecisionNavigator(tree, build_model(settings), build_config(settings))
    flat = flat_retriever(tree)
    nav_hits = flat_hits = 0
    calls = seconds = 0.0
    for query, expected in GOLDEN:
        result = await navigator.navigate(query)
        calls += result.model_calls
        seconds += result.seconds
        nav_hits += bool(result.passages) and result.passages[0].node.id == expected
        top = flat.search(query, tenant_id="eval", k=1)
        flat_hits += bool(top) and top[0].chunk.id == expected
    n = len(GOLDEN)
    return Report(n, nav_hits / n, flat_hits / n, calls / n, seconds / n)


if __name__ == "__main__":
    report = asyncio.run(evaluate())
    print(f"queries            {report.queries}")
    print(f"navigator Hit@1    {report.navigator_hit1:.2f}")
    print(f"flat lexical Hit@1 {report.flat_hit1:.2f}")
    print(f"decision-model calls per query {report.mean_model_calls:.1f}")
    print(f"mean latency       {report.mean_seconds * 1000:.1f} ms")
