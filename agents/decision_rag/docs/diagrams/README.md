# Diagrams

`.mmd` files are the Mermaid sources. The same diagrams are embedded in the Markdown docs (GitHub
renders them), and `../images` holds rendered PNG and SVG copies for viewers that do not.
`tests/test_docs.py` fails if a diagram embedded in a doc differs from its source here.

| File | Shows |
|---|---|
| 01-capability-asymmetry | classical retrieval bottleneck vs a decision model |
| 02-corpus-hierarchy | the topic, document, section, passage tree for a query |
| 03-navigation-sequence | one navigation: per-level joint judgment, pruning, ranking |
| 04-architecture | modules, entry points, the decision-model port, Jev |
| 05-joint-vs-independent | one shared context vs n isolated ones |
| 06-tournament | judging more candidates than fit one context |
| 07-pruning-rules | keep, widen, rank, abstain |
| 10 to 12-trace-* | **generated** from real runs by `--mermaid` |

## Regenerate the traces

```bash
uv run python -m decision_rag "How do Kafka clients authenticate to Event Hubs?" --mermaid docs/diagrams/10-trace-kafka-event-hubs.mmd
uv run python -m decision_rag "What should I do with a poison message that retries cannot fix?" --mermaid docs/diagrams/11-trace-dead-letter.mmd
uv run python -m decision_rag "what is the airspeed of a swallow" --mermaid docs/diagrams/12-trace-abstain.mmd
```

## Re-render the images

With Node and Chromium available, Mermaid CLI renders any `.mmd`:

```bash
npx -p @mermaid-js/mermaid-cli mmdc -i docs/diagrams/04-architecture.mmd -o docs/images/04-architecture.png -s 2
```
