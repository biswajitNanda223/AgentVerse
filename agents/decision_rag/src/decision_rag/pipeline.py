"""Navigate, then answer from the passages found. Fails safe when the decision model is down."""

from __future__ import annotations

from dataclasses import dataclass

from decision_rag.corpus import CorpusTree
from decision_rag.models import DecisionModel, DecisionModelError
from decision_rag.navigator import DecisionNavigator, NavigationConfig, NavigationResult


@dataclass(frozen=True)
class Citation:
    passage_id: str
    path: str  # human-readable breadcrumb
    probability: float


@dataclass(frozen=True)
class RagAnswer:
    text: str
    citations: tuple[Citation, ...]
    abstained: bool
    reason: str | None
    navigation: NavigationResult | None


class DecisionRagPipeline:
    def __init__(
        self, tree: CorpusTree, model: DecisionModel, config: NavigationConfig | None = None
    ) -> None:
        self._navigator = DecisionNavigator(tree, model, config)

    async def answer(self, query: str) -> RagAnswer:
        try:
            result = await self._navigator.navigate(query)
        except DecisionModelError as exc:
            return RagAnswer(
                "I could not search the corpus right now.",
                (),
                True,
                f"decision_model_unavailable: {exc}",
                None,
            )
        if result.abstained:
            return RagAnswer(
                "I did not find evidence that answers this.", (), True, "low_relevance", result
            )
        citations = tuple(
            Citation(p.node.id, p.node.breadcrumb(), round(p.last_probability, 3))
            for p in result.passages
        )
        # Extractive answer: the best passage verbatim. A generator model would synthesise here,
        # but only from these passages and with these citations.
        best = result.passages[0].node.text or ""
        return RagAnswer(best, citations, False, None, result)
