from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RiskLevel(StrEnum):
    READ = "read"
    REVERSIBLE_WRITE = "reversible_write"
    IRREVERSIBLE_WRITE = "irreversible_write"


class ActionState(StrEnum):
    PROPOSED = "proposed"
    SANDBOXED = "sandboxed"
    AWAITING_APPROVAL = "awaiting_approval"
    COMMITTED = "committed"
    ROLLED_BACK = "rolled_back"
    DENIED = "denied"


@dataclass(frozen=True, slots=True)
class Identity:
    subject: str
    tenant_id: str
    scopes: frozenset[str]


@dataclass(frozen=True, slots=True)
class ToolRequest:
    origin: str
    name: str
    arguments: dict[str, Any]
    request_id: str


@dataclass(slots=True)
class ActionRecord:
    action_id: str
    actor: str
    tenant_id: str
    tool_id: str
    arguments: dict[str, Any]
    risk: RiskLevel
    state: ActionState = ActionState.PROPOSED
    preview: dict[str, Any] = field(default_factory=dict)
    result: dict[str, Any] = field(default_factory=dict)
    reason: str = ""


@dataclass(frozen=True, slots=True)
class Evidence:
    document_id: str
    text: str
    source: str
    tenant_id: str
    score: float
    trusted: bool = False


@dataclass(frozen=True, slots=True)
class AgentResponse:
    answer: str
    citations: tuple[str, ...]
    action_id: str | None = None
    requires_approval: bool = False
    trace: tuple[str, ...] = ()
