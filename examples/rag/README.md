# RAG examples

| Directory | Pattern | Production decision it demonstrates |
|---|---|---|
| `01_naive` | lexical baseline | establish a measurable baseline first |
| `02_dense` | vector similarity | semantic recall behind an embedder interface |
| `03_hybrid` | dense + lexical RRF | exact and semantic recall without score coupling |
| `04_reranked` | retrieve wide, rerank narrow | spend extra latency only on a small candidate set |
| `05_parent_child` | child search, parent context | precise matching with sufficient answer context |
| `06_multi_query` | query expansion and fusion | improve ambiguous-query recall with bounded variants |
| `07_hyde` | hypothetical document retrieval | bridge question/document representation gaps |
| `08_crag` | relevance grading and rewrite | correct weak retrieval using the original query |
| `09_self_adaptive` | conditional retrieval/routing | avoid expensive retrieval when it is unnecessary |
| `10_agentic_federated` | bounded multi-source plan | parallel independent reads and one final synthesis |
| `11_graph` | relation traversal | answer entity/relation questions with source evidence |
| `12_multimodal` | representation late fusion | retrieve source images/pages through captions/OCR |
| `13_conversational` | history condensation | retrieve with a standalone question, not raw history |
| `14_sql_temporal` | structured/freshness retrieval | allowlisted SQL and time-aware ranking |

All examples run without model credentials. The local hash embedder is a teaching substitute,
not a production embedding model.

