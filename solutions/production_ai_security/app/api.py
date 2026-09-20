from __future__ import annotations

from typing import Annotated, Any, Literal
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from agentverse.core.config import get_settings
from agentverse.core.security import constant_time_key_match
from agentverse.core.telemetry import configure_telemetry
from solutions.production_ai_security.app.models import Evidence, Identity, ToolRequest
from solutions.production_ai_security.app.orchestrator import SecureAgent
from solutions.production_ai_security.app.settings import settings
from solutions.production_ai_security.app.signing import SignedTokenService
from solutions.production_ai_security.app.storage import DurableSecurityStore


class AskBody(BaseModel):
    question: str = Field(min_length=1, max_length=4_000)


class ActionBody(BaseModel):
    origin: str = Field(min_length=1, max_length=200)
    name: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any]
    request_id: str = Field(min_length=1, max_length=128)


class DecisionBody(BaseModel):
    decision: Literal["approve", "reject"]
    reason: str = Field(default="human decision", max_length=500)


class MemoryBody(BaseModel):
    text: str = Field(min_length=1, max_length=2_000)
    source: str = Field(min_length=1, max_length=200)
    confidence: float = Field(ge=0, le=1)


def actor(
    x_api_key: str = Header(default=""),
    x_tenant_id: str = Header(default="public", min_length=1, max_length=128),
    x_subject: str = Header(default="api-client", min_length=1, max_length=128),
    x_scopes: str = Header(default=""),
) -> Identity:
    if not constant_time_key_match(x_api_key, settings().api_key):
        raise HTTPException(status_code=401, detail="invalid API key")
    scopes = frozenset(value.strip() for value in x_scopes.split(",") if value.strip())
    return Identity(x_subject, x_tenant_id, scopes)


def create_app() -> FastAPI:
    config = settings()
    configure_telemetry(get_settings())
    app = FastAPI(title="AgentVerse Production AI Security", version="1.0.0")
    app.state.agent = SecureAgent(
        (
            Evidence(
                "consent",
                "Sensitive agent actions remain reversible until explicit human approval.",
                "docs://security/consent",
                "public",
                1.0,
                True,
            ),
        )
    )
    app.state.tokens = SignedTokenService(config.approval_signing_secret)
    app.state.store = DurableSecurityStore(config.security_db_path)

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/ask")
    async def ask(
        payload: AskBody,
        request: Request,
        identity: Annotated[Identity, Depends(actor)],
    ) -> dict[str, Any]:
        response = request.app.state.agent.answer(identity, payload.question)
        return {
            "answer": response.answer,
            "citations": response.citations,
            "trace": response.trace,
        }

    @app.post("/v1/actions", status_code=202)
    async def propose(
        payload: ActionBody,
        request: Request,
        identity: Annotated[Identity, Depends(actor)],
    ) -> dict[str, Any]:
        try:
            response = request.app.state.agent.propose_action(
                identity,
                ToolRequest(payload.origin, payload.name, payload.arguments, payload.request_id),
            )
        except (LookupError, PermissionError, ValueError) as exc:
            raise HTTPException(status_code=403, detail=str(exc)) from exc
        request.app.state.store.append_event(
            identity.tenant_id,
            "api.action.proposed",
            {"action_id": response.action_id, "subject": identity.subject},
        )
        return {
            "action_id": response.action_id,
            "preview": response.answer,
            "requires_approval": response.requires_approval,
            "trace": response.trace,
        }

    @app.post("/v1/actions/{action_id}/decision")
    async def decide(
        action_id: str,
        payload: DecisionBody,
        request: Request,
        identity: Annotated[Identity, Depends(actor)],
    ) -> dict[str, Any]:
        if "approvals:decide" not in identity.scopes:
            raise HTTPException(status_code=403, detail="missing scope: approvals:decide")
        if payload.decision == "reject":
            record = request.app.state.agent.sandbox.rollback(
                action_id, identity, reason=payload.reason
            )
            return {"action_id": action_id, "state": record.state}
        nonce = str(uuid4())
        token = request.app.state.tokens.issue(
            {
                "action_id": action_id,
                "tenant_id": identity.tenant_id,
                "approver": identity.subject,
                "nonce": nonce,
            },
            ttl_seconds=300,
        )
        claims = request.app.state.tokens.verify(token)
        if claims["action_id"] != action_id or claims["tenant_id"] != identity.tenant_id:
            raise HTTPException(status_code=403, detail="approval binding mismatch")
        if not request.app.state.store.consume_nonce(identity.tenant_id, str(claims["nonce"])):
            raise HTTPException(status_code=409, detail="approval token already consumed")
        record = request.app.state.agent.sandbox.commit(action_id, identity, approved=True)
        request.app.state.store.append_event(
            identity.tenant_id,
            "api.action.approved",
            {"action_id": action_id, "approver": identity.subject},
        )
        return {"action_id": action_id, "state": record.state, "result": record.result}

    @app.get("/v1/audit")
    async def audit(
        request: Request,
        identity: Annotated[Identity, Depends(actor)],
    ) -> dict[str, Any]:
        if "audit:read" not in identity.scopes:
            raise HTTPException(status_code=403, detail="missing scope: audit:read")
        volatile = request.app.state.agent.audit.for_tenant(identity.tenant_id)
        return {
            "chain_valid": request.app.state.agent.audit.verify_chain(),
            "events": [
                {
                    "sequence": item.sequence,
                    "event_type": item.event_type,
                    "timestamp": item.timestamp,
                    "details": item.details,
                    "event_hash": item.event_hash,
                }
                for item in volatile
            ],
            "durable_events": request.app.state.store.events(identity.tenant_id),
        }

    @app.post("/v1/memory", status_code=201)
    async def remember(
        payload: MemoryBody,
        request: Request,
        identity: Annotated[Identity, Depends(actor)],
    ) -> dict[str, Any]:
        if "memory:write" not in identity.scopes:
            raise HTTPException(status_code=403, detail="missing scope: memory:write")
        try:
            item = request.app.state.agent.memory.remember(
                tenant_id=identity.tenant_id,
                subject=identity.subject,
                text=payload.text,
                source=payload.source,
                confidence=payload.confidence,
            )
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return {"memory_id": item.memory_id, "expires_at": item.expires_at}

    @app.get("/v1/memory")
    async def recall(
        query: str,
        request: Request,
        identity: Annotated[Identity, Depends(actor)],
    ) -> dict[str, Any]:
        if "memory:read" not in identity.scopes:
            raise HTTPException(status_code=403, detail="missing scope: memory:read")
        items = request.app.state.agent.memory.recall(tenant_id=identity.tenant_id, query=query)
        return {"items": [{"memory_id": item.memory_id, "text": item.text} for item in items]}

    @app.delete("/v1/memory", status_code=200)
    async def forget(
        request: Request,
        identity: Annotated[Identity, Depends(actor)],
    ) -> dict[str, int]:
        if "memory:delete" not in identity.scopes:
            raise HTTPException(status_code=403, detail="missing scope: memory:delete")
        return {
            "removed": request.app.state.agent.memory.forget(
                tenant_id=identity.tenant_id, subject=identity.subject
            )
        }

    return app


app = create_app()
