from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import uuid4

import structlog
from fastapi import Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse, Response

from agentverse.api.schemas import IngestRequest, QueryRequest, QueryResponse
from agentverse.core.config import Settings, get_settings
from agentverse.core.security import Principal, constant_time_key_match
from agentverse.core.telemetry import configure_telemetry
from agentverse.rag.chunking import RecursiveChunker
from agentverse.rag.models import Document
from agentverse.rag.pipeline import CorrectiveRag
from agentverse.rag.retrieval import InMemoryLexicalRetriever

logger = structlog.get_logger()


class Runtime:
    def __init__(self) -> None:
        self.retriever = InMemoryLexicalRetriever()
        self.rag = CorrectiveRag(self.retriever)


def _principal(
    settings: Annotated[Settings, Depends(get_settings)],
    x_api_key: Annotated[str, Header()] = "",
    x_tenant_id: Annotated[str, Header(min_length=1, max_length=128)] = "public",
) -> Principal:
    if not constant_time_key_match(x_api_key, settings.api_key):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid API key")
    return Principal("api-client", x_tenant_id, frozenset({"rag:read", "rag:write"}))


def create_app() -> FastAPI:
    settings = get_settings()
    configure_telemetry(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.runtime = Runtime()
        yield

    app = FastAPI(title="AgentVerse API", version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = request.headers.get("x-request-id", str(uuid4()))[:128]
        if request.headers.get("content-length"):
            try:
                content_length = int(request.headers["content-length"])
            except ValueError:
                return JSONResponse(status_code=400, content={"detail": "invalid content-length"})
            if content_length > settings.max_request_bytes:
                return JSONResponse(status_code=413, content={"detail": "request too large"})
        response = await call_next(request)
        response.headers["x-request-id"] = request_id
        return response

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready")
    async def ready(request: Request) -> dict[str, str]:
        if not hasattr(request.app.state, "runtime"):
            raise HTTPException(status_code=503, detail="runtime unavailable")
        return {"status": "ready"}

    @app.post("/v1/rag/documents", status_code=202)
    async def ingest(
        payload: IngestRequest,
        request: Request,
        principal: Annotated[Principal, Depends(_principal)],
    ) -> dict[str, int]:
        principal.require("rag:write")
        chunker = RecursiveChunker()
        chunks = []
        for item in payload.documents:
            document = Document(item.id, item.text, item.source_uri, principal.tenant_id)
            chunks.extend(chunker.split(document))
        request.app.state.runtime.retriever.add(chunks)
        await logger.ainfo("documents_ingested", count=len(payload.documents), chunks=len(chunks))
        return {"documents": len(payload.documents), "chunks": len(chunks)}

    @app.post("/v1/rag/query", response_model=QueryResponse)
    async def query(
        payload: QueryRequest,
        request: Request,
        principal: Annotated[Principal, Depends(_principal)],
    ) -> QueryResponse:
        principal.require("rag:read")
        answer = request.app.state.runtime.rag.retrieve(
            payload.query, principal.tenant_id, payload.top_k
        )
        return QueryResponse(
            query=answer.query,
            context=answer.context,
            citations=list(answer.citations),
            corrected=answer.corrected,
            request_id=request.headers.get("x-request-id", "generated"),
        )

    return app


app = create_app()
