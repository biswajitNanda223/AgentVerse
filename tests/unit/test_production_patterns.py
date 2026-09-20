from agentverse.production.failures import (
    FailureEvent,
    FailureLayer,
    RecoveryAction,
    classify_recovery,
)
from agentverse.production.provenance import create_lineage, verify_lineage


def test_failure_recovery_is_layer_and_side_effect_aware() -> None:
    security = classify_recovery(FailureEvent(FailureLayer.SECURITY, "tenant_mismatch", False))
    replay_risk = classify_recovery(
        FailureEvent(FailureLayer.TOOL, "unknown_result", True, side_effect_possible=True)
    )
    retrieval = classify_recovery(FailureEvent(FailureLayer.RETRIEVAL, "low_recall", True))
    assert security.action is RecoveryAction.FAIL_CLOSED
    assert replay_risk.action is RecoveryAction.RESUME_CHECKPOINT
    assert retrieval.action is RecoveryAction.REWRITE_QUERY


def test_provenance_detects_tenant_and_content_changes() -> None:
    lineage = create_lineage(
        request_id="r",
        tenant_id="tenant-a",
        agent_version="1",
        prompt_version="p1",
        model="m1",
        index_version="i1",
        source_uri="memory://source",
        content="verified evidence",
    )
    assert verify_lineage(lineage, tenant_id="tenant-a", content="verified evidence")
    assert not verify_lineage(lineage, tenant_id="tenant-b", content="verified evidence")
    assert not verify_lineage(lineage, tenant_id="tenant-a", content="modified evidence")
