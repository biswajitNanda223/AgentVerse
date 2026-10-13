---
name: steward
description: Repo conventions for driving AgentVerse pull requests to green (CI failures, review comments, merge conflicts). Read before acting on CI or review events for a PR in this repository.
---

# Steward: PR conventions for this repo

## Before every push

- Run `make check` (see the `check` skill). Do not push on red or unverified.
- If `pyproject.toml` files changed, run `uv lock` and commit `uv.lock`. Never edit `uv.lock`
  by hand; resolve lockfile conflicts by merging the base branch and re-running `uv lock`.
- Keep docs in the same PR as the code they describe; `make docs` must pass.

## CI failures

- `ruff`/`format`: run the fix commands and push.
- `mypy`: CI installs without optional extras. Reproduce with `uv sync --all-packages && uv run mypy`.
- `pytest`: reproduce locally first. Never skip, xfail or delete a test to get green.
- `images` matrix (Docker builds): Dockerfiles build from the repo root and use `uv sync --frozen
  --package <member>`. A frozen failure means `uv.lock` is stale; run `uv lock`.

## Conventions

- Merge the base branch into the PR branch; do not rebase or force-push shared branches.
- One logical change per PR. New agents come from `scripts/new_agent.py` (`add-agent` skill).
- Do not widen a PR to fix unrelated failures; say what is failing and propose a patch.
- Never include credentials, personal data or unrestricted prompt content in code, tests or docs.
