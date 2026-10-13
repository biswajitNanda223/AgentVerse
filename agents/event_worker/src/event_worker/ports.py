"""Infrastructure boundaries. The processor depends only on these protocols."""

from dataclasses import dataclass
from typing import Any, Protocol

from event_worker.models import Answer, TaskEvent


@dataclass(frozen=True)
class Message:
    key: str | None
    value: bytes
    token: Any = None  # adapter-private data needed to commit this message


class MessageSource(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def poll(self, timeout: float) -> Message | None: ...
    async def commit(self, message: Message) -> None: ...


class MessageSink(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def publish(self, topic: str, key: str | None, value: bytes) -> None: ...


class ResultStore(Protocol):
    async def start(self) -> None: ...
    async def stop(self) -> None: ...
    async def put_if_absent(self, name: str, value: bytes) -> bool:
        """Write once. Return False when the record already exists (duplicate delivery)."""
        ...

    async def get(self, name: str) -> bytes | None: ...


class Responder(Protocol):
    async def respond(self, event: TaskEvent) -> Answer: ...
