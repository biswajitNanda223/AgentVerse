import math
import re
from collections import Counter, defaultdict
from collections.abc import Iterable, Sequence
from typing import Protocol

from agentverse.rag.models import Chunk, RetrievalCandidate

_TOKEN = re.compile(r"[\w-]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    return [match.group(0).lower() for match in _TOKEN.finditer(text)]


class Retriever(Protocol):
    def search(self, query: str, tenant_id: str, k: int) -> list[RetrievalCandidate]: ...


class InMemoryLexicalRetriever:
    """Small BM25-like reference index for tests/local learning, not a scale database."""

    def __init__(self, chunks: Iterable[Chunk] = ()) -> None:
        self._chunks = list(chunks)
        self._term_counts = [Counter(tokenize(chunk.text)) for chunk in self._chunks]
        self._doc_frequency: Counter[str] = Counter()
        for counts in self._term_counts:
            self._doc_frequency.update(counts.keys())

    def add(self, chunks: Iterable[Chunk]) -> None:
        self._chunks.extend(chunks)
        self._term_counts = [Counter(tokenize(chunk.text)) for chunk in self._chunks]
        self._doc_frequency = Counter()
        for counts in self._term_counts:
            self._doc_frequency.update(counts.keys())

    def search(self, query: str, tenant_id: str, k: int = 5) -> list[RetrievalCandidate]:
        terms = tokenize(query)
        eligible = [i for i, chunk in enumerate(self._chunks) if chunk.tenant_id == tenant_id]
        scored: list[tuple[float, Chunk]] = []
        for index in eligible:
            counts = self._term_counts[index]
            length_norm = 1.0 + math.log1p(sum(counts.values()))
            score = sum(
                counts[term]
                * math.log((len(self._chunks) + 1) / (self._doc_frequency[term] + 1) + 1)
                / length_norm
                for term in terms
            )
            if score > 0:
                scored.append((score, self._chunks[index]))
        scored.sort(key=lambda pair: (-pair[0], pair[1].id))
        ceiling = scored[0][0] if scored else 1.0
        return [
            RetrievalCandidate(chunk=chunk, score=score / ceiling, lexical_rank=rank)
            for rank, (score, chunk) in enumerate(scored[:k], start=1)
        ]


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[RetrievalCandidate]], *, k: int = 60, limit: int = 10
) -> list[RetrievalCandidate]:
    """Fuse heterogeneous rankings without assuming comparable raw scores."""

    scores: defaultdict[str, float] = defaultdict(float)
    candidates: dict[str, RetrievalCandidate] = {}
    for ranking in rankings:
        for rank, candidate in enumerate(ranking, start=1):
            scores[candidate.chunk.id] += 1.0 / (k + rank)
            candidates[candidate.chunk.id] = candidate
    ordered = sorted(scores, key=lambda item: (-scores[item], item))[:limit]
    maximum = scores[ordered[0]] if ordered else 1.0
    return [
        RetrievalCandidate(chunk=candidates[item].chunk, score=scores[item] / maximum)
        for item in ordered
    ]
