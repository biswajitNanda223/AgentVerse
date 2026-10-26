# Concepts

## System One and System Two

| | System One (Jev) | System Two (the ADK agent here) |
|---|---|---|
| Output | typed values: choice, score, probability | generated text and tool calls |
| Good at | fast gut-check judgments your code consumes | multi-step reasoning, tool use, explanation |
| Cost shape | one small request answers many questions in parallel | one or more LLM turns |
| Failure mode | a confident but wrong label; a misread payload | slow, variable, can wander |

The pattern is a cascade: ask System One first; if it is confident and the case is low-risk, act
in code; otherwise escalate to System Two (or a human). The ADK agent in this folder is the
escalation target and also calls the same triage as a tool.

## The three question types

| Type | You provide | You get | Used here for |
|---|---|---|---|
| Choice | instructions plus labelled options | the chosen label, a probability per option, confidence | `category` |
| Score | instructions plus an ordered rubric | a position on the rubric, a probability per level, confidence | `urgency` |
| Noul | a statement that is or is not true | a probability from 0 to 1 that it is true | `security_incident`, `contains_pii` |

## Decompose, then compose in code

Each question should be answerable in seconds by a knowledgeable person with the right context.
"Triage this ticket" is not; these are:

1. What category is this? (choice)
2. How urgent is it for the customer? (score)
3. Does it suggest a security incident? (noul)
4. Does it contain personal data? (noul)

`triage.decide()` then applies explicit rules and a priority formula:

```text
priority = 0.7 * (urgency / top_level) + 0.3 * P(security_incident)
```

Changing how much security matters is editing `0.3`, with a test, in a normal code review.

## Using probabilities and confidence

- Treat `confidence` as the gate for *acting*: below `min_category_confidence` the ticket goes
  to System Two.
- Treat risk probabilities asymmetrically. A 0.5 threshold on `security_incident` accepts some
  false alarms to avoid missing real incidents; tune it from data, not intuition.
- Noul answers may not carry a confidence in every deployment; the types allow `None`.

## Failure semantics

System One is a dependency like any other. The router never returns "auto" on a failed or
unreadable call: it falls back to System Two with the reason `system_one_unavailable`.
