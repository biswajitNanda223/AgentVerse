"""Retrieval by decisions: screen documents, score their passages, optionally rerank.

The pipeline follows Figure 2(c) of the DecisionRAG paper:

1. Optional higher-order levels (for example categories) narrow the corpus.
2. Document screening: one yes/no question per document, all judged in a single shared context
   (one decision-model call); keep the top k.
3. Passage scoring: one yes/no question per passage of the kept documents only; pruned documents
   are never expanded; keep the top r.
4. Optional choice reranking: one multiple-choice question over the top r passages gives the final
   order.

Everything marked "this example" below is a design choice of this repository, not taken from the
paper: the tournament for candidate sets larger than a context, abstaining on weak evidence, the
optional probability threshold, and skipping the model call when a step has a single option.
"""

from __future__ import annotations

import asyncio
import math
from collections.abc import Iterator
from dataclasses import dataclass
from time import perf_counter

from decision_rag.corpus import CorpusTree, Node
from decision_rag.models import Candidate, ChoiceModel, DecisionModel, DecisionModelError

PROBABILITY_SUM_TOLERANCE = 0.05


@dataclass(frozen=True)
class NavigationConfig:
    keep_topics: int = 2  # optional higher-order levels (categories)
    keep_documents: int = 3  # k: documents kept after screening
    keep_sections: int = 3  # only used when sections are not skipped
    keep_passages: int = 3  # r: passages kept after scoring (and reranked, if enabled)
    skip_sections: bool = True  # paper layout: documents -> passages, sections only as context
    rerank: bool = False  # optional choice reranking over the top r
    # This example: optional floor on P(yes). 0 keeps pure top-k as in the figure. If a floor is
    # set and nothing reaches it, the top candidates are kept anyway (no signal: widen, not guess).
    min_probability: float = 0.0
    abstain_below: float = 0.3  # this example: best passage under this P(yes) -> abstain
    max_candidates_per_call: int = 40  # this example: context budget for one joint judgment

    def __post_init__(self) -> None:
        keeps = (self.keep_topics, self.keep_documents, self.keep_sections, self.keep_passages)
        if min(keeps) < 1 or self.max_candidates_per_call < 2:
            raise ValueError("keep counts must be >= 1 and max_candidates_per_call >= 2")
        if not (0 <= self.min_probability <= 1 and 0 <= self.abstain_below <= 1):
            raise ValueError("probability thresholds must be within 0..1")
        if self.rerank and self.keep_passages > self.max_candidates_per_call:
            raise ValueError("rerank needs keep_passages <= max_candidates_per_call")

    def keep_for(self, kind: str) -> int:
        return {
            "topic": self.keep_topics,
            "document": self.keep_documents,
            "section": self.keep_sections,
            "passage": self.keep_passages,
        }.get(kind, self.keep_documents)

    @property
    def skipped_kinds(self) -> frozenset[str]:
        return frozenset({"section"}) if self.skip_sections else frozenset()


@dataclass(frozen=True)
class CandidateTrace:
    node_id: str
    parent_id: str
    title: str
    kind: str
    probability: float | None  # None: dropped in an early round of an oversized judgment
    kept: bool


@dataclass(frozen=True)
class StepTrace:
    step: int
    stage: str  # "topic", "document", "section", "passage" (screening/scoring) or "rerank"
    candidates: tuple[CandidateTrace, ...]
    model_calls: int
    seconds: float


@dataclass(frozen=True)
class RankedPassage:
    node: Node
    score: float  # the ranking score: choice probability if reranked, else P(yes)
    last_probability: float  # the passage's own yes/no probability
    path: tuple[str, ...]  # node ids from the top level down to the passage
    choice_probability: float | None = None


@dataclass(frozen=True)
class NavigationResult:
    query: str
    passages: tuple[RankedPassage, ...]
    steps: tuple[StepTrace, ...]
    abstained: bool
    model_calls: int
    seconds: float
    kept_ids: frozenset[str] = frozenset()


@dataclass(frozen=True)
class _State:
    node: Node
    last_probability: float
    ids: tuple[str, ...]


def _candidate(node: Node) -> Candidate:
    crumb = node.breadcrumb()
    text = f"{crumb}: {node.description}" if node.description else crumb
    return Candidate(id=node.id, title=node.title, text=text, level=node.level)


class DecisionNavigator:
    def __init__(
        self, tree: CorpusTree, model: DecisionModel, config: NavigationConfig | None = None
    ) -> None:
        self._tree = tree
        self._model = model
        self._config = config or NavigationConfig()
        if self._config.rerank and not isinstance(model, ChoiceModel):
            raise ValueError("rerank=True needs a decision model that implements choose()")

    def _children(self, node: Node) -> Iterator[Node]:
        """Children to consider, looking through skipped kinds (sections) to their passages."""

        for child in node.children:
            if child.kind in self._config.skipped_kinds:
                yield from self._children(child)
            else:
                yield child

    async def navigate(self, query: str) -> NavigationResult:
        cfg = self._config
        started = perf_counter()
        frontier = [_State(self._tree.root, 1.0, ())]
        finished: list[_State] = []
        steps: list[StepTrace] = []
        kept_ids: set[str] = set()
        total_calls = 0

        while frontier:
            owners: dict[str, _State] = {}
            nodes: list[Node] = []
            for state in frontier:
                children = list(self._children(state.node))
                if not children:
                    if state.ids:
                        finished.append(state)
                    continue
                for child in children:
                    owners[child.id] = state
                    nodes.append(child)
            if not nodes:
                break

            step_started = perf_counter()
            if len(nodes) == 1:
                # This example: one option in the whole step, nothing to compare, so no model
                # call. It inherits its parent's probability because no evidence was gathered.
                only = nodes[0]
                probabilities, calls = {only.id: owners[only.id].last_probability}, 0
            else:
                probabilities, calls = await self._judge(query, nodes)
            total_calls += calls

            judged = sorted(
                (n for n in nodes if n.id in probabilities),
                key=lambda n: probabilities[n.id],
                reverse=True,
            )
            limit = max(cfg.keep_for(n.kind) for n in nodes)
            qualified = [n for n in judged if probabilities[n.id] >= cfg.min_probability]
            kept = (qualified or judged)[:limit]
            kept_set = {n.id for n in kept}
            kept_ids |= kept_set

            steps.append(
                StepTrace(
                    step=len(steps) + 1,
                    stage=nodes[0].kind,
                    candidates=tuple(
                        CandidateTrace(
                            n.id,
                            owners[n.id].node.id,
                            n.label(),
                            n.kind,
                            probabilities.get(n.id),
                            n.id in kept_set,
                        )
                        for n in nodes
                    ),
                    model_calls=calls,
                    seconds=perf_counter() - step_started,
                )
            )
            frontier = [_State(n, probabilities[n.id], (*owners[n.id].ids, n.id)) for n in kept]

        ranked = sorted(
            (s for s in finished if s.node.kind == "passage"),
            key=lambda s: s.last_probability,
            reverse=True,
        )[: cfg.keep_passages]
        passages = tuple(
            RankedPassage(s.node, s.last_probability, s.last_probability, s.ids) for s in ranked
        )

        if cfg.rerank and len(passages) > 1:
            passages, rerank_trace = await self._rerank(query, passages, len(steps) + 1)
            steps.append(rerank_trace)
            total_calls += 1

        abstained = not passages or passages[0].last_probability < cfg.abstain_below
        return NavigationResult(
            query=query,
            passages=passages,
            steps=tuple(steps),
            abstained=abstained,
            model_calls=total_calls,
            seconds=perf_counter() - started,
            kept_ids=frozenset(kept_ids),
        )

    async def _rerank(
        self, query: str, passages: tuple[RankedPassage, ...], step: int
    ) -> tuple[tuple[RankedPassage, ...], StepTrace]:
        """Optional choice reranking: one multiple-choice question over the top r passages."""

        started = perf_counter()
        assert isinstance(self._model, ChoiceModel)
        distribution = await self._model.choose(query, [_candidate(p.node) for p in passages])
        if len(distribution) != len(passages):
            raise DecisionModelError("choice reranking returned the wrong number of options")
        for value in distribution:
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise DecisionModelError("choice reranking returned a probability outside 0..1")
        if abs(sum(distribution) - 1.0) > PROBABILITY_SUM_TOLERANCE:
            raise DecisionModelError("choice reranking probabilities do not sum to 1")
        order = sorted(range(len(passages)), key=lambda i: distribution[i], reverse=True)
        reranked = tuple(
            RankedPassage(
                passages[i].node,
                distribution[i],
                passages[i].last_probability,
                passages[i].path,
                distribution[i],
            )
            for i in order
        )
        trace = StepTrace(
            step=step,
            stage="rerank",
            candidates=tuple(
                CandidateTrace(
                    p.node.id,
                    p.node.parent.id if p.node.parent else "",
                    p.node.label(),
                    "passage",
                    p.choice_probability,
                    True,
                )
                for p in reranked
            ),
            model_calls=1,
            seconds=perf_counter() - started,
        )
        return reranked, trace

    async def _judge(self, query: str, nodes: list[Node]) -> tuple[dict[str, float], int]:
        """Judge candidates jointly. Oversized sets run as a tournament (this example).

        Each chunk is judged in its own context, the best few of every chunk advance, and the
        survivors are judged together (recursively if still too many). Only survivors get a
        probability; probabilities are comparable among the final shared context.
        """
        limit = self._config.max_candidates_per_call
        if len(nodes) <= limit:
            return await self._judge_once(query, nodes), 1
        chunks = [nodes[i : i + limit] for i in range(0, len(nodes), limit)]
        per_chunk = max(1, limit // len(chunks))
        results = await asyncio.gather(*(self._judge_once(query, chunk) for chunk in chunks))
        survivors: list[Node] = []
        for chunk, scores in zip(chunks, results, strict=True):
            best = sorted(chunk, key=lambda n: scores[n.id], reverse=True)[:per_chunk]
            survivors.extend(best)
        final, calls = await self._judge(query, survivors)
        return final, calls + len(chunks)

    async def _judge_once(self, query: str, nodes: list[Node]) -> dict[str, float]:
        candidates = [_candidate(n) for n in nodes]
        scores = await self._model.judge(query, candidates)
        if len(scores) != len(candidates):
            raise DecisionModelError("decision model returned the wrong number of judgments")
        for score in scores:
            valid = isinstance(score, int | float) and math.isfinite(score) and 0 <= score <= 1
            if not valid:
                raise DecisionModelError("decision model returned a probability outside 0..1")
        return {n.id: float(s) for n, s in zip(nodes, scores, strict=True)}
