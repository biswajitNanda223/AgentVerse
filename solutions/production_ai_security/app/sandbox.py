from __future__ import annotations

import secrets
from dataclasses import replace

from solutions.production_ai_security.app.audit import AuditLog
from solutions.production_ai_security.app.models import (
    ActionRecord,
    ActionState,
    Identity,
    ToolRequest,
)
from solutions.production_ai_security.app.policy import PolicyEngine
from solutions.production_ai_security.app.tools import ToolRegistry


class ActionSandbox:
    """Keep a side effect reversible until policy and a human allow commit."""

    def __init__(self, registry: ToolRegistry, policy: PolicyEngine, audit: AuditLog) -> None:
        self._registry = registry
        self._policy = policy
        self._audit = audit
        self._actions: dict[str, ActionRecord] = {}
        self._request_index: dict[tuple[str, str], str] = {}

    def propose(self, identity: Identity, request: ToolRequest) -> ActionRecord:
        request_key = (identity.tenant_id, request.request_id)
        if request_key in self._request_index:
            return self.get(self._request_index[request_key], identity.tenant_id)

        spec = self._registry.resolve(request.origin, request.name)
        decision = self._policy.decide(
            identity,
            required_scope=spec.required_scope,
            risk=spec.risk,
            arguments=request.arguments,
        )
        record = ActionRecord(
            action_id=secrets.token_urlsafe(12),
            actor=identity.subject,
            tenant_id=identity.tenant_id,
            tool_id=spec.tool_id,
            arguments=dict(request.arguments),
            risk=spec.risk,
            reason=decision.reason,
        )
        if not decision.allowed:
            record.state = ActionState.DENIED
        else:
            record.preview = spec.handler(record.arguments, True)
            record.state = (
                ActionState.AWAITING_APPROVAL
                if decision.requires_approval
                else ActionState.SANDBOXED
            )
        self._actions[record.action_id] = record
        self._request_index[request_key] = record.action_id
        self._audit.append(
            "action.proposed",
            actor=identity.subject,
            tenant_id=identity.tenant_id,
            details={
                "action_id": record.action_id,
                "tool_id": record.tool_id,
                "state": record.state,
            },
        )
        return replace(record)

    def commit(self, action_id: str, identity: Identity, *, approved: bool = False) -> ActionRecord:
        record = self._owned(action_id, identity)
        if record.state is ActionState.AWAITING_APPROVAL and not approved:
            raise PermissionError("explicit human approval is required")
        if record.state not in {ActionState.SANDBOXED, ActionState.AWAITING_APPROVAL}:
            raise ValueError(f"cannot commit action in state {record.state}")
        origin, name = record.tool_id.split("::", maxsplit=1)
        spec = self._registry.resolve(origin, name)
        record.result = spec.handler(record.arguments, False)
        record.state = ActionState.COMMITTED
        self._audit.append(
            "action.committed",
            actor=identity.subject,
            tenant_id=identity.tenant_id,
            details={"action_id": record.action_id, "approved": approved},
        )
        return replace(record)

    def rollback(self, action_id: str, identity: Identity, *, reason: str) -> ActionRecord:
        record = self._owned(action_id, identity)
        if record.state is ActionState.COMMITTED:
            raise ValueError("committed effects require a compensating transaction")
        if record.state in {ActionState.ROLLED_BACK, ActionState.DENIED}:
            return replace(record)
        record.state = ActionState.ROLLED_BACK
        record.reason = reason
        self._audit.append(
            "action.rolled_back",
            actor=identity.subject,
            tenant_id=identity.tenant_id,
            details={"action_id": record.action_id, "reason": reason},
        )
        return replace(record)

    def get(self, action_id: str, tenant_id: str) -> ActionRecord:
        record = self._actions[action_id]
        if record.tenant_id != tenant_id:
            raise PermissionError("cross-tenant action access denied")
        return replace(record)

    def _owned(self, action_id: str, identity: Identity) -> ActionRecord:
        record = self._actions[action_id]
        if record.tenant_id != identity.tenant_id:
            raise PermissionError("cross-tenant action access denied")
        return record
