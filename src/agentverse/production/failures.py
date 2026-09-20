from dataclasses import dataclass
from enum import StrEnum


class FailureLayer(StrEnum):
    INGESTION = "ingestion"
    RETRIEVAL = "retrieval"
    GENERATION = "generation"
    TOOL = "tool"
    ORCHESTRATION = "orchestration"
    PLATFORM = "platform"
    SECURITY = "security"


class RecoveryAction(StrEnum):
    QUARANTINE = "quarantine"
    REWRITE_QUERY = "rewrite_query"
    ABSTAIN = "abstain"
    RETRY_SAFE_READ = "retry_safe_read"
    RESUME_CHECKPOINT = "resume_checkpoint"
    SHED_LOAD = "shed_load"
    FAIL_CLOSED = "fail_closed"


@dataclass(frozen=True, slots=True)
class FailureEvent:
    layer: FailureLayer
    code: str
    retryable: bool
    side_effect_possible: bool = False


@dataclass(frozen=True, slots=True)
class FailureDecision:
    action: RecoveryAction
    reason: str


def classify_recovery(event: FailureEvent) -> FailureDecision:
    """Choose recovery by failure semantics, never by exception type alone."""

    if event.layer is FailureLayer.SECURITY:
        return FailureDecision(
            RecoveryAction.FAIL_CLOSED, "security boundaries cannot degrade open"
        )
    if event.side_effect_possible:
        return FailureDecision(
            RecoveryAction.RESUME_CHECKPOINT,
            "reconcile recorded side effects before any retry",
        )
    if event.layer is FailureLayer.INGESTION:
        return FailureDecision(
            RecoveryAction.QUARANTINE, "keep corrupt input outside the active index"
        )
    if event.layer is FailureLayer.RETRIEVAL:
        return FailureDecision(RecoveryAction.REWRITE_QUERY, "retry once using alternate retrieval")
    if event.layer is FailureLayer.GENERATION:
        return FailureDecision(RecoveryAction.ABSTAIN, "do not return an unsupported answer")
    if event.layer is FailureLayer.TOOL and event.retryable:
        return FailureDecision(
            RecoveryAction.RETRY_SAFE_READ, "bounded retry is safe for read-only tool"
        )
    if event.layer is FailureLayer.PLATFORM:
        return FailureDecision(
            RecoveryAction.SHED_LOAD, "protect dependencies and recover capacity"
        )
    return FailureDecision(RecoveryAction.ABSTAIN, "unknown orchestration state requires review")
