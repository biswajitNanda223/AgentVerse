# Algorithm

All of it lives in [`navigator.py`](../src/decision_rag/navigator.py). Constants are in
`NavigationConfig`.

## Navigation

```text
frontier = [root]
repeat until no frontier branch has children:
    candidates = every child of every frontier branch
    p = decision_model.judge(query, candidates)        # ONE joint judgment (see tournament)
    keep = candidates with p >= min_probability, best first
    if keep is empty: keep = best candidates anyway    # no signal: widen, do not guess
    frontier = keep[:beam_width]
rank the passages reached by  geometric_mean(p along the path)
abstain if the best passage's last p < abstain_below, or none was reached
return top_k
```

```mermaid
flowchart TD
  Start["Candidates judged: p for each"] --> Any{"any p >= min_probability?"}
  Any -->|"yes"| KeepQ["keep those that qualify"]
  Any -->|"no signal"| Widen["WIDEN: keep top beam_width anyway<br/>do not commit to one arbitrary branch"]
  KeepQ --> Cap["cap at beam_width, best first"]
  Widen --> Next
  Cap --> Next{"any kept branch has children?"}
  Next -->|"yes"| Down["expand children: next step"]
  Next -->|"no: all are passages"| Rank["rank passages by geometric mean<br/>of probabilities along the path"]
  Rank --> Abst{"best passage p < abstain_below?"}
  Abst -->|"yes"| No["abstain: no answer from weak evidence"]
  Abst -->|"no"| Yes["return top_k passages with citations"]
  classDef ok fill:#d7f0dd,stroke:#2e7d32,color:#000
  classDef bad fill:#fde2e2,stroke:#c0392b,color:#000
  classDef mid fill:#fff3c4,stroke:#b8860b,color:#000
  class Yes,KeepQ ok
  class No bad
  class Widen mid
```

### Why a probability product, not a sum

A passage is only useful if every ancestor was plausibly right, so the path score is the
**geometric mean** of the probabilities from topic to passage (the mean of logs, exponentiated).
One very unlikely ancestor drags it down; depth does not penalise it, because it is a mean, not a
raw product. The final passage probability is used separately for the abstain decision, so a
strong path to a weak passage still abstains.

### Why widen instead of picking one branch

If every candidate scores near zero, the model is saying "I cannot tell from these descriptions".
Committing to the single highest score would be an arbitrary bet that cannot be undone. Keeping
the top `beam_width` costs one extra level of judging and usually recovers, as in the poison
message trace in the [README](../README.md).

## Cost

One decision-model call per level when a level fits in a context. With depth `d`, a query makes
`d` calls (4 here), independent of corpus size. Latency is `d` times the model latency, plus the
tournament rounds below on wide levels.

## The tournament for oversized candidate sets

A real corpus can have thousands of documents under a topic, more than fits one context.
`max_candidates_per_call` bounds a single judgment. Larger sets run as a tournament:

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
true joint judgment) at the cost of a few extra calls. It is this example's design; the paper's
treatment of very wide levels was not available when this was written.

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

There is no embedding index, but the model can only judge what it is shown. Each branch is shown
as `breadcrumb: description`, where the description is extractive:

- topic: its documents with their section titles
- document: its sections, each with the opening of its first passage
- section: the opening of its first passage
- passage: the passage text

If navigation misses, look at the trace for the level where the right branch got a low
probability, then improve that branch's title or description (or switch to a stronger model).

## Failure handling

| Event | Behaviour |
|---|---|
| decision model errors, times out or answers an invalid shape | `DecisionModelError`; the pipeline abstains with `decision_model_unavailable` |
| wrong number of judgments, or a probability outside 0..1 | `DecisionModelError` (validated before use) |
| no passage reached | abstain |
| best passage below `abstain_below` | abstain (`low_relevance`), no citations |

## Complexity and limits

- Memory: the whole tree is held in memory; for very large corpora, build the tree lazily or
  shard by topic.
- A leaf-level tie is broken by the last probability, then by order.
- The trace records every candidate, so its size is the number of candidates judged, not just
  the ones kept.
