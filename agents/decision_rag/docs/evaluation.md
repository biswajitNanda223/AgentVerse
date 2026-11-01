# Evaluating DecisionRAG honestly

## What the harness does

`uv run python -m decision_rag.evaluate` runs the golden questions in
[`sample_corpus.py`](../src/decision_rag/sample_corpus.py) through the navigator and through a flat
lexical retriever (the shared `agentverse` BM25-style retriever over every passage), and reports
Hit@1 (is the top passage exactly the expected one), decision-model calls per query, and latency.

## Reading the offline numbers

With the offline stand-in both sides are word-matchers, so the result checks that the machinery
works (one call per stage, sensible routing). It says nothing about whether DecisionRAG beats
retrieval: a flat word-matcher can win on a 17-passage corpus, and the stand-in cannot understand
paraphrases. `tests/test_evaluate.py` only guards against regressions (Hit@1 stays at or above 0.7 and
one call per stage).

## Measuring the real thing

1. **Build a labelled set.** 50 to 200 real questions, each with the passage (or document) that
   answers it. Include questions with no answer to test abstention.
2. **Point the harness at your corpus.** Load it with `load_markdown_corpus`, or add a loader for
   your format that returns a `CorpusTree`.
3. **Run four configurations on the same set:**

   | Run | Setting |
   |---|---|
   | screening + scoring, joint | `DECISION_RAG_BACKEND=jev` (or `claude`) |
   | the same with choice reranking | plus `DECISION_RAG_RERANK=true` |
   | independent judgments (ablation) | plus `DECISION_RAG_JUDGEMENT=independent` |
   | your current retriever | the baseline you would otherwise ship |
   | retriever plus reranker | if you use one |

   Also sweep **k** and **r** (`KEEP_DOCUMENTS`, `KEEP_PASSAGES`): the paper's pipeline trades
   recall against cost through them.

4. **Report** Hit@1 or R@1, Hit@k, abstention precision (of abstained questions, how many truly
   had no answer), model calls per query, p50 and p95 latency, and cost per query.
5. **Inspect misses with `--trace`.** Find the level where the right branch lost, then decide:
   better titles and descriptions, a wider beam, a different threshold, or a stronger model.

## Pitfalls

- Do not tune thresholds on the same questions you report. Hold out a test set.
- Vendor and paper numbers are claims until you reproduce them on your data and corpus structure.
- Track `joint` vs `independent` on your data: the paper reports a gain from judging jointly, and
  this is how you find out whether it holds for you.
- A hierarchy is only as good as its titles. Measure with your real headings, not cleaned ones.

## Regression tests that keep it honest

`tests/test_navigator.py` pins the behaviours that make the technique work (one joint call per
level, widening on no signal, tournament bounds, abstention). `tests/test_jev.py` pins the wire
format against a mock transport, including that joint mode is exactly one request.

## Evaluating with Claude (or Jev) on the Project SLM scenarios

```bash
export ANTHROPIC_API_KEY=...
DECISION_RAG_BACKEND=claude uv run python -m decision_rag.evaluate --suite project-slm
DECISION_RAG_BACKEND=claude uv run python -m decision_rag.evaluate            # built-in corpus
```

The suite asks 13 questions about the 60 scenarios (`slm_golden.py`) and counts a hit when the top
passage belongs to the expected scenario. Expect roughly 2 to 4 model requests per question, each
carrying one level's candidate descriptions (up to a few dozen short texts), so a full run is a few
dozen small requests. Estimate the bill from your model's current price before running, and try a
cheaper model first with `DECISION_RAG_CLAUDE_MODEL`.

What to compare, and what not to conclude:

- Compare the Claude run with the offline stand-in and the flat lexical baseline on the same
  questions, and look at the traces of every miss.
- Thirteen questions written by the same person who wrote the system is a smoke test. Build a
  larger labelled set from real user questions before drawing conclusions.
- Self-reported Claude scores are not calibrated: if abstention fires too often or never, tune
  `MIN_PROBABILITY` and `ABSTAIN_BELOW` on held-out questions.
