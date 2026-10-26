# Extending and evaluating

## Add a question

1. Add it to `build_questions()` in `triage.py` with a narrow, one-judgment instruction.
2. Read the typed answer in `decide()` and use it in a rule or in the priority formula.
3. Add the new name to `local.py` if you want the offline stand-in to answer it (otherwise it
   raises, and tests using it should use a fake client like `BrokenClient` in `test_triage.py`).
4. Add a routing test that fails without your change.

Prefer adding a question over making one question broader: independent questions do not degrade
each other, and each can be tuned and audited separately.

## Tune thresholds from data

The defaults in `TriagePolicy` are starting points. To set them for real:

1. Collect a labelled sample of tickets (category, true urgency, was it a security incident).
2. Run the real backend over it and save `Decision.facts`.
3. For each threshold, sweep values and plot precision and recall (for example, of auto-handled
   tickets, what fraction landed in the right queue at each `min_category_confidence`).
4. Pick the lowest-risk operating point, record the sample size and date in the PR, and change
   the value in code.

Do not tune on the stand-in: its probabilities are not calibrated.

## Evaluate in CI

Keep a small golden set (a few dozen tickets with expected routes) and assert on it in a test
that uses recorded System One answers, so CI is deterministic and free. Re-record against the
live service on a schedule or before changing thresholds, and review the diff.

## Operational notes

- Timeouts default to 5 seconds (`SYSTEM_ONE_TIMEOUT_SECONDS`); a timeout falls back to System
  Two rather than retrying inline.
- The hosted model is early access; the model id (`SYSTEM_ONE_MODEL`) is configurable so you
  can pin a specific version once one is published.
- Vendor performance and accuracy figures are marketing claims until you measure them on your
  own data.
