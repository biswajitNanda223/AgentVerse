from __future__ import annotations

from production_security.audit import AuditLog
from production_security.cache import TenantCache
from production_security.memory import SecureMemory
from production_security.models import (
    ActionState,
    AgentResponse,
    Evidence,
    Identity,
    ToolRequest,
)
from production_security.policy import PolicyEngine
from production_security.retrieval import SecureRetriever
from production_security.sandbox import ActionSandbox
from production_security.telemetry import actions, denials, retrieval_abstentions
from production_security.tools import ToolRegistry, build_default_registry


class SecureAgent:
    """A small agentic control loop with security decisions outside the model."""

    def __init__(
        self,
        evidence: tuple[Evidence, ...] = (),
        *,
        registry: ToolRegistry | None = None,
    ) -> None:
        self.audit = AuditLog()
        self.cache = TenantCache()
        self.memory = SecureMemory(self.audit)
        self.retriever = SecureRetriever(evidence)
        self.sandbox = ActionSandbox(
            registry or build_default_registry(), PolicyEngine(), self.audit
        )

    def answer(self, identity: Identity, question: str) -> AgentResponse:
        trace = ["authenticate", "authorize", "retrieve", "screen_context", "synthesize"]
        cache_key = self.cache.key(
            identity.tenant_id,
            "answer",
            question,
            policy_version="v1",
            source_version="demo-v1",
        )
        cached = self.cache.get(cache_key)
        if isinstance(cached, AgentResponse):
            return AgentResponse(
                cached.answer,
                cached.citations,
                trace=(*cached.trace, "cache_hit"),
            )
        evidence = self.retriever.search(question, tenant_id=identity.tenant_id)
        if not evidence:
            retrieval_abstentions.add(1, {"tenant_id": identity.tenant_id})
            response = AgentResponse(
                "I do not have enough trusted evidence to answer.", (), trace=tuple(trace)
            )
        else:
            summary = " ".join(item.text for item in evidence)
            response = AgentResponse(
                summary,
                tuple(item.source for item in evidence),
                trace=tuple(trace),
            )
        self.cache.put(cache_key, response)
        self.audit.append(
            "agent.answered",
            actor=identity.subject,
            tenant_id=identity.tenant_id,
            details={"citation_count": len(response.citations)},
        )
        return response

    def propose_action(self, identity: Identity, request: ToolRequest) -> AgentResponse:
        trace = ("authenticate", "resolve_origin_name", "authorize", "sandbox")
        record = self.sandbox.propose(identity, request)
        actions.add(1, {"tenant_id": identity.tenant_id, "tool_id": record.tool_id})
        if record.state is ActionState.DENIED:
            denials.add(1, {"tenant_id": identity.tenant_id, "tool_id": record.tool_id})
            return AgentResponse(
                f"Action denied: {record.reason}", (), action_id=record.action_id, trace=trace
            )
        requires_approval = record.state is ActionState.AWAITING_APPROVAL
        final_trace = (*trace, "await_approval") if requires_approval else trace
        return AgentResponse(
            f"Action preview created: {record.preview}",
            (),
            action_id=record.action_id,
            requires_approval=requires_approval,
            trace=final_trace,
        )
