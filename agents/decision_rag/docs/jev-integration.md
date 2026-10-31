# Using TypeSafe Jev as the decision model

[`jev.py`](../src/decision_rag/jev.py) turns "judge these candidates" into one Jev request. It
uses **only the `noul` question type** (a yes/no probability), because that is the type with
documented fields, which keeps the unverified surface as small as possible.

## The request

```json
{
  "model": "jev-latest",
  "state": {
    "query": "How do Kafka clients authenticate to Event Hubs?",
    "candidates": {
      "C0": "Messaging: Documents: Kafka consumer groups [...]; Azure Event Hubs [...]",
      "C1": "Retrieval: Documents: Hybrid retrieval [...]",
      "C2": "Agents: Documents: ADK tools [...]"
    }
  },
  "questions": {
    "c0": {"type": "noul", "instructions": "Candidate C0 contains information needed to answer the query."},
    "c1": {"type": "noul", "instructions": "Candidate C1 contains information needed to answer the query."},
    "c2": {"type": "noul", "instructions": "Candidate C2 contains information needed to answer the query."}
  }
}
```

`POST https://api.typesafe.ai/v1/systemone` with `Authorization: Bearer <key>`. The answer for
each question is read as a probability from `noul` (a `probability` alias is also accepted),
either at the top level or under an `answers` key, and must be a number within 0 to 1.

## Joint vs independent

| Mode | Requests per level | Context per question | Use |
|---|---|---|---|
| `joint` (default) | 1 | the query and **every** candidate | the technique as intended |
| `independent` | one per candidate | the query and **only that** candidate | ablation: measure what joint judging buys |

Independent mode costs `n` requests per level instead of 1, so use it only to evaluate.

## What is verified and what is not

| Item | Status |
|---|---|
| endpoint, bearer auth, `model`, `state`, `questions` keyed by name | from TypeSafe's published reference |
| `noul` question as `{"type": "noul", "instructions": ...}` | from TypeSafe's published reference |
| a probability in `noul` (or `probability`), envelope top-level or under `answers` | from secondary write-ups; not confirmed against the official page |
| state as a JSON object with `query` and `candidates` | allowed (state may be text or JSON); the particular field names are this example's choice |
| model id `jev-latest` | an example id; pin the current one from TypeSafe |

The official reference could not be opened when this was written (the sandbox had no access to
it), so confirm against <https://docs.typesafe.ai/api/system-one> before relying on it. If the
shape differs, change `JevDecisionModel._request` and `_decode`; the navigator never sees HTTP.

## Failure behaviour

Any non-200, timeout, non-JSON body, missing answer, non-numeric or out-of-range value raises
`DecisionModelError`. Error messages contain only the status or exception type, never the query,
candidate text or response body (the corpus may be confidential). The pipeline then abstains
instead of guessing.

## First live run checklist

1. `export DECISION_RAG_BACKEND=jev DECISION_RAG_API_KEY=...`
2. `uv run python -m decision_rag "<question>" --trace`. A `decision_model_unavailable` reason
   means the call failed or the shape differed; the message names the status or the field.
3. Adjust `jev.py` and `tests/test_jev.py` if the real response differs.
4. Run [the evaluation](evaluation.md) with `joint` and with `independent`.

## Cost and privacy

Joint mode sends the query plus all candidate descriptions of a level (up to
`MAX_CANDIDATES_PER_CALL`) in one request, so four requests per query on a four-level corpus.
Descriptions and passage text leave your boundary; do not use a hosted model on data you could
not send to any other API.
