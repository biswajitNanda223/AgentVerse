from collections.abc import Callable, Sequence
from dataclasses import dataclass

from agentverse.core.telemetry import span
from agentverse.rag.models import RetrievalCandidate
from agentverse.rag.retrieval import Retriever

Grader = Callable[[str, RetrievalCandidate], float]
Rewriter = Callable[[str], str]


@dataclass(frozen=True, slots=True)
class RagAnswer:
    query: str
    context: str
    citations: tuple[str, ...]
    candidates: tuple[RetrievalCandidate, ...]
    corrected: bool = False


class CorrectiveRag:
    """Query-aware corrective retrieval with bounded single rewrite."""

    def __init__(
        self,
        retriever: Retriever,
        grader: Grader | None = None,
        rewriter: Rewriter | None = None,
        min_relevance: float = 0.2,
    ) -> None:
        self.retriever = retriever
        self.grader = grader or (lambda _query, candidate: candidate.score)
        self.rewriter = rewriter or (lambda query: query)
        self.min_relevance = min_relevance

    def retrieve(self, query: str, tenant_id: str, k: int = 5) -> RagAnswer:
        with span("rag.retrieve", rag_top_k=k, tenant_id=tenant_id):
            candidates = self.retriever.search(query, tenant_id, k)
            relevant = self._grade(query, candidates)
            corrected = False
            if not relevant:
                rewritten = self.rewriter(query)
                candidates = self.retriever.search(rewritten, tenant_id, k)
                relevant = self._grade(query, candidates)
                corrected = rewritten != query
            selected = relevant[:k]
            context = "\n\n".join(
                f"[{index}] {candidate.chunk.text}"
                for index, candidate in enumerate(selected, start=1)
            )
            citations = tuple(candidate.chunk.source_uri for candidate in selected)
            return RagAnswer(query, context, citations, tuple(selected), corrected)

    def _grade(
        self, query: str, candidates: Sequence[RetrievalCandidate]
    ) -> list[RetrievalCandidate]:
        graded = [
            RetrievalCandidate(
                chunk=candidate.chunk,
                score=self.grader(query, candidate),
                dense_rank=candidate.dense_rank,
                lexical_rank=candidate.lexical_rank,
                rationale=candidate.rationale,
            )
            for candidate in candidates
        ]
        return sorted(
            (candidate for candidate in graded if candidate.score >= self.min_relevance),
            key=lambda candidate: (-candidate.score, candidate.chunk.id),
        )
