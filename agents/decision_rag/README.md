# DecisionRAG: retrieval by navigating, not searching

A runnable implementation of the idea in **"Retriever-Free Retrieval: Navigating Documents with
Decision Models"** (Wan, Jünger, Du, Liu, Krishnan, Weinberger; arXiv:2610.35868v1 [cs.AI],
26 Oct 2026). Instead of scoring every passage with BM25 or an embedding index, a *decision model*
walks the corpus the way a person browses a library: from broad topics, to documents, to
sections, to the individual passage, deciding at each level which branches are worth opening.

> **Read this first.** This folder was written from the title, abstract, Figure 1 and the first
> pages of the paper (the parts available when it was built), not from the full text. The core
> idea below is the paper's. Anything else (beam search, the tournament for oversized candidate
> sets, geometric-mean ranking, thresholds) is **this example's own design** and is labelled as
> such. The paper's reported numbers are quoted, not reproduced: no benchmark was run here.

```mermaid
flowchart TB
  subgraph Classical["(a) Classical retrieval"]
    direction LR
    C1[("Large corpus")] -->|"all passages"| R1["Simple retriever<br/>BM25 or fixed embeddings<br/>BOTTLENECK"]
    R1 -->|"only what it found"| G1["Powerful LLM<br/>cannot recover what<br/>the retriever missed"]
  end
  subgraph Decision["(b) DecisionRAG"]
    direction LR
    C2[("Large corpus")] -->|"topics, documents,<br/>sections, passages"| D2["Decision model<br/>as capable as the generator<br/>judges branches jointly"]
    D2 -->|"best passages + path"| G2["Powerful LLM<br/>answers from evidence"]
  end
  Classical ~~~ Decision
  classDef weak fill:#fde2e2,stroke:#c0392b,color:#000
  classDef strong fill:#d7f0dd,stroke:#2e7d32,color:#000
  classDef store fill:#dbe8ff,stroke:#2f5fb3,color:#000
  class R1 weak
  class D2,G1,G2 strong
  class C1,C2 store
```

## The idea in five points

1. **Capability asymmetry.** A strong generator cannot recover what a weak retriever never
   surfaced. Retrieval is the bottleneck.
2. **Decision models fix the asymmetry.** A decision model (the paper cites TypeSafe's Jev) takes a
   context and a set of questions and returns, for each, a probability distribution over answer
   options (for yes/no, `P(yes)`) in **one forward pass, generating no tokens**.
3. **Judge candidates together.** Putting all candidates in one shared context makes their
   relevance estimates *comparable*. The paper reports this contributes up to 7.7 points over
   judging them independently. This folder lets you test that on your data
   ([joint vs independent](docs/jev-integration.md)).
4. **Navigate the structure the corpus already has.** Topics, document titles, sections,
   passages. One decision per level, so latency is a handful of fast calls, not an agentic loop of
   generated tokens.
5. **No first-stage retriever, no precomputed index, no task-specific training.**

Paper-reported results (not reproduced here): +13.8 R@1 over dense retrieval with an 8B reranker on
MultiDoc2Dial, +17.4 Hit@1 on Natural Questions, and 0.7 to 1.8 seconds per query across four
benchmarks including a 2.68 million paragraph Wikipedia corpus.

## How it works

```mermaid
flowchart TD
  Q(["Query: How do Kafka clients<br/>authenticate to Event Hubs?"])
  Q --> M["Messaging (topic)"]
  Q --> R["Retrieval (topic)"]
  Q --> A["Agents (topic)"]
  M --> M1["Kafka consumer groups (document)"]
  M --> M2["Azure Event Hubs (document)"]
  M --> M3["Dead-letter queues (document)"]
  M2 --> S1["Kafka compatibility (section)"]
  M2 --> S2["Capture and retention (section)"]
  S1 --> P1["Passage 1: port 9093, SASL_SSL,<br/>username $ConnectionString"]
  S1 --> P2["Passage 2: each Kafka topic<br/>maps to an event hub"]
  R --> R1["3 documents ..."]
  A --> A1["3 documents ..."]
  M1 --> M1a["2 sections ..."]
  M3 --> M3a["1 section ..."]
  classDef topic fill:#dbe8ff,stroke:#2f5fb3,color:#000
  classDef doc fill:#e8e0f7,stroke:#6a4fb3,color:#000
  classDef sec fill:#ffeccc,stroke:#c77c0e,color:#000
  classDef pas fill:#fff3c4,stroke:#b8860b,color:#000
  classDef more fill:#f4f4f4,stroke:#bbb,color:#777,stroke-dasharray:4 3
  class M,R,A topic
  class M1,M2,M3 doc
  class S1,S2 sec
  class P1,P2 pas
  class R1,A1,M1a,M3a more
```

```mermaid
sequenceDiagram
  autonumber
  participant U as Caller
  participant N as DecisionNavigator
  participant T as CorpusTree
  participant M as Decision model
  U->>N: navigate(query)
  loop one iteration per level (topic, document, section, passage)
    N->>T: children of every branch still alive
    T-->>N: candidates (breadcrumb + description each)
    Note over N,M: ONE joint judgment: all candidates share one context
    N->>M: judge(query, candidates)
    M-->>N: P(relevant) for each candidate, comparable to each other
    N->>N: keep top beam_width with p >= min_probability<br/>(none qualify: widen, keep top beam_width anyway)
    N->>N: record StepTrace (kept and pruned candidates)
  end
  N->>N: rank surviving passages by geometric mean of path probabilities
  alt best passage p below abstain_below, or none reached
    N-->>U: abstained=true
  else
    N-->>U: top_k passages + citations + full trace
  end
```

Every level is **one joint judgment**: all candidates, one context, one decision-model call. A
four-level corpus costs four calls however large it is, which is why the technique is fast. The
pruning rules, including what happens when the model sees nothing relevant and when to abstain:

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

## Quick start

No key or network is needed; the default decision model is an offline lexical stand-in.

```bash
make install
uv run python -m decision_rag "How do Kafka clients authenticate to Event Hubs?"
uv run python -m decision_rag "What should I do with a poison message that retries cannot fix?" --trace
uv run python -m decision_rag "..." --mermaid trace.mmd      # the navigation as a diagram
uv run python -m decision_rag.evaluate                       # golden-set check
uv run pytest agents/decision_rag
```

Output of the first command (real, from the offline stand-in):

```json
{
  "abstained": false,
  "reason": null,
  "answer": "Event Hubs exposes a Kafka endpoint on port 9093, so Kafka clients connect with SASL_SSL and the username $ConnectionString plus an Event Hubs connection string.",
  "citations": [
    {
      "path": "Messaging > Azure Event Hubs > Kafka compatibility > Passage 1",
      "probability": 0.95
    },
    {
      "path": "Messaging > Azure Event Hubs > Kafka compatibility > Passage 2",
      "probability": 0.947
    },
    {
      "path": "Messaging > Azure Event Hubs > Capture and retention > Passage 1",
      "probability": 0.479
    }
  ]
}
```

### Watch it navigate

`--trace` prints every candidate the model judged at each level:

```text
step 1: 3 candidates, 1 call(s)
  KEEP 0.00  [topic] Messaging
  KEEP 0.00  [topic] Retrieval
  KEEP 0.00  [topic] Agents

step 2: 9 candidates, 1 call(s)
  KEEP 0.95  [document] Dead-letter queues
       0.19  [document] Human approval
       0.13  [document] Kafka consumer groups
       0.00  [document] Azure Event Hubs
       0.00  [document] Hybrid retrieval
       0.00  [document] Chunking strategies
       0.00  [document] GraphRAG
       0.00  [document] ADK tools
       0.00  [document] A2A delegation

step 3: 1 candidates, 1 call(s)
  KEEP 0.95  [section] When to dead-letter

step 4: 2 candidates, 1 call(s)
  KEEP 0.95  [passage] Send a message to the dead-letter topic when re…
       0.00  [passage] Store the failure reason and attempt count with…

4 decision-model call(s) in 3 ms
```

The same run as a diagram (`--mermaid`). Green was kept, grey was pruned, gold is the answer,
dotted edges are pruned branches. Note step 1: no topic looked relevant (`p=0.00`), so the
navigator **widened the beam** and kept all three instead of betting on one; the joint judgment at
the document level then found the right branch.

![Navigation trace: poison message](docs/images/11-trace-dead-letter.png)

A confident run, and one that abstains:

![Navigation trace: Event Hubs](docs/images/10-trace-kafka-event-hubs.png)

![Navigation trace: abstained](docs/images/12-trace-abstain.png)

Every diagram in this folder is also available as a rendered PNG and SVG in
[docs/images](docs/images) (sources in [docs/diagrams](docs/diagrams)).

### On your own documents

```bash
uv run python -m decision_rag --corpus docs "How is the system deployed?" --trace
```

`--corpus` takes a folder of Markdown: folders become topics, files documents, `##` headings
sections, paragraphs passages. Fenced code (including Mermaid) and hidden folders are skipped.

## Use a real decision model (TypeSafe Jev)

```bash
export DECISION_RAG_BACKEND=jev
export DECISION_RAG_API_KEY=...            # never commit; use your secret manager
uv run python -m decision_rag "..." --trace
DECISION_RAG_JUDGEMENT=independent uv run python -m decision_rag.evaluate   # ablation
```

Jev is hosted and in early access. **Read [docs/jev-integration.md](docs/jev-integration.md)
first:** it states which parts of the HTTP shape are confirmed and which are assumed.

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

## Honest evaluation

`python -m decision_rag.evaluate` compares navigation with a flat lexical retriever on a 10-query
golden set over the built-in 17-passage corpus. Result with the offline stand-in:

```text
queries            10
navigator Hit@1    0.90
flat lexical Hit@1 1.00
decision-model calls per query 4.0
mean latency       0.3 ms
```

**This is a plumbing check, not evidence about DecisionRAG.** The stand-in matches words, so it
cannot understand paraphrases ("authenticate" does not match "SASL"), and a flat word-matcher
legitimately beats a hierarchy of word-matchers on a tiny corpus. The paper's gains come from a
*language-model* decision model; to measure them, run this harness with Jev on a labelled set of
your own questions. [docs/evaluation.md](docs/evaluation.md) says how.

## Architecture

```mermaid
flowchart LR
  subgraph Entry["Entry points"]
    CLI["python -m decision_rag<br/>--trace --mermaid"]
    Tool["ADK tool<br/>navigate_corpus"]
    Eval["python -m decision_rag.evaluate"]
  end
  subgraph Core["decision_rag package"]
    Factory["factory + settings<br/>DECISION_RAG_*"]
    Pipe["DecisionRagPipeline<br/>navigate, then answer or abstain"]
    Nav["DecisionNavigator<br/>beam search, tournament,<br/>trace"]
    Tree["CorpusTree<br/>topic, document, section, passage"]
    Mer["trace_to_mermaid"]
  end
  subgraph Sources["Corpus sources"]
    Sample["built-in sample corpus"]
    Md["Markdown folder loader<br/>folders, headings, paragraphs"]
  end
  Port{{"DecisionModel protocol<br/>judge(query, candidates) -> P(relevant) each"}}
  Lex["LexicalDecisionModel<br/>offline stand-in, not a language model"]
  Jev["JevDecisionModel<br/>joint or independent<br/>one noul question per candidate"]
  Ext[("TypeSafe Jev<br/>POST /v1/systemone")]
  CLI --> Factory
  Tool --> Factory
  Eval --> Factory
  Factory --> Pipe --> Nav
  Nav --> Tree
  Sample --> Tree
  Md --> Tree
  Nav --> Port
  Port -.->|"default, no key"| Lex
  Port -.->|"DECISION_RAG_BACKEND=jev"| Jev
  Jev --> Ext
  Nav --> Mer
```

```text
src/decision_rag/
  corpus.py            CorpusTree: topic > document > section > passage, extractive descriptions
  markdown_loader.py   build a tree from a folder of Markdown
  sample_corpus.py     built-in corpus + golden questions
  models.py            Candidate and the DecisionModel protocol
  navigator.py         beam navigation, tournament, trace (the algorithm)
  local.py             offline stand-in decision model (NOT a language model)
  jev.py               TypeSafe Jev adapter: joint or independent, noul questions only
  pipeline.py          navigate, then answer or abstain; fails safe when the model is down
  mermaid.py           render a real trace as a diagram
  evaluate.py          golden-set harness vs a flat lexical retriever
  adk_agent.py         ADK agent with a navigate_corpus tool (agents-cli entrypoint)
  factory.py settings.py __main__.py
tests/                 corpus, navigator, Jev adapter (mock transport), pipeline, docs-in-sync
docs/                  concepts, algorithm, Jev integration, evaluation, diagrams, images
```

## Configuration (`DECISION_RAG_*`)

| Variable | Default | Meaning |
|---|---|---|
| `BACKEND` | `local` | `local` offline stand-in, or `jev` |
| `JUDGEMENT` | `joint` | `joint` one request per level; `independent` one per candidate (ablation) |
| `API_KEY`, `BASE_URL`, `MODEL`, `TIMEOUT_SECONDS` | unset, TypeSafe, `jev-latest`, 10 | Jev connection |
| `CORPUS_DIR` | unset | Markdown folder; unset uses the sample corpus |
| `BEAM_WIDTH` | 3 | branches kept per level |
| `MIN_PROBABILITY` | 0.2 | keep a candidate only if at least this likely relevant |
| `ABSTAIN_BELOW` | 0.3 | best passage under this probability: abstain |
| `MAX_CANDIDATES_PER_CALL` | 40 | context budget; more candidates run as a tournament |
| `TOP_K` | 3 | passages returned |

## Safety and limits

- **Fails safe.** If the decision model errors, times out or returns an invalid shape, the
  pipeline abstains with reason `decision_model_unavailable`; it never answers from a guess.
- **Abstains** when the best passage is below `ABSTAIN_BELOW`.
- **Answers are extractive** (the best passage verbatim, with its topic > document > section
  path as the citation). Retrieved text is untrusted data; the ADK agent is told never to follow
  instructions found in it.
- **Navigation can dead-end on weak titles.** If a topic or document description does not mention
  what the query needs, the right branch may score low and be pruned. Better descriptions, a
  wider beam, or a stronger decision model are the fixes; the trace shows where it happened.
- **No ingestion index to maintain,** but quality depends on the corpus having meaningful
  structure (titles, headings). A flat pile of unlabelled text is a poor fit.
- Ticket or document text sent to a hosted decision model leaves your boundary. Do not send data
  you could not send to any other API.

## More

- [Concepts](docs/concepts.md): the paper's argument, vocabulary, when to use this
- [Algorithm](docs/algorithm.md): navigation, tournament, ranking, cost, design choices
- [Jev integration](docs/jev-integration.md): wire format status, joint vs independent
- [Evaluation](docs/evaluation.md): measure it honestly on your own data
- [Diagrams](docs/diagrams/README.md): sources, how to re-render

## Source

Wan, C., Jünger, P., Du, B., Liu, B., Krishnan, N., Weinberger, K. Q. *Retriever-Free Retrieval:
Navigating Documents with Decision Models.* arXiv:2610.35868v1 [cs.AI], 26 Oct 2026.
Decision model referenced there: TypeSafe AI's Jev, <https://docs.typesafe.ai/api/system-one>.
