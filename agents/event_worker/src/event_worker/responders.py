import asyncio

from agentverse.agents.tools import search_knowledge
from event_worker.models import Answer, TaskEvent
from event_worker.ports import Responder
from event_worker.settings import WorkerSettings


class KnowledgeResponder:
    """Deterministic, offline responder over the shared retrieval tool. No model key needed."""

    async def respond(self, event: TaskEvent) -> Answer:
        found = await asyncio.to_thread(search_knowledge, event.question)
        evidence = [str(item) for item in found.get("evidence", [])]  # type: ignore[attr-defined]
        citations = [str(item) for item in found.get("citations", [])]  # type: ignore[attr-defined]
        if not evidence:
            return Answer(text="Insufficient evidence to answer.", abstained=True)
        return Answer(text=" ".join(evidence), citations=sorted(set(citations)))


class AdkResponder:
    """Runs the ADK agent per task in an isolated session. Needs GOOGLE_API_KEY or Vertex AI."""

    def __init__(self) -> None:
        from google.adk.runners import InMemoryRunner

        from event_worker.adk_agent import root_agent

        self._app = "event_worker"
        self._runner = InMemoryRunner(agent=root_agent, app_name=self._app)

    async def respond(self, event: TaskEvent) -> Answer:
        from google.genai import types

        session = await self._runner.session_service.create_session(
            app_name=self._app, user_id=event.tenant_id, session_id=event.id
        )
        message = types.Content(role="user", parts=[types.Part(text=event.question)])
        text = ""
        async for item in self._runner.run_async(
            user_id=event.tenant_id, session_id=session.id, new_message=message
        ):
            if item.is_final_response() and item.content and item.content.parts:
                text = "".join(part.text or "" for part in item.content.parts)
        if not text:
            return Answer(text="Insufficient evidence to answer.", abstained=True)
        return Answer(text=text)


def build_responder(settings: WorkerSettings) -> Responder:
    return AdkResponder() if settings.responder == "adk" else KnowledgeResponder()
