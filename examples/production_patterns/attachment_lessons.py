"""Run every concrete production lesson extracted from the supplied screenshots."""

from agentverse.agents.reliability import (
    Checkpoint,
    CheckpointStore,
    IdempotencyStore,
    PlannedTask,
    compact_tool_payload,
    safe_parallel_groups,
)
from agentverse.production.failures import FailureEvent, FailureLayer, classify_recovery
from agentverse.production.provenance import create_lineage, verify_lineage
from agentverse.rag.models import Chunk
from agentverse.rag.pipeline import CorrectiveRag
from agentverse.rag.retrieval import InMemoryLexicalRetriever


def main() -> None:
    chunk = Chunk("c", "d", "CRAG grades evidence against the query", 0, "memory://d", "t", 0, 38)
    rag = CorrectiveRag(
        InMemoryLexicalRetriever([chunk]),
        grader=lambda query, candidate: 1.0 if "crag" in query.lower() and candidate.score else 0.0,
    )
    print("query-aware CRAG:", rag.retrieve("How does CRAG grade?", "t").citations)

    checkpoints = CheckpointStore()
    checkpoints.save(
        Checkpoint("run-1", next_step=2, completed_side_effects=frozenset({"email:1"}))
    )
    once: IdempotencyStore[str] = IdempotencyStore()
    print("idempotent result:", once.execute_once("t", "email:1", {"to": "user"}, lambda: "sent"))

    tasks = [
        PlannedTask("retrieve", "read independent evidence", "evidence"),
        PlannedTask("write", "write the final answer", "answer", writes_shared_state=True),
    ]
    parallel, serial = safe_parallel_groups(tasks)
    print(
        "parallel reads:",
        [task.id for task in parallel],
        "serial writes:",
        [task.id for task in serial],
    )

    artifacts: dict[str, str] = {}

    def persist(key: str, payload: str) -> str:
        artifacts[key] = payload
        return f"artifact://{key}"

    compacted = compact_tool_payload("large tool result " * 500, persist, 100)
    print("bounded context:", len(compacted.summary), "full audit:", compacted.full_payload_ref)

    lineage = create_lineage(
        request_id="request-1",
        tenant_id="t",
        agent_version="1.0.0",
        prompt_version="sha256:prompt",
        model="model-v1",
        index_version="index-v1",
        source_uri="memory://d",
        content=chunk.text,
    )
    print("lineage valid:", verify_lineage(lineage, tenant_id="t", content=chunk.text))

    failure = FailureEvent(FailureLayer.TOOL, "timeout", retryable=True)
    print("failure recovery:", classify_recovery(failure))


if __name__ == "__main__":
    main()
