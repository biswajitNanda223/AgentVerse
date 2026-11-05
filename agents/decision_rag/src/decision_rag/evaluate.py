"""Compare navigation with a flat lexical retriever on a golden set.

`python -m decision_rag.evaluate [--suite sample|project-slm]`. With the offline stand-in this is
a consistency check of the machinery, NOT evidence about DecisionRAG's accuracy; both sides are
word-matchers. Set DECISION_RAG_BACKEND=claude or jev to measure a real decision model.
"""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass
from pathlib import Path

from agentverse.rag.models import Chunk
from agentverse.rag.retrieval import InMemoryLexicalRetriever
from decision_rag.corpus import CorpusTree, Node
from decision_rag.factory import build_config, build_model
from decision_rag.loaders import load_corpus
from decision_rag.navigator import DecisionNavigator
from decision_rag.sample_corpus import GOLDEN, sample_tree
from decision_rag.settings import DecisionRagSettings, get_settings
from decision_rag.slm_golden import GOLDEN_SLM

SLM_DATA = Path(__file__).resolve().parents[2] / "data" / "project_slm"


@dataclass(frozen=True)
class Report:
    queries: int
    navigator_hit1: float
    flat_hit1: float
    mean_model_calls: float
    mean_seconds: float


def suite(name: str) -> tuple[CorpusTree, list[tuple[str, str]]]:
    if name == "project-slm":
        return load_corpus(SLM_DATA), GOLDEN_SLM
    return sample_tree(), GOLDEN


def matches(node: Node | None, expected: str) -> bool:
    """A passage matches by id, or when its section's title starts with the expected scenario id."""

    if node is None:
        return False
    return node.id == expected or (
        node.parent is not None and node.parent.title.startswith(expected)
    )


def flat_retriever(tree: CorpusTree) -> InMemoryLexicalRetriever:
    chunks = [
        Chunk(
            id=p.id,
            document_id=p.parent.id if p.parent else p.id,
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


async def evaluate(
    settings: DecisionRagSettings | None = None, suite_name: str = "sample"
) -> Report:
    settings = settings or get_settings()
    tree, golden = suite(suite_name)
    navigator = DecisionNavigator(tree, build_model(settings), build_config(settings))
    flat = flat_retriever(tree)
    nav_hits = flat_hits = 0
    calls = seconds = 0.0
    for query, expected in golden:
        result = await navigator.navigate(query)
        calls += result.model_calls
        seconds += result.seconds
        nav_hits += bool(result.passages) and matches(result.passages[0].node, expected)
        top = flat.search(query, tenant_id="eval", k=1)
        flat_hits += bool(top) and matches(tree.nodes.get(top[0].chunk.id), expected)
    n = len(golden)
    return Report(n, nav_hits / n, flat_hits / n, calls / n, seconds / n)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="decision_rag.evaluate")
    parser.add_argument("--suite", choices=["sample", "project-slm"], default="sample")
    args = parser.parse_args()
    report = asyncio.run(evaluate(suite_name=args.suite))
    print(f"suite              {args.suite}")
    print(f"queries            {report.queries}")
    print(f"navigator Hit@1    {report.navigator_hit1:.2f}")
    print(f"flat lexical Hit@1 {report.flat_hit1:.2f}")
    print(f"decision-model calls per query {report.mean_model_calls:.1f}")
    print(f"mean latency       {report.mean_seconds * 1000:.1f} ms")
