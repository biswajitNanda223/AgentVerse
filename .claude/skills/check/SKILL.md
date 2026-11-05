---
name: check
description: Run the full AgentVerse quality gate (ruff, mypy, security eval, docs links, tests) and report failures. Use before committing, before pushing, or when asked to verify the repo.
---

# Check the repo

From the repository root:

```bash
uv sync --all-packages --all-extras
make check
```

`make check` runs, in order: `ruff check`, `ruff format --check`, `mypy` (strict, all members),
the production-security evaluation gate, the Markdown link check (`scripts/check_docs.py`), and
the whole pytest suite with coverage. CI runs the same steps without `--all-extras`, so for a
change that touches optional dependencies (rag, ocr) also run:

```bash
uv sync --all-packages && make lint typecheck test
```

## Fixing failures

- Lint or format: `uv run ruff check . --fix && uv run ruff format .`, then re-run.
- mypy complaining about an optional library: it belongs in the `[[tool.mypy.overrides]]` list in
  the root `pyproject.toml`; do not add `# type: ignore` that only works in one environment.
- Docs check: fix the broken relative link or unterminated code fence it names.
- A failing test is a finding: fix the cause, never skip or delete the test.

## Diagrams

If you edited a Mermaid block, confirm it renders: paste it into the Mermaid live editor, or run
a Mermaid CLI/`mermaid.parse` check if available. GitHub renders Mermaid, so a syntax error
shows as a broken diagram on the page.

Report results plainly: which step failed, with the output, or that everything passed.
