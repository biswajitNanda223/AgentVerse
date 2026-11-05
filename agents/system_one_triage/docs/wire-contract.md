# Wire contract (read before using real Jev)

All HTTP details live in `src/system_one_triage/wire.py`. This page records what is solid and
what is an assumption, because only part of it could be checked against the vendor's own
documentation when this example was written.

## Confirmed from TypeSafe's documentation

- `POST https://api.typesafe.ai/v1/systemone`
- `Authorization: Bearer <key>` and `Content-Type: application/json`
- Body fields `model` (for example `jev-latest`), `state`, and `questions`
- `questions` is an object keyed by your question name
- A `noul` question is `{"type": "noul", "instructions": "..."}`
- State may be plain text or JSON

## Assumed from secondary sources, to be verified

| Item | Assumption in this code |
|---|---|
| Choice question | `{"type": "choice", "instructions": "...", "criteria": {label: description}}` |
| Score question | `{"type": "score", "instructions": "...", "criteria": [level, ...]}` ordered low to high |
| Choice answer | `{"choice": label, "probabilities": {label: p}, "confidence": c}` |
| Score answer | `{"score": x, "probabilities": {...}, "confidence": c}` with `x` in `0 .. len(levels)-1` |
| Noul answer | `{"noul": p}`, with `{"probability": p}` accepted as an alias seen on a gateway |
| Answer envelope | keyed by question name, either at the top level or under `"answers"` |

If TypeSafe's reference says otherwise, update `encode_request` / `_decode_one` and the matching
cases in `tests/test_wire.py`. Nothing outside `wire.py` knows these names.

## Fail-closed decoding

`decode_response` raises `WireFormatError` when an answer is missing, names an option that was
not offered, has a probability outside 0..1, probabilities that do not sum to 1 (tolerance
0.05), a score outside the rubric, or a non-numeric value. The router turns that into a System
Two fallback. If the real score scale is 1-based, every score will be rejected on the first
live call, which is deliberate: a loud failure beats silently mis-scoring.

## First live run checklist

1. Set `SYSTEM_ONE_BACKEND=jev` and a key, run `python -m system_one_triage "<a ticket>"`.
2. If the reason is `system_one_unavailable`, the `error` field in `facts` names the HTTP status
   or the decoding problem. It never contains your ticket text.
3. Compare the real request/response with the table above and adjust `wire.py` and its tests.
4. Run `uv run pytest agents/system_one_triage` and `make check`.
