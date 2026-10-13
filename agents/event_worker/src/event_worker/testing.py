"""Helpers shared by tests and local experiments (no Kafka, Azure or model needed)."""

import asyncio
import contextlib
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager

from event_worker.models import Answer, TaskEvent
from event_worker.service import BackgroundService


class ScriptedResponder:
    """Fails `fail_times` times, then answers. Counts calls."""

    def __init__(self, fail_times: int = 0) -> None:
        self.fail_times = fail_times
        self.calls = 0

    async def respond(self, event: TaskEvent) -> Answer:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise RuntimeError("model unavailable")
        return Answer(text=f"answer to {event.question}", citations=["docs://x"])


async def wait_for(condition: Callable[[], bool], timeout: float = 3.0) -> None:
    async def poll() -> None:
        while not condition():
            await asyncio.sleep(0.01)

    await asyncio.wait_for(poll(), timeout)


@asynccontextmanager
async def running(service: BackgroundService) -> AsyncIterator[asyncio.Task[None]]:
    task = asyncio.create_task(service.run())
    try:
        await wait_for(lambda: service.running or task.done())
        yield task
    finally:
        service.request_stop()
        with contextlib.suppress(Exception):
            await asyncio.wait_for(task, 3)
