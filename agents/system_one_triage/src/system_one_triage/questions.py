"""Typed questions and answers: the vocabulary shared by every System One backend."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Choice:
    """Pick one option. `options` maps each label to a short description."""

    instructions: str
    options: Mapping[str, str]

    def __post_init__(self) -> None:
        if not self.instructions.strip():
            raise ValueError("instructions are required")
        if len(self.options) < 2:
            raise ValueError("a choice needs at least two options")


@dataclass(frozen=True)
class Score:
    """Rate the state on an ordered rubric. `levels` run from lowest (index 0) to highest."""

    instructions: str
    levels: Sequence[str]

    def __post_init__(self) -> None:
        if not self.instructions.strip():
            raise ValueError("instructions are required")
        if len(self.levels) < 2:
            raise ValueError("a score needs at least two levels")


@dataclass(frozen=True)
class Noul:
    """Is the statement in `instructions` true? Answered as a probability."""

    instructions: str

    def __post_init__(self) -> None:
        if not self.instructions.strip():
            raise ValueError("instructions are required")


Question = Choice | Score | Noul


@dataclass(frozen=True)
class ChoiceAnswer:
    choice: str
    probabilities: Mapping[str, float]
    confidence: float


@dataclass(frozen=True)
class ScoreAnswer:
    score: float  # position on the rubric: 0 (lowest level) .. len(levels) - 1
    probabilities: Mapping[str, float]
    confidence: float
    top: int  # highest level index, so callers can normalise without the question


@dataclass(frozen=True)
class NoulAnswer:
    noul: float  # probability that the statement is true, 0..1
    confidence: float | None = None  # not every deployment reports it for this type


Answer = ChoiceAnswer | ScoreAnswer | NoulAnswer
