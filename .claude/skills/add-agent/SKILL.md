---
name: add-agent
description: Scaffold a new ADK agent as a uv workspace member in this monorepo (agents/<name>) and register it in the root pyproject, Makefile and CI. Use when asked to add, create or scaffold a new agent.
---

# Add an agent to the AgentVerse monorepo

Every agent is an installable workspace member under `agents/<name>/` that depends on the shared
`agentverse` library. Do not hand-copy another agent: use the scaffolder so the root config stays
consistent.

## Steps

1. Pick a `snake_case` name (`^[a-z][a-z0-9_]{1,40}$`) and a one-line description.
2. Scaffold. The script validates every root edit before writing anything, so a failure leaves
   the tree untouched:
   ```bash
   python3 scripts/new_agent.py <name> "<description>"
   ```
3. Refresh the lockfile and environment, then format:
   ```bash
   uv lock && uv sync --all-packages --all-extras
   uv run ruff check . --fix && uv run ruff format .
   ```
4. Replace the placeholders:
   - `src/<name>/adk_agent.py`: real instruction and narrow, typed tools.
   - `Dockerfile`: replace the placeholder `ENTRYPOINT` with the real one (HTTP app, worker...).
   - `README.md`: design, run instructions, and a Mermaid diagram if the flow is non-trivial.
   - Add the agent to the root `README.md` ("Start here" table, structure tree, workspace diagram).
5. Write real tests (offline, no model key). The scaffold's one test only checks wiring.
6. Run `make check`; it must pass before you commit. Use the `check` skill.

## What the scaffolder edits

`pyproject.toml` (ruff known-first-party, mypy packages, pytest testpaths), `Makefile` and
`.github/workflows/ci.yml` (coverage flags), and the CI image matrix. It creates the member's
`pyproject.toml`, `README.md`, `agents-cli-manifest.yaml`, `Dockerfile`, `src/<name>/` and `tests/`.

## Rules

- Commit `uv.lock`; Docker builds use `--frozen`.
- Agents depend on `agentverse = {workspace = true}`; do not duplicate shared code between agents.
- Never put credentials in `.env.example`, fixtures or docs.
