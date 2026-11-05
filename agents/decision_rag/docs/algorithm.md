# Algorithm

All of it lives in [`navigator.py`](../src/decision_rag/navigator.py). Constants are in
`NavigationConfig`. The pipeline is the one in the paper's Figure 2(c); items marked **this
example** are additions that the figure does not show.

```mermaid
flowchart LR
  Q(["Query q"]) --> C[("Corpus")]
  C -.->|"optional higher-order levels<br/>e.g. categories: keep top few"| Docs
  C --> Docs["Documents D1 ... DN<br/>1 DOCUMENT SCREENING<br/>one yes/no question per document<br/>judged together in ONE forward pass<br/>keep top k"]
  Docs -->|"kept documents only"| Pass["Passages of the kept documents<br/>2 PASSAGE SCORING<br/>one yes/no question per passage<br/>one forward pass<br/>keep top r"]
  Docs -.->|"pruned documents:<br/>never expanded, never scored"| Gone["pruned"]
  Pass --> Top["Top r passages"]
  Top -->|"optional"| Choice["3 CHOICE RERANKING<br/>ONE multiple-choice question<br/>options = the r passages<br/>final ranking"]
  Top -->|"without reranking"| Gen
  Choice --> Gen["Generator LLM<br/>answers from the passages"]
  classDef stage fill:#d7f0dd,stroke:#2e7d32,color:#000
  classDef opt fill:#fff3c4,stroke:#b8860b,color:#000
  classDef gone fill:#eeeeee,stroke:#9e9e9e,color:#777,stroke-dasharray:4 3
  classDef io fill:#dbe8ff,stroke:#2f5fb3,color:#000
  class Docs,Pass stage
  class Choice opt
  class Gone gone
  class Q,C,Top,Gen io
```

## Stages

1. **Optional higher-order levels** (for example categories or topics): one joint judgment over
   the corpus's top-level groups, keep `keep_topics`. If the corpus has only one group the model is
   not called at all (this example).
2. **Document screening**: one yes/no question per document under the kept groups, all in a single
   shared context, so one decision-model call. Keep the top **k** (`keep_documents`).
3. **Passage scoring**: one yes/no question per passage of the **kept documents only**, again one
   call. Pruned documents are never expanded, so their passages are never scored. Keep the top
   **r** (`keep_passages`).
4. **Optional choice reranking** (`rerank=True`): one multiple-choice question whose options are
   the r passages; the returned distribution gives the final order. Needs a model that implements
   `choose()`.

Sections sit between documents and passages in the tree. By default they are folded away
(`skip_sections=True`): passage scoring sees the passages of a kept document directly, with the
section title still in each candidate's breadcrumb. Set `skip_sections=False` to judge sections as
their own stage.

```text
frontier = [root]
for each stage (topics, documents, [sections], passages):
    candidates = children of every branch in the frontier (skipped kinds looked through)
    p = decision_model.judge(query, candidates)          # ONE joint judgment (see tournament)
    keep = top k (top r at the passage stage), best first
    frontier = keep                                      # pruned branches are never expanded
if rerank:  order = decision_model.choose(query, kept passages)   # ONE multiple-choice question
else:       order = kept passages by their own P(yes)
abstain if the best passage's P(yes) < abstain_below, or none was reached      # this example
```

```mermaid
flowchart TD
  Start["Stage candidates judged: P(yes) for each"] --> Floor{"optional floor set<br/>and nobody reaches it?"}
  Floor -->|"yes: no signal"| Widen["WIDEN: keep the top few anyway<br/>do not commit to one arbitrary branch"]
  Floor -->|"no"| Top["keep the top k documents<br/>(top r passages at the last stage)"]
  Widen --> Next
  Top --> Next{"stage was passages?"}
  Next -->|"no"| Down["expand ONLY the kept branches<br/>pruned ones are never scored"]
  Next -->|"yes"| Rerank{"choice reranking on?"}
  Rerank -->|"yes"| Choose["one multiple-choice question over the r passages<br/>order by choice probability"]
  Rerank -->|"no"| Order["order by passage P(yes)"]
  Choose --> Abst
  Order --> Abst{"best passage P(yes) < abstain_below?"}
  Abst -->|"yes"| No["abstain: no answer from weak evidence"]
  Abst -->|"no"| Yes["return passages with citations"]
  classDef ok fill:#d7f0dd,stroke:#2e7d32,color:#000
  classDef bad fill:#fde2e2,stroke:#c0392b,color:#000
  classDef mid fill:#fff3c4,stroke:#b8860b,color:#000
  class Yes,Top ok
  class No bad
  class Widen,Choose mid
```

### The keep rule

The figure's rule is "keep top k": no probability threshold. That is the default
(`min_probability=0`). **This example** adds an optional floor; if you set one and no candidate
reaches it, the top candidates are kept anyway, because "nothing looks relevant" means widen, not
commit to one arbitrary branch.

### Ranking

Passages are ordered by their own yes/no probability, or by the choice probability when reranking
is on. The paper's text that was available does not describe any path-level combination, so none is
used.

### Abstaining

Not in the paper. If the best passage's P(yes) is below `abstain_below`, the pipeline returns no
answer instead of the nearest weak match.

## Cost

One decision-model call per stage when the stage fits in a context. For a corpus with categories
that is up to three calls (categories, documents, passages), plus one for the optional rerank,
independent of corpus size. A step with only one candidate needs no call: it inherits its parent's
probability, because no evidence was gathered (the trace shows `0 call(s)`). With a single topic
and no rerank, a query costs two calls.

## Choice reranking vs yes/no scoring

Passage scoring asks each passage "is this relevant?" independently of the others' answers, even
though they share a context. Choice reranking asks one question, "which of these answers the
query?", so the model must trade the passages off against each other. The paper's Figure 2 lists
it as optional. The rerank costs one extra call over only r passages.

## The tournament for oversized candidate sets (this example)

A real corpus can have thousands of documents, more than fits one context. `max_candidates_per_call`
bounds a single judgment. Larger sets run as a tournament:

```mermaid
flowchart TD
  All["Oversized candidate set<br/>n > max_candidates_per_call"] --> Split["Split into chunks<br/>each fits one context"]
  Split --> J1["Chunk 1: joint judgment"]
  Split --> J2["Chunk 2: joint judgment"]
  Split --> Jk["Chunk k: joint judgment"]
  J1 -->|"best few advance"| Surv["Survivors from every chunk"]
  J2 -->|"best few advance"| Surv
  Jk -->|"best few advance"| Surv
  Surv --> Q{"survivors fit<br/>one context?"}
  Q -->|"no"| Split
  Q -->|"yes"| Final["FINAL joint judgment<br/>probabilities used for pruning"]
  Final --> Out["kept branches (others recorded as 'pruned early')"]
  classDef step fill:#dbe8ff,stroke:#2f5fb3,color:#000
  classDef final fill:#d7f0dd,stroke:#2e7d32,color:#000
  class Split,J1,J2,Jk,Surv step
  class Final,Out final
```

Only the survivors of the last round get a probability, and the trace marks the rest
`pruned early`. This keeps every probability that drives pruning comparable (the final round is a
true joint judgment) at the cost of a few extra calls. The paper's treatment of very wide stages
was not available when this was written.

## Joint vs independent judgments

```mermaid
flowchart LR
  subgraph Joint["Joint judgment (default): comparable probabilities"]
    direction TB
    JS["state = query + ALL candidates<br/>C0 ... Cn in one context"] --> JR["ONE request<br/>n yes/no questions in parallel"]
    JR --> JP["p0 ... pn<br/>every candidate was seen<br/>next to every other"]
  end
  subgraph Indep["Independent judgment (ablation): n separate contexts"]
    direction TB
    I0["request 0: query + C0 only"] --> IP0["p0"]
    I1["request 1: query + C1 only"] --> IP1["p1"]
    In["request n: query + Cn only"] --> IPn["pn"]
  end
  JP --> JV["Rank and prune on p<br/>differences are meaningful"]
  IP0 --> IV["Rank and prune on p<br/>each p was judged in isolation,<br/>so scales can drift"]
  IP1 --> IV
  IPn --> IV
  classDef good fill:#d7f0dd,stroke:#2e7d32,color:#000
  classDef warn fill:#fff3c4,stroke:#b8860b,color:#000
  class JS,JR,JP,JV good
  class I0,I1,In,IP0,IP1,IPn,IV warn
```

The navigator always asks the decision model to judge a *set*. Whether that set is evaluated in
one context or one-by-one is the model adapter's choice, which is what makes the ablation a
configuration switch (`DECISION_RAG_JUDGEMENT`) rather than a code change.

## Descriptions are the index

There is no embedding index, but the model can only judge what it is shown. Each candidate is shown
as `breadcrumb: description`, where the description is extractive:

- topic: its documents with their section titles
- document: its sections, each with the opening of its first passage
- passage: the passage text, with its section title in the breadcrumb

If navigation misses, look at the trace for the stage where the right branch got a low
probability, then improve that branch's title or description, raise k, or use a stronger model.

## Failure handling

| Event | Behaviour |
|---|---|
| decision model errors, times out or answers an invalid shape | `DecisionModelError`; the pipeline abstains with `decision_model_unavailable` |
| wrong number of judgments, or a probability outside 0..1 | `DecisionModelError` (validated before use) |
| choice distribution of the wrong length, outside 0..1, or not summing to 1 | `DecisionModelError` |
| `rerank=True` with a model that cannot `choose()` | `ValueError` at construction |
| no passage reached | abstain |
| best passage below `abstain_below` | abstain (`low_relevance`), no citations |

## Limits

- The whole tree is held in memory; for very large corpora, build it lazily or shard by topic.
- Pure top-k always keeps k candidates, even when all are irrelevant. That costs extra passage
  scoring but never prunes the right branch for lack of a threshold.
- The trace records every candidate judged, so its size is the number of candidates, not only the
  kept ones.
