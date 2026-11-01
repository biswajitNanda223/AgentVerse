"""Shared types: candidates the decision model judges, and the model interface itself."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class DecisionModelError(Exception):
    """The decision model failed or answered in an unusable shape."""


@dataclass(frozen=True)
class Candidate:
    """One branch (topic, document, section or passage) offered to the decision model."""

    id: str
    title: str
    text: str  # breadcrumb plus a short description of what the branch contains
    level: int


class DecisionModel(Protocol):
    async def judge(self, query: str, candidates: Sequence[Candidate]) -> list[float]:
        """Return P(relevant) for every candidate, in order, judged together in one context.

        Probabilities must be comparable across candidates because the model saw them all at
        once. That is what lets the navigator rank and prune them against each other.
        """
        ...


@runtime_checkable
class ChoiceModel(Protocol):
    """Optional second capability: one multiple-choice question over a few candidates."""

    async def choose(self, query: str, candidates: Sequence[Candidate]) -> list[float]:
        """Return a probability distribution over the candidates (non-negative, sums to 1).

        Used for the optional final reranking of the top passages: one question whose options
        are the passages, instead of independent yes/no scores.
        """
        ...
