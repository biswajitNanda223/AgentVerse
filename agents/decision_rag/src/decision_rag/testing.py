"""Test helpers: a decision model whose scores you control and whose calls are recorded."""

from collections.abc import Callable, Sequence

from decision_rag.models import Candidate


class ScriptedModel:
    """Decision model that scores candidates by a function of their id and records every call."""

    def __init__(self, score: Callable[[Candidate], float]) -> None:
        self._score = score
        self.calls: list[list[str]] = []

    async def judge(self, query: str, candidates: Sequence[Candidate]) -> list[float]:
        self.calls.append([c.id for c in candidates])
        return [self._score(c) for c in candidates]


class ScriptedChoiceModel(ScriptedModel):
    """ScriptedModel that also answers the multiple-choice rerank with a chosen distribution."""

    def __init__(
        self,
        score: Callable[[Candidate], float],
        choice: Callable[[Sequence[Candidate]], list[float]],
    ) -> None:
        super().__init__(score)
        self._choice = choice
        self.choose_calls: list[list[str]] = []

    async def choose(self, query: str, candidates: Sequence[Candidate]) -> list[float]:
        self.choose_calls.append([c.id for c in candidates])
        return self._choice(candidates)
