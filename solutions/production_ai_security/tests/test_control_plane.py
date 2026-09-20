from pathlib import Path

from fastapi.testclient import TestClient

from solutions.production_ai_security.app.api import create_app
from solutions.production_ai_security.app.models import Evidence
from solutions.production_ai_security.app.semantic_eval import (
    LightweightNLI,
    LocalBiEncoder,
    LocalCrossEncoder,
)
from solutions.production_ai_security.app.signing import (
    ManifestVerifier,
    SignedTokenService,
    ToolManifest,
)
from solutions.production_ai_security.app.storage import DurableSecurityStore


def headers(scopes: str = "") -> dict[str, str]:
    return {
        "x-api-key": "local-development-only",
        "x-tenant-id": "public",
        "x-subject": "tester",
        "x-scopes": scopes,
    }


def test_signed_token_detects_tampering() -> None:
    service = SignedTokenService("a-secure-test-secret-at-least-32-characters")
    token = service.issue({"action_id": "a1", "tenant_id": "t1", "nonce": "n1"})
    assert service.verify(token)["action_id"] == "a1"
    encoded, signature = token.split(".")
    try:
        service.verify(f"{encoded}.{signature[:-1]}x")
    except PermissionError as exc:
        assert "signature" in str(exc)
    else:
        raise AssertionError("tampered token unexpectedly verified")


def test_manifest_binds_publisher_origin_name_version_and_digest() -> None:
    verifier = ManifestVerifier({"agentverse": "publisher-key-with-at-least-32-bytes"})
    manifest = ToolManifest("com.agentverse.orders", "read_orders", "1.0.0", "abc", "agentverse")
    signature = verifier.sign(manifest)
    assert verifier.verify(manifest, signature)
    impersonated = ToolManifest("evil.example", "read_orders", "1.0.0", "abc", "agentverse")
    assert not verifier.verify(impersonated, signature)


def test_durable_store_enforces_one_time_nonce(tmp_path: Path) -> None:
    store = DurableSecurityStore(tmp_path / "security.db")
    store.append_event("tenant-a", "test", {"safe": True})
    assert store.events("tenant-a")[0]["payload"] == {"safe": True}
    assert store.consume_nonce("tenant-a", "nonce-1")
    assert not store.consume_nonce("tenant-a", "nonce-1")


def test_zero_call_semantic_reranking_and_nli() -> None:
    encoder = LocalBiEncoder()
    assert encoder.score("human approval", "human approval is required") > 0.5
    evidence = (
        Evidence("a", "approval is useful", "a", "t", 0.4),
        Evidence("b", "human approval protects writes", "b", "t", 0.4),
    )
    assert LocalCrossEncoder().rerank("human approval", evidence)[0].document_id == "b"
    assert LightweightNLI().classify("approval is required", "approval is not required").label == (
        "contradiction"
    )


def test_api_action_approval_and_audit_flow(tmp_path: Path) -> None:
    app = create_app()
    app.state.store = DurableSecurityStore(tmp_path / "api.db")
    client = TestClient(app)
    proposal = client.post(
        "/v1/actions",
        headers=headers("refunds:write"),
        json={
            "origin": "com.agentverse.payments",
            "name": "issue_refund_lt_100",
            "arguments": {"order_id": "ord-100", "amount": 79},
            "request_id": "api-refund-1",
        },
    )
    assert proposal.status_code == 202
    action_id = proposal.json()["action_id"]
    assert proposal.json()["requires_approval"]
    decision = client.post(
        f"/v1/actions/{action_id}/decision",
        headers=headers("approvals:decide"),
        json={"decision": "approve", "reason": "verified by support"},
    )
    assert decision.status_code == 200
    assert decision.json()["state"] == "committed"
    audit = client.get("/v1/audit", headers=headers("audit:read"))
    assert audit.status_code == 200
    assert audit.json()["chain_valid"]
