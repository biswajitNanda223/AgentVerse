"""In-memory adapters for local runs and tests. They mirror the production semantics."""

import asyncio

from event_worker.ports import Message


class InMemoryBroker:
    """One queue for inbound tasks plus a log of everything published."""

    def __init__(self) -> None:
        self.inbox: asyncio.Queue[Message] = asyncio.Queue()
        self.published: list[tuple[str, str | None, bytes]] = []
        self.committed: list[Message] = []

    def send(self, value: bytes, key: str | None = None) -> None:
        self.inbox.put_nowait(Message(key=key, value=value))

    def topic(self, name: str) -> list[bytes]:
        return [value for topic, _, value in self.published if topic == name]


class InMemorySource:
    def __init__(self, broker: InMemoryBroker) -> None:
        self._broker = broker

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def poll(self, timeout: float) -> Message | None:
        try:
            return await asyncio.wait_for(self._broker.inbox.get(), timeout)
        except TimeoutError:
            return None

    async def commit(self, message: Message) -> None:
        self._broker.committed.append(message)


class InMemorySink:
    def __init__(self, broker: InMemoryBroker) -> None:
        self._broker = broker

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def publish(self, topic: str, key: str | None, value: bytes) -> None:
        self._broker.published.append((topic, key, value))


class InMemoryResultStore:
    def __init__(self) -> None:
        self.records: dict[str, bytes] = {}

    async def start(self) -> None:
        return None

    async def stop(self) -> None:
        return None

    async def put_if_absent(self, name: str, value: bytes) -> bool:
        if name in self.records:
            return False
        self.records[name] = value
        return True

    async def get(self, name: str) -> bytes | None:
        return self.records.get(name)
