from __future__ import annotations

import math
import re
from collections import Counter
from dataclasses import dataclass
from itertools import pairwise

from solutions.production_ai_security.app.models import Evidence


def _tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def _cosine(left: Counter[str], right: Counter[str]) -> float:
    numerator = sum(value * right[token] for token, value in left.items())
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    return numerator / max(left_norm * right_norm, 1.0)


class LocalBiEncoder:
    """Zero-call lexical embedding baseline with the same interface as a dense bi-encoder."""

    def score(self, query: str, document: str) -> float:
        return _cosine(Counter(_tokens(query)), Counter(_tokens(document)))


class LocalCrossEncoder:
    """Pairwise reranker baseline; replace with a trained cross-encoder behind this contract."""

    def rerank(self, query: str, evidence: tuple[Evidence, ...]) -> tuple[Evidence, ...]:
        query_tokens = _tokens(query)

        def pair_score(item: Evidence) -> tuple[float, float]:
            text = item.text.lower()
            phrase_bonus = sum(
                1 for left, right in pairwise(query_tokens) if f"{left} {right}" in text
            )
            return (item.score + phrase_bonus * 0.2, item.score)

        return tuple(sorted(evidence, key=pair_score, reverse=True))


@dataclass(frozen=True, slots=True)
class NLIResult:
    label: str
    confidence: float


class LightweightNLI:
    """Deterministic NLI baseline for reproducible CI; intentionally conservative."""

    _negations = frozenset({"not", "never", "no", "cannot", "deny", "denied"})

    def classify(self, premise: str, hypothesis: str) -> NLIResult:
        premise_tokens = set(_tokens(premise))
        hypothesis_tokens = set(_tokens(hypothesis))
        overlap = len(premise_tokens & hypothesis_tokens) / max(len(hypothesis_tokens), 1)
        opposite_polarity = bool(premise_tokens & self._negations) != bool(
            hypothesis_tokens & self._negations
        )
        if overlap >= 0.5 and opposite_polarity:
            return NLIResult("contradiction", overlap)
        if overlap >= 0.7:
            return NLIResult("entailment", overlap)
        return NLIResult("neutral", 1.0 - overlap)
