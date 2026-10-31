"""A small built-in corpus with three topics, used by the demo, tests and the eval harness."""

from decision_rag.corpus import CorpusTree, Outline

OUTLINE: Outline = {
    "Messaging": {
        "Kafka consumer groups": {
            "Partition assignment": [
                "A consumer group splits a topic's partitions between its members, so each "
                "partition is read by exactly one consumer in the group at a time.",
                "Adding consumers beyond the number of partitions leaves the extra consumers idle, "
                "so the partition count caps parallelism.",
            ],
            "Offsets and commits": [
                "A consumer commits the offset of the next message to read. Committing only after "
                "processing gives at-least-once delivery; committing before gives at-most-once.",
            ],
        },
        "Azure Event Hubs": {
            "Kafka compatibility": [
                "Event Hubs exposes a Kafka endpoint on port 9093, so Kafka clients connect with "
                "SASL_SSL and the username $ConnectionString plus an Event Hubs connection string.",
                "Each Kafka topic maps to an event hub inside the namespace, which must be created "
                "before clients can produce or consume.",
            ],
            "Capture and retention": [
                "Event Hubs Capture writes streaming events to Azure Blob Storage on a schedule so "
                "downstream batch jobs can replay history.",
            ],
        },
        "Dead-letter queues": {
            "When to dead-letter": [
                "Send a message to the dead-letter topic when retries cannot fix it, such as "
                "malformed JSON or a business rule violation, so one poison message cannot block "
                "the partition.",
                "Store the failure reason and attempt count with the dead-lettered payload so "
                "operators can triage and replay it later.",
            ],
        },
    },
    "Retrieval": {
        "Hybrid retrieval": {
            "Fusion": [
                "Hybrid retrieval combines lexical scores such as BM25 with dense embedding "
                "similarity, and reciprocal rank fusion merges the two ranked lists without "
                "needing comparable score scales.",
            ],
            "Reranking": [
                "A cross-encoder reranker rescoring the top candidates improves precision but can "
                "only reorder what the first-stage retriever already returned.",
            ],
        },
        "Chunking strategies": {
            "Fixed and recursive": [
                "Fixed-window chunking splits text every N tokens with overlap. Recursive "
                "chunking tries paragraph, then sentence, then word boundaries before cutting.",
            ],
            "Structure-aware": [
                "Markdown and HTML chunkers keep headings with their content, and table chunkers "
                "keep header rows with each row group so meaning survives the split.",
            ],
        },
        "GraphRAG": {
            "Relationship questions": [
                "GraphRAG follows entity relationships to answer questions that span documents, "
                "such as which teams depend on a service that failed.",
            ],
        },
    },
    "Agents": {
        "ADK tools": {
            "Tool design": [
                "Give an ADK agent narrow, typed tools with clear docstrings, because the model "
                "chooses tools from their names, parameters and descriptions.",
                "Bound every tool with a timeout and return structured results with citations so "
                "the agent can ground its answer.",
            ],
        },
        "Human approval": {
            "Risky actions": [
                "Classify an action before executing it. Deleting data, paying, sending messages "
                "or changing permissions require explicit human approval and an idempotency key.",
            ],
        },
        "A2A delegation": {
            "Agent cards": [
                "An A2A agent publishes an agent card describing its skills so peers can discover "
                "it and delegate tasks with message/send.",
            ],
        },
    },
}

# (query, expected passage id). Ids follow topic/document/section/ordinal slugs.
GOLDEN: list[tuple[str, str]] = [
    (
        "Why do extra consumers sit idle when I add more than the partition count?",
        "messaging/kafka-consumer-groups/partition-assignment/2",
    ),
    (
        "How do I get at-least-once delivery when committing offsets?",
        "messaging/kafka-consumer-groups/offsets-and-commits/1",
    ),
    (
        "How do Kafka clients authenticate to Event Hubs?",
        "messaging/azure-event-hubs/kafka-compatibility/1",
    ),
    (
        "How can I replay old Event Hubs events from Blob Storage?",
        "messaging/azure-event-hubs/capture-and-retention/1",
    ),
    (
        "What should I do with a poison message that retries cannot fix?",
        "messaging/dead-letter-queues/when-to-dead-letter/1",
    ),
    (
        "How does reciprocal rank fusion merge lexical and dense results?",
        "retrieval/hybrid-retrieval/fusion/1",
    ),
    (
        "Which chunker keeps table header rows with each row group?",
        "retrieval/chunking-strategies/structure-aware/1",
    ),
    (
        "How do I answer questions that span documents through entity relationships?",
        "retrieval/graphrag/relationship-questions/1",
    ),
    (
        "Which actions need human approval and an idempotency key?",
        "agents/human-approval/risky-actions/1",
    ),
    (
        "How do peers discover an A2A agent and delegate tasks?",
        "agents/a2a-delegation/agent-cards/1",
    ),
]


def sample_tree() -> CorpusTree:
    return CorpusTree.from_outline(OUTLINE, "sample")
