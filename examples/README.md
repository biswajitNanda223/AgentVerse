# Runnable examples

Every example imports the production-shaped implementation from `src/agentverse`; algorithms
are not copied into notebooks. Run any example from the repository root:

```bash
uv run python examples/rag/01_naive/example.py
uv run python examples/chunking/05_semantic/example.py
```

The examples use deterministic local models and in-memory stores so they run without cloud
credentials. Replace these through the documented protocols only after adding retrieval and
answer-quality evaluations.

