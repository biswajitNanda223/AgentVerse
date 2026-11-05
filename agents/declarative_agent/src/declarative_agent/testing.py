"""A scripted model and runner helper, so the real agent can be driven with no API key."""

from __future__ import annotations

from collections.abc import AsyncGenerator, Callable
from typing import Any

from google.adk.agents.base_agent import BaseAgent
from google.adk.events import Event
from google.adk.models import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.runners import InMemoryRunner
from google.genai import types
from pydantic import Field

Script = Callable[[int, LlmRequest], LlmResponse]


def call(name: str, **args: Any) -> LlmResponse:
    part = types.Part(function_call=types.FunctionCall(name=name, args=args))
    return LlmResponse(content=types.Content(role="model", parts=[part]))


def say(text: str) -> LlmResponse:
    return LlmResponse(content=types.Content(role="model", parts=[types.Part(text=text)]))


def tool_names(request: LlmRequest) -> set[str]:
    names: set[str] = set()
    for tool in request.config.tools or []:
        for declaration in getattr(tool, "function_declarations", None) or []:
            names.add(declaration.name)
    return names


class ScriptedLlm(BaseLlm):
    """Replays a script: turn N returns whatever `script(N, request)` says."""

    model: str = "scripted"
    script: Script
    seen_tools: list[set[str]] = Field(default_factory=list)
    calls: int = 0

    async def generate_content_async(
        self, llm_request: LlmRequest, stream: bool = False
    ) -> AsyncGenerator[LlmResponse, None]:
        self.seen_tools.append(tool_names(llm_request))
        index = self.calls
        self.calls += 1
        yield self.script(index, llm_request)


async def run_turns(
    agent: BaseAgent, question: str, state: dict[str, Any] | None = None
) -> list[Event]:
    runner = InMemoryRunner(agent=agent, app_name="declarative-agent-tests")
    session = await runner.session_service.create_session(
        app_name="declarative-agent-tests", user_id="u1", state=state or {}
    )
    message = types.Content(role="user", parts=[types.Part(text=question)])
    return [
        event
        async for event in runner.run_async(
            user_id="u1", session_id=session.id, new_message=message
        )
    ]


def responses(events: list[Event], name: str) -> list[dict[str, Any]]:
    """All function responses with this tool name, in order."""

    found: list[dict[str, Any]] = []
    for event in events:
        for response in event.get_function_responses():
            if response.name == name:
                found.append(dict(response.response or {}))
    return found


def final_text(events: list[Event]) -> str:
    for event in reversed(events):
        if event.content and event.content.parts and not event.get_function_calls():
            text = "".join(p.text or "" for p in event.content.parts)
            if text:
                return text
    return ""
