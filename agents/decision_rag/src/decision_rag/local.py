"""Offline stand-in decision model: a lexical heuristic, NOT a language model.

It judges all candidates in one shared context the way a decision model does (probabilities are
relative to the other candidates in the same call), so the navigator, tests and demos run with
no key. It matches words, so it cannot understand paraphrases; real gains need a real decision
model such as Jev (see jev.py). Do not read benchmark numbers from this class as evidence for
or against DecisionRAG.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence

from decision_rag.models import Candidate

STOP = frozenset(
    [
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "can",
        "do",
        "does",
        "for",
        "from",
        "how",
        "i",
        "if",
        "in",
        "is",
        "it",
        "of",
        "on",
        "or",
        "so",
        "that",
        "the",
        "their",
        "then",
        "there",
        "these",
        "this",
        "to",
        "was",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
        "you",
        "your",
    ]
)


def terms(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words if w not in STOP]


class LexicalDecisionModel:
    async def judge(self, query: str, candidates: Sequence[Candidate]) -> list[float]:
        if not candidates:
            return []
        query_terms = set(terms(query))
        bags = [Counter(terms(c.text)) for c in candidates]
        document_frequency: Counter[str] = Counter()
        for bag in bags:
            document_frequency.update(bag.keys())
        n = len(candidates)
        scores: list[float] = []
        for bag in bags:
            length = sum(bag.values()) or 1
            raw = sum(
                math.log(1 + n / (1 + document_frequency[t])) * (bag[t] / (bag[t] + 1.2))
                for t in query_terms
                if t in bag
            )
            scores.append(raw / math.sqrt(length))
        best = max(scores)
        if best <= 0:
            return [0.0] * n
        return [0.95 * s / best for s in scores]  # relative to the best candidate in this call
