# Attachment-derived engineering requirements

The supplied archive contained nine LinkedIn screenshots. They are not treated as
authoritative technical documentation; they were used as design prompts. The screenshots
were reviewed on 2026-09-20 and led to these explicit requirements:

| Observation in attachment | Concrete repository response |
|---|---|
| Failure taxonomies survive framework churn | `docs/production-guide.md` separates retrieval, generation, tool and orchestration failures. |
| RAG quality depends on chunks, retrieval, context and evaluation | Executable chunkers, score/fusion logic, citations and retrieval tests. |
| CRAG grading must see query plus chunk | `CorrectiveRag` grades a `RetrievalCandidate` against the original query. |
| Resumption can replay side effects | Idempotency keys and checkpoint guidance at every external-write boundary. |
| Parallelism is safe for partitioned outputs, unsafe for one shared decision | Coordinator fans out reads; one synthesizer owns the final answer. |
| Tool payloads bloat context | Store full results in traces/object storage; pass bounded summaries into model context. |
| Network sandboxing without provenance is insufficient | Request/tenant/agent/tool lineage is part of the telemetry and citation model. |
| RAG flow: ingest, index, retrieve, augment, generate | Implemented as separate interfaces so every stage can be tested and replaced. |

The expanded implementation directly encodes each observation: query-aware CRAG grading,
monotonic checkpoints, tenant-scoped idempotency, single-writer parallel grouping, payload
compaction with an external artifact reference, approval policies and provenance-bearing chunks.

Raw screenshots are intentionally ignored by Git to avoid republishing social-media and
third-party visual content. Keep the original archive outside the repository.
