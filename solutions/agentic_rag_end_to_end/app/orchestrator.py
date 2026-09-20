from collections.abc import Callable, Sequence
from dataclasses import dataclass
from itertools import pairwise

from agentverse.agents.guardrails import inspect_untrusted_content, validate_citations
from agentverse.rag.models import Chunk, Document, RetrievalCandidate
from agentverse.rag.pipeline import CorrectiveRag
from agentverse.rag.retrieval import InMemoryLexicalRetriever
from agentverse.rag.strategies import (
    AgenticRag,
    DenseRetriever,
    GraphEdge,
    GraphRetriever,
    HybridRetriever,
)
from solutions.agentic_rag_end_to_end.app.models import Citation, RetrievalMode
from solutions.agentic_rag_end_to_end.app.router import QueryRouter

Generator = Callable[[str, Sequence[RetrievalCandidate]], str]


@dataclass(frozen=True, slots=True)
class OrchestrationResult:
    answer: str
    mode: RetrievalMode
    citations: tuple[Citation, ...]
    steps: tuple[str, ...]
    abstained: bool


def cited_extractive_generator(question: str, candidates: Sequence[RetrievalCandidate]) -> str:
    """Offline-safe generator. Production injects the ADK/model generator behind this boundary."""

    del question
    if not candidates:
        return "I do not have enough verified evidence to answer this request."
    statements = [
        f"{candidate.chunk.text.strip()} [{index}]" for index, candidate in enumerate(candidates, 1)
    ]
    return " ".join(statements)


class AgenticRagOrchestrator:
    """One-shot control plane: route, retrieve/delegate, guard and synthesize once."""

    def __init__(
        self,
        chunks: Sequence[Chunk] = (),
        edges: Sequence[GraphEdge] = (),
        generator: Generator = cited_extractive_generator,
        max_steps: int = 6,
    ) -> None:
        self.router = QueryRouter()
        self.generator = generator
        self.max_steps = max_steps
        self.replace_index(chunks, edges)

    def replace_index(self, chunks: Sequence[Chunk], edges: Sequence[GraphEdge] = ()) -> None:
        self._chunks = list(chunks)
        graph_edges = list(edges) or self._derive_edges(self._chunks)
        self.semantic = DenseRetriever(self._chunks)
        self.lexical = InMemoryLexicalRetriever(self._chunks)
        self.hybrid = HybridRetriever(self.semantic, self.lexical)
        self.corrective = CorrectiveRag(self.hybrid, min_relevance=0.1)
        self.graph = GraphRetriever({chunk.id: chunk for chunk in self._chunks}, graph_edges)
        self.agentic = AgenticRag(
            {"semantic": self.semantic, "lexical": self.lexical, "graph": self.graph},
            self._plan,
            max_steps=self.max_steps,
        )

    def add_documents(self, documents: Sequence[Document]) -> int:
        from agentverse.rag.advanced_chunking import SemanticChunker

        chunks = [chunk for document in documents for chunk in SemanticChunker().split(document)]
        self.replace_index([*self._chunks, *chunks])
        return len(chunks)

    def ask(
        self, question: str, tenant_id: str, requested: RetrievalMode = RetrievalMode.AUTO
    ) -> OrchestrationResult:
        decision = self.router.route(question, requested)
        steps = [f"route:{decision.mode.value}:{decision.reason}"]
        if decision.mode is RetrievalMode.RAGLESS:
            return OrchestrationResult(
                "Hello. Ask me a question about the indexed knowledge sources.",
                decision.mode,
                (),
                tuple(steps),
                False,
            )
        if decision.mode is RetrievalMode.SEMANTIC:
            candidates = self.corrective.retrieve(question, tenant_id, 5).candidates
            steps.append("retrieve:hybrid-semantic+lexical")
        elif decision.mode is RetrievalMode.GRAPH:
            candidates = tuple(self.graph.search(question, tenant_id, 5))
            steps.append("retrieve:graph")
        else:
            result = self.agentic.retrieve(question, tenant_id, 5)
            candidates = result.answer.candidates
            steps.extend(f"retrieve:{step.source}:{step.query}" for step in result.steps)
        safe = [item for item in candidates if inspect_untrusted_content(item.chunk.text).allowed]
        if len(safe) != len(candidates):
            steps.append("guard:removed-untrusted-evidence")
        answer = self.generator(question, safe)
        citation_check = validate_citations(answer, len(safe))
        if not citation_check.allowed:
            answer = "I abstained because the generated citation set failed validation."
            safe = []
            steps.append(f"guard:abstain:{citation_check.reason}")
        citations = tuple(
            Citation(source_uri=item.chunk.source_uri, chunk_id=item.chunk.id, score=item.score)
            for item in safe
        )
        return OrchestrationResult(answer, decision.mode, citations, tuple(steps), not bool(safe))

    @staticmethod
    def _plan(question: str, sources: Sequence[str]) -> list[tuple[str, str]]:
        """Bounded disjoint read plan; a single caller owns final synthesis."""

        preferred = [name for name in ("semantic", "lexical", "graph") if name in sources]
        return [(question, name) for name in preferred]

    @staticmethod
    def _derive_edges(chunks: Sequence[Chunk]) -> list[GraphEdge]:
        """Local co-occurrence graph; production replaces this with evaluated entity extraction."""

        from agentverse.rag.retrieval import tokenize

        edges: list[GraphEdge] = []
        for chunk in chunks:
            terms = list(dict.fromkeys(tokenize(chunk.text)))[:30]
            edges.extend(
                GraphEdge(left, "co_occurs", right, chunk.id) for left, right in pairwise(terms)
            )
        return edges
