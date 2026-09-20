from dataclasses import dataclass

from agentverse.rag.retrieval import tokenize
from solutions.agentic_rag_end_to_end.app.models import RetrievalMode


@dataclass(frozen=True, slots=True)
class RouteDecision:
    mode: RetrievalMode
    reason: str


class QueryRouter:
    """Deterministic first-pass router; an evaluated classifier can replace it."""

    def route(self, question: str, requested: RetrievalMode) -> RouteDecision:
        if requested is not RetrievalMode.AUTO:
            return RouteDecision(requested, "explicit client selection")
        terms = set(tokenize(question))
        if terms & {"hello", "hi", "thanks", "help"} and len(terms) <= 5:
            return RouteDecision(RetrievalMode.RAGLESS, "small conversational request")
        if terms & {"relationship", "depends", "connected", "path", "graph"}:
            return RouteDecision(RetrievalMode.GRAPH, "relationship-oriented request")
        if terms & {"compare", "research", "across", "multi-hop", "investigate"}:
            return RouteDecision(RetrievalMode.AGENTIC, "multi-source reasoning request")
        return RouteDecision(RetrievalMode.SEMANTIC, "knowledge request")
