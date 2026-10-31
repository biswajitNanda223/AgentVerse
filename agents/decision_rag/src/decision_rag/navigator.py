"""Beam navigation of a corpus tree with a decision model.

At each step the candidates are every child of every branch still alive. They are judged
together in one shared context (one decision-model call), the best few are kept, and their
children become the next step's candidates. When nothing alive has children, the surviving
passages are ranked by the geometric mean of the probabilities along their path.

Everything that is a tunable choice (beam width, thresholds, how oversized candidate sets are
split) is in NavigationConfig. These are this example's design decisions, not values taken from
a paper.
"""

from __future__ import annotations

import asyncio
import math
from dataclasses import dataclass, field
from time import perf_counter

from decision_rag.corpus import CorpusTree, Node
from decision_rag.models import Candidate, DecisionModel, DecisionModelError


@dataclass(frozen=True)
class NavigationConfig:
    beam_width: int = 3  # branches kept per step
    # Keep a candidate only if at least this likely relevant. If none qualifies, keep the top
    # beam_width anyway: no signal means widen, not guess one branch.
    min_probability: float = 0.2
    abstain_below: float = 0.3  # best passage under this probability -> abstain
    max_candidates_per_call: int = 40  # context budget for one joint judgment
    top_k: int = 3  # passages returned

    def __post_init__(self) -> None:
        if self.beam_width < 1 or self.top_k < 1 or self.max_candidates_per_call < 2:
            raise ValueError("beam_width and top_k must be >= 1, max_candidates_per_call >= 2")
        if not (0 <= self.min_probability <= 1 and 0 <= self.abstain_below <= 1):
            raise ValueError("probability thresholds must be within 0..1")


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
    candidates: tuple[CandidateTrace, ...]
    model_calls: int
    seconds: float


@dataclass(frozen=True)
class RankedPassage:
    node: Node
    score: float  # geometric mean of path probabilities
    last_probability: float
    path: tuple[str, ...]  # node ids from topic down to the passage


@dataclass(frozen=True)
class NavigationResult:
    query: str
    passages: tuple[RankedPassage, ...]
    steps: tuple[StepTrace, ...]
    abstained: bool
    model_calls: int
    seconds: float
    kept_ids: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class _Path:
    node: Node
    log_sum: float
    depth: int
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

    async def navigate(self, query: str) -> NavigationResult:
        cfg = self._config
        started = perf_counter()
        frontier = [_Path(self._tree.root, 0.0, 0, 1.0, ())]
        finished: list[_Path] = []
        steps: list[StepTrace] = []
        kept_ids: set[str] = set()
        total_calls = 0

        while frontier:
            owners: dict[str, _Path] = {}
            nodes: list[Node] = []
            for state in frontier:
                if state.node.is_leaf:
                    if state.depth:
                        finished.append(state)
                    continue
                for child in state.node.children:
                    owners[child.id] = state
                    nodes.append(child)
            if not nodes:
                break

            step_started = perf_counter()
            probabilities, calls = await self._judge(query, nodes)
            total_calls += calls

            judged = sorted(
                (n for n in nodes if n.id in probabilities),
                key=lambda n: probabilities[n.id],
                reverse=True,
            )
            kept = [n for n in judged if probabilities[n.id] >= cfg.min_probability]
            # No candidate looks relevant: the model has no signal here, so widen the beam
            # (keep the top beam_width) rather than commit to one arbitrary branch.
            kept = (kept or judged)[: cfg.beam_width]
            kept_set = {n.id for n in kept}
            kept_ids |= kept_set

            steps.append(
                StepTrace(
                    step=len(steps) + 1,
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
            frontier = [
                _Path(
                    n,
                    owners[n.id].log_sum + math.log(max(probabilities[n.id], 1e-6)),
                    owners[n.id].depth + 1,
                    probabilities[n.id],
                    (*owners[n.id].ids, n.id),
                )
                for n in kept
            ]

        ranked = sorted(
            (p for p in finished if p.node.kind == "passage"),
            key=lambda p: (p.log_sum / p.depth, p.last_probability),
            reverse=True,
        )[: cfg.top_k]
        passages = tuple(
            RankedPassage(p.node, math.exp(p.log_sum / p.depth), p.last_probability, p.ids)
            for p in ranked
        )
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

    async def _judge(self, query: str, nodes: list[Node]) -> tuple[dict[str, float], int]:
        """Judge candidates jointly. Oversized sets run as a tournament.

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
            if (
                not isinstance(score, int | float)
                or not math.isfinite(score)
                or not 0 <= score <= 1
            ):
                raise DecisionModelError("decision model returned a probability outside 0..1")
        return {n.id: float(s) for n, s in zip(nodes, scores, strict=True)}
