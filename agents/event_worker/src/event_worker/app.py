import asyncio
import contextlib
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from event_worker.service import BackgroundService, build_service
from event_worker.settings import get_settings

log = logging.getLogger(__name__)


def create_app(service: BackgroundService | None = None) -> FastAPI:
    """HTTP shell for the worker: health probes and stats. The consume loop is a background task."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        svc = service or build_service(get_settings())
        task = asyncio.create_task(svc.run(), name="event-worker")
        app.state.service, app.state.task = svc, task
        try:
            yield
        finally:
            svc.request_stop()
            with contextlib.suppress(Exception):
                await asyncio.wait_for(task, timeout=15)
            if not task.done():
                task.cancel()

    app = FastAPI(title="AgentVerse event worker", lifespan=lifespan)

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        # A crashed consume loop must fail liveness so the pod restarts and redelivers.
        if app.state.task.done():
            raise HTTPException(503, detail=app.state.service.last_error or "worker stopped")
        return {"status": "alive"}

    @app.get("/health/ready")
    async def ready() -> dict[str, str]:
        if not app.state.service.running:
            raise HTTPException(503, detail="worker not running")
        return {"status": "ready"}

    @app.get("/v1/stats")
    async def stats() -> dict[str, int]:
        s = app.state.service.stats
        return {"answered": s.answered, "replayed": s.replayed, "dead_lettered": s.dead_lettered}

    return app
