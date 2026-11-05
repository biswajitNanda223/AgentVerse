"""Guardrails as code. The YAML wires them in; the model cannot talk its way past them."""

from __future__ import annotations

from typing import Any

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from declarative_agent.demo_data import ALL_TABLES
from declarative_agent.sql_guard import check_sql

DEFAULT_MAX_LLM_CALLS = 45  # the circuit-breaker value from the requirement list


def llm_call_budget(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> LlmResponse | None:
    """before_model_callback: hard cap on model calls for one question.

    Counts calls in per-invocation state. At the cap it does not call the model; it returns a
    partial synthesis built only from tool results already gathered.
    """

    limit = int(callback_context.state.get("max_llm_calls", DEFAULT_MAX_LLM_CALLS))
    used = int(callback_context.state.get("temp:llm_calls", 0))
    if used < limit:
        callback_context.state["temp:llm_calls"] = used + 1
        return None
    evidence = _gathered_evidence(llm_request)
    header = (
        f"Stopped after {used} model calls (limit {limit}). "
        "Partial answer from the evidence so far:"
    )
    lines = [header]
    lines += evidence or ["No tool results were gathered, so there is nothing to report."]
    return LlmResponse(
        content=types.Content(role="model", parts=[types.Part(text="\n".join(lines))])
    )


def tool_guardrail(
    tool: BaseTool, args: dict[str, Any], tool_context: ToolContext
) -> dict[str, Any] | None:
    """before_tool_callback: inspect SQL before it runs. Returning a dict skips the tool."""

    if tool.name != "run_governed_sql":
        return None
    allowed = tool_context.state.get("allowed_tables")
    allowed = ALL_TABLES if allowed is None else allowed  # demo default; production: deny
    masked = tool_context.state.get("masked_columns") or ()
    result = check_sql(str(args.get("sql", "")), allowed, masked)
    if result.ok:
        return None
    return {"blocked": True, "reason": result.reason}


def _gathered_evidence(llm_request: LlmRequest) -> list[str]:
    found: list[str] = []
    for content in llm_request.contents or []:
        for part in content.parts or []:
            response = getattr(part, "function_response", None)
            if response is None or response.name in {"list_skills", "load_skill"}:
                continue
            body = str(response.response)
            found.append(f"- {response.name}: {body[:300]}")
    return found
