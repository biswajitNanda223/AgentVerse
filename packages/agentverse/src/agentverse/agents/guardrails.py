"""Simple deterministic boundaries; model-based guardrails may augment, never replace them."""

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class GuardrailResult:
    allowed: bool
    reason: str


_INJECTION_PATTERNS = (
    re.compile(r"ignore (all|any|the|previous) instructions", re.I),
    re.compile(r"reveal (the )?(system|developer) prompt", re.I),
    re.compile(r"exfiltrate|send .* secret", re.I),
)


def inspect_untrusted_content(text: str) -> GuardrailResult:
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(text):
            return GuardrailResult(False, "possible prompt injection in untrusted content")
    return GuardrailResult(True, "no deterministic injection marker detected")


def validate_citations(answer: str, citation_count: int) -> GuardrailResult:
    cited = {int(value) for value in re.findall(r"\[(\d+)]", answer)}
    if any(value < 1 or value > citation_count for value in cited):
        return GuardrailResult(False, "answer contains a citation not present in evidence")
    if answer.strip() and citation_count and not cited:
        return GuardrailResult(False, "grounded answer omitted citations")
    return GuardrailResult(True, "citation references are valid")
