"""Runnable reference implementations for the major RAG strategy families.

These classes teach orchestration and contracts. Replace local hash embeddings, in-memory
stores and deterministic policies with evaluated production services behind the same protocols.
"""

import math
import re
import sqlite3
from collections import defaultdict
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from hashlib import sha256
from typing import Protocol

from agentverse.rag.models import Chunk, RetrievalCandidate
from agentverse.rag.pipeline import CorrectiveRag, RagAnswer
from agentverse.rag.retrieval import Retriever, reciprocal_rank_fusion, tokenize


class Embedder(Protocol):
    def embed(self, text: str) -> Sequence[float]: ...


@dataclass(frozen=True, slots=True)
class HashEmbedder:
    """Deterministic feature-hashing embedder for offline examples and tests only."""

    dimensions: int = 256

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for term in tokenize(text):
            bucket = int.from_bytes(sha256(term.encode()).digest()[:8], "big") % self.dimensions
            vector[bucket] += 1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]


class DenseRetriever:
    def __init__(self, chunks: Iterable[Chunk], embedder: Embedder | None = None) -> None:
        self.chunks = list(chunks)
        self.embedder = embedder or HashEmbedder()
        self.vectors = [self.embedder.embed(chunk.text) for chunk in self.chunks]

    def search(self, query: str, tenant_id: str, k: int = 5) -> list[RetrievalCandidate]:
        query_vector = self.embedder.embed(query)
        scored = []
        for chunk, vector in zip(self.chunks, self.vectors, strict=True):
            if chunk.tenant_id != tenant_id:
                continue
            score = sum(left * right for left, right in zip(query_vector, vector, strict=True))
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda pair: (-pair[0], pair[1].id))
        return [
            RetrievalCandidate(chunk, score, dense_rank=rank)
            for rank, (score, chunk) in enumerate(scored[:k], start=1)
        ]


@dataclass(slots=True)
class HybridRetriever:
    dense: Retriever
    lexical: Retriever
    fetch_k: int = 20

    def search(self, query: str, tenant_id: str, k: int = 5) -> list[RetrievalCandidate]:
        return reciprocal_rank_fusion(
            [
                self.dense.search(query, tenant_id, self.fetch_k),
                self.lexical.search(query, tenant_id, self.fetch_k),
            ],
            limit=k,
        )


Reranker = Callable[[str, Chunk], float]


@dataclass(slots=True)
class RerankingRetriever:
    base: Retriever
    reranker: Reranker
    fetch_k: int = 20

    def search(self, query: str, tenant_id: str, k: int = 5) -> list[RetrievalCandidate]:
        candidates = self.base.search(query, tenant_id, self.fetch_k)
        reranked = [
            RetrievalCandidate(
                candidate.chunk,
                self.reranker(query, candidate.chunk),
                candidate.dense_rank,
                candidate.lexical_rank,
            )
            for candidate in candidates
        ]
        return sorted(reranked, key=lambda item: (-item.score, item.chunk.id))[:k]


@dataclass(slots=True)
class ParentDocumentRetriever:
    child_retriever: Retriever
    parents: Mapping[str, Chunk]

    def search(self, query: str, tenant_id: str, k: int = 5) -> list[RetrievalCandidate]:
        hits = self.child_retriever.search(query, tenant_id, k * 3)
        best: dict[str, RetrievalCandidate] = {}
        for hit in hits:
            if not hit.chunk.parent_id or hit.chunk.parent_id not in self.parents:
                continue
            parent = self.parents[hit.chunk.parent_id]
            existing = best.get(parent.id)
            if existing is None or hit.score > existing.score:
                best[parent.id] = replace(hit, chunk=parent)
        return sorted(best.values(), key=lambda item: (-item.score, item.chunk.id))[:k]


@dataclass(slots=True)
class MultiQueryRetriever:
    base: Retriever
    expand: Callable[[str], Sequence[str]]

    def search(self, query: str, tenant_id: str, k: int = 5) -> list[RetrievalCandidate]:
        variants = list(dict.fromkeys([query, *self.expand(query)]))[:5]
        return reciprocal_rank_fusion(
            [self.base.search(variant, tenant_id, k * 2) for variant in variants], limit=k
        )


@dataclass(slots=True)
class HyDERetriever:
    base: Retriever
    hypothetical_answer: Callable[[str], str]

    def search(self, query: str, tenant_id: str, k: int = 5) -> list[RetrievalCandidate]:
        hypothesis = self.hypothetical_answer(query)
        return self.base.search(f"{query}\n{hypothesis}", tenant_id, k)


@dataclass(frozen=True, slots=True)
class RetrievalDecision:
    needs_retrieval: bool
    reason: str


@dataclass(slots=True)
class SelfRag:
    """Retrieve only when policy asks, then critique evidence before returning context."""

    retriever: Retriever
    decide: Callable[[str], RetrievalDecision]
    critique: Callable[[str, Sequence[RetrievalCandidate]], Sequence[RetrievalCandidate]]

    def retrieve(self, query: str, tenant_id: str, k: int = 5) -> RagAnswer:
        decision = self.decide(query)
        if not decision.needs_retrieval:
            return RagAnswer(query, "", (), ())
        candidates = list(self.critique(query, self.retriever.search(query, tenant_id, k)))[:k]
        return _answer(query, candidates)


@dataclass(slots=True)
class AdaptiveRag:
    """Route by query complexity instead of using the most expensive path universally."""

    simple: Retriever
    complex: CorrectiveRag
    classify: Callable[[str], str]

    def retrieve(self, query: str, tenant_id: str, k: int = 5) -> RagAnswer:
        route = self.classify(query)
        if route == "no_retrieval":
            return RagAnswer(query, "", (), ())
        if route == "simple":
            return _answer(query, self.simple.search(query, tenant_id, k))
        return self.complex.retrieve(query, tenant_id, k)


@dataclass(slots=True)
class FederatedRetriever:
    """Search independently owned stores and fuse results without sharing mutable state."""

    stores: Mapping[str, Retriever]

    def search(self, query: str, tenant_id: str, k: int = 5) -> list[RetrievalCandidate]:
        rankings = [store.search(query, tenant_id, k * 2) for store in self.stores.values()]
        return reciprocal_rank_fusion(rankings, limit=k)


@dataclass(frozen=True, slots=True)
class AgenticStep:
    query: str
    source: str
    evidence: tuple[RetrievalCandidate, ...]


@dataclass(frozen=True, slots=True)
class AgenticResult:
    answer: RagAnswer
    steps: tuple[AgenticStep, ...]


@dataclass(slots=True)
class AgenticRag:
    """Bounded multi-hop retrieval: plan reads in parallel, synthesize once."""

    sources: Mapping[str, Retriever]
    plan: Callable[[str, Sequence[str]], Sequence[tuple[str, str]]]
    max_steps: int = 6

    def retrieve(self, query: str, tenant_id: str, k: int = 5) -> AgenticResult:
        proposed = list(self.plan(query, list(self.sources)))[: self.max_steps]
        steps: list[AgenticStep] = []
        rankings = []
        for subquery, source_name in proposed:
            source = self.sources.get(source_name)
            if source is None:
                continue
            evidence = tuple(source.search(subquery, tenant_id, k))
            steps.append(AgenticStep(subquery, source_name, evidence))
            rankings.append(evidence)
        fused = reciprocal_rank_fusion(rankings, limit=k)
        return AgenticResult(_answer(query, fused), tuple(steps))


@dataclass(frozen=True, slots=True)
class GraphEdge:
    source: str
    relation: str
    target: str
    chunk_id: str


@dataclass(slots=True)
class GraphRetriever:
    chunks: Mapping[str, Chunk]
    edges: Sequence[GraphEdge]

    def search(self, query: str, tenant_id: str, k: int = 5) -> list[RetrievalCandidate]:
        terms = set(tokenize(query))
        matched: defaultdict[str, float] = defaultdict(float)
        for edge in self.edges:
            edge_terms = set(tokenize(f"{edge.source} {edge.relation} {edge.target}"))
            overlap = len(terms & edge_terms)
            chunk = self.chunks.get(edge.chunk_id)
            if overlap and chunk and chunk.tenant_id == tenant_id:
                matched[chunk.id] += float(overlap)
        ordered = sorted(matched, key=lambda item: (-matched[item], item))[:k]
        maximum = matched[ordered[0]] if ordered else 1.0
        return [RetrievalCandidate(self.chunks[item], matched[item] / maximum) for item in ordered]


@dataclass(frozen=True, slots=True)
class MultimodalItem:
    chunk: Chunk
    modality: str
    representation: str


class MultimodalRetriever:
    """Late-fuse caption/OCR/audio representations while returning source artifacts."""

    def __init__(self, items: Iterable[MultimodalItem], embedder: Embedder | None = None) -> None:
        self.items = list(items)
        self._dense = DenseRetriever(
            [replace(item.chunk, text=item.representation) for item in self.items], embedder
        )

    def search(self, query: str, tenant_id: str, k: int = 5) -> list[RetrievalCandidate]:
        hits = self._dense.search(query, tenant_id, k)
        originals = {item.chunk.id: item.chunk for item in self.items}
        return [replace(hit, chunk=originals[hit.chunk.id]) for hit in hits]


@dataclass(slots=True)
class ConversationalRetriever:
    base: Retriever
    condense: Callable[[Sequence[str], str], str]
    max_history_turns: int = 6

    def search(
        self, query: str, tenant_id: str, k: int = 5, history: Sequence[str] = ()
    ) -> list[RetrievalCandidate]:
        standalone = self.condense(history[-self.max_history_turns :], query)
        return self.base.search(standalone, tenant_id, k)


@dataclass(slots=True)
class SqlRag:
    """Read-only parameterized SQL retrieval with an explicit query allowlist."""

    connection: sqlite3.Connection
    allowed_queries: Mapping[str, str]

    def execute(self, query_id: str, parameters: Mapping[str, str]) -> list[dict[str, object]]:
        statement = self.allowed_queries.get(query_id)
        if statement is None or not statement.lstrip().upper().startswith("SELECT"):
            raise PermissionError("query is not allowlisted as read-only")
        cursor = self.connection.execute(statement, dict(parameters))
        columns = [item[0] for item in cursor.description or ()]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


@dataclass(slots=True)
class TemporalRetriever:
    base: Retriever
    now: Callable[[], datetime] = lambda: datetime.now(UTC)
    half_life_days: float = 90.0

    def search(self, query: str, tenant_id: str, k: int = 5) -> list[RetrievalCandidate]:
        hits = self.base.search(query, tenant_id, k * 3)
        rescored = []
        for hit in hits:
            raw = hit.chunk.metadata.get("effective_at")
            if not isinstance(raw, str):
                freshness = 1.0
            else:
                age = max(0.0, (self.now() - datetime.fromisoformat(raw)).total_seconds() / 86400)
                freshness = 0.5 ** (age / self.half_life_days)
            rescored.append(replace(hit, score=hit.score * freshness))
        return sorted(rescored, key=lambda item: (-item.score, item.chunk.id))[:k]


def _answer(query: str, candidates: Sequence[RetrievalCandidate]) -> RagAnswer:
    context = "\n\n".join(
        f"[{index}] {candidate.chunk.text}" for index, candidate in enumerate(candidates, start=1)
    )
    return RagAnswer(
        query,
        context,
        tuple(candidate.chunk.source_uri for candidate in candidates),
        tuple(candidates),
    )


def simple_query_expander(query: str) -> list[str]:
    """Safe deterministic baseline; production variants may use an evaluated model."""

    terms = tokenize(query)
    return [" ".join(terms), re.sub(r"\bhow\b", "method", query, flags=re.I)]
