"""Framework-neutral reliability controls used around ADK workflows."""

import json
import threading
from collections.abc import Callable, Mapping, MutableMapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from hashlib import sha256
from typing import Generic, Protocol, TypeVar

from agentverse.core.security import Principal, stable_tenant_key

T = TypeVar("T")


class Impact(StrEnum):
    READ = "read"
    REVERSIBLE_WRITE = "reversible_write"
    IRREVERSIBLE_WRITE = "irreversible_write"


@dataclass(frozen=True, slots=True)
class ToolPolicy:
    name: str
    required_scope: str
    impact: Impact = Impact.READ
    timeout_seconds: float = 10.0
    max_result_chars: int = 8_000

    @property
    def requires_approval(self) -> bool:
        return self.impact is not Impact.READ


@dataclass(frozen=True, slots=True)
class ToolInvocation:
    tool: str
    arguments: Mapping[str, object]
    principal: Principal
    run_id: str
    approval_id: str | None = None


class ApprovalVerifier(Protocol):
    def __call__(self, approval_id: str, invocation: ToolInvocation) -> bool: ...


def authorize_tool(
    policy: ToolPolicy, invocation: ToolInvocation, verify_approval: ApprovalVerifier
) -> None:
    invocation.principal.require(policy.required_scope)
    if policy.requires_approval and (
        not invocation.approval_id or not verify_approval(invocation.approval_id, invocation)
    ):
        raise PermissionError(f"{policy.name} requires valid human approval")


@dataclass(frozen=True, slots=True)
class StoredResult(Generic[T]):
    value: T
    fingerprint: str


class IdempotencyStore(Generic[T]):
    """Thread-safe teaching store; production uses durable transactional storage."""

    def __init__(self) -> None:
        self._items: MutableMapping[str, StoredResult[T]] = {}
        self._lock = threading.Lock()

    def execute_once(
        self,
        tenant_id: str,
        key: str,
        arguments: Mapping[str, object],
        operation: Callable[[], T],
    ) -> T:
        namespaced = stable_tenant_key(tenant_id, key)
        fingerprint = sha256(json.dumps(arguments, sort_keys=True).encode()).hexdigest()
        with self._lock:
            existing = self._items.get(namespaced)
            if existing:
                if existing.fingerprint != fingerprint:
                    raise ValueError("idempotency key reused with different arguments")
                return existing.value
            value = operation()
            self._items[namespaced] = StoredResult(value, fingerprint)
            return value


@dataclass(frozen=True, slots=True)
class Checkpoint:
    run_id: str
    next_step: int
    completed_side_effects: frozenset[str] = frozenset()
    state: Mapping[str, object] = field(default_factory=dict)


class CheckpointStore:
    def __init__(self) -> None:
        self._checkpoints: dict[str, Checkpoint] = {}

    def save(self, checkpoint: Checkpoint) -> None:
        current = self._checkpoints.get(checkpoint.run_id)
        if current and checkpoint.next_step < current.next_step:
            raise ValueError("checkpoint cannot move backwards")
        self._checkpoints[checkpoint.run_id] = checkpoint

    def load(self, run_id: str) -> Checkpoint | None:
        return self._checkpoints.get(run_id)


@dataclass(frozen=True, slots=True)
class ContextArtifact:
    summary: str
    full_payload_ref: str
    original_chars: int
    sha256: str


def compact_tool_payload(
    payload: str, persist: Callable[[str, str], str], max_context_chars: int = 2_000
) -> ContextArtifact:
    """Keep bounded context while persisting full evidence for audit and replay."""

    digest = sha256(payload.encode()).hexdigest()
    reference = persist(digest, payload)
    normalized = " ".join(payload.split())
    summary = normalized[:max_context_chars]
    if len(normalized) > max_context_chars:
        summary += "…"
    return ContextArtifact(summary, reference, len(payload), digest)


@dataclass(frozen=True, slots=True)
class PlannedTask:
    id: str
    description: str
    output_key: str
    writes_shared_state: bool = False


def safe_parallel_groups(
    tasks: Sequence[PlannedTask],
) -> tuple[list[PlannedTask], list[PlannedTask]]:
    """Only disjoint, read-like outputs are parallel; shared writes remain serial."""

    seen: set[str] = set()
    parallel: list[PlannedTask] = []
    serial: list[PlannedTask] = []
    for task in tasks:
        if task.writes_shared_state or task.output_key in seen:
            serial.append(task)
        else:
            parallel.append(task)
            seen.add(task.output_key)
    return parallel, serial
