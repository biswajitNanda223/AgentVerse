from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request

from agentverse.core.config import get_settings
from agentverse.core.security import Principal, constant_time_key_match
from agentverse.core.telemetry import configure_telemetry, span
from agentverse.rag.models import Document
from solutions.agentic_rag_end_to_end.app.models import (
    AskRequest,
    AskResponse,
    IngestRequest,
)
from solutions.agentic_rag_end_to_end.app.orchestrator import AgenticRagOrchestrator
from solutions.agentic_rag_end_to_end.app.settings import SolutionSettings, settings


def principal(
    x_api_key: str = Header(default=""),
    x_tenant_id: str = Header(default="public", min_length=1, max_length=128),
) -> Principal:
    if not constant_time_key_match(x_api_key, settings().api_key):
        raise HTTPException(status_code=401, detail="invalid API key")
    return Principal("api-client", x_tenant_id, frozenset({"ask", "ingest"}))


def create_app() -> FastAPI:
    config: SolutionSettings = settings()
    configure_telemetry(get_settings())

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.orchestrator = AgenticRagOrchestrator(max_steps=config.max_agent_steps)
        yield

    app = FastAPI(
        title="AgentVerse Agentic RAG End-to-End",
        version="1.0.0",
        lifespan=lifespan,
    )

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/documents", status_code=202)
    async def ingest(
        payload: IngestRequest,
        request: Request,
        actor: Annotated[Principal, Depends(principal)],
    ) -> dict[str, int]:
        actor.require("ingest")
        documents = [
            Document(item.id, item.text, item.source_uri, actor.tenant_id)
            for item in payload.documents
        ]
        count = request.app.state.orchestrator.add_documents(documents)
        return {"documents": len(documents), "chunks": count}

    @app.post("/v1/ask", response_model=AskResponse)
    async def ask(
        payload: AskRequest,
        request: Request,
        actor: Annotated[Principal, Depends(principal)],
        x_request_id: str | None = Header(default=None),
    ) -> AskResponse:
        actor.require("ask")
        request_id = (x_request_id or str(uuid4()))[:128]
        with span(
            "agentic_rag.request",
            tenant_id=actor.tenant_id,
            requested_mode=payload.mode.value,
        ):
            result = request.app.state.orchestrator.ask(
                payload.question, actor.tenant_id, payload.mode
            )
        return AskResponse(
            answer=result.answer,
            mode=result.mode,
            citations=list(result.citations),
            request_id=request_id,
            steps=list(result.steps),
            abstained=result.abstained,
        )

    return app


app = create_app()
