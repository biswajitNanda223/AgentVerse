import asyncio
import logging
from dataclasses import dataclass, field

from event_worker.azure_store import BlobResultStore
from event_worker.kafka_adapters import KafkaSink, KafkaSource
from event_worker.memory import InMemoryBroker, InMemoryResultStore, InMemorySink, InMemorySource
from event_worker.ports import MessageSink, MessageSource, Responder, ResultStore
from event_worker.processor import Outcome, TaskProcessor
from event_worker.responders import build_responder
from event_worker.settings import WorkerSettings

log = logging.getLogger(__name__)


@dataclass
class Stats:
    answered: int = 0
    replayed: int = 0
    dead_lettered: int = 0
    counts: dict[str, int] = field(default_factory=dict)


class BackgroundService:
    """Long-running consume loop. Commits an offset only after the message is fully handled.

    Delivery is at-least-once. Failures that retries cannot fix go to the dead-letter topic;
    infrastructure failures stop the loop so the orchestrator restarts the pod and the
    uncommitted message is redelivered.
    """

    def __init__(
        self,
        *,
        source: MessageSource,
        sink: MessageSink,
        store: ResultStore,
        processor: TaskProcessor,
        poll_timeout: float,
    ) -> None:
        self._source, self._sink, self._store = source, sink, store
        self._processor = processor
        self._poll_timeout = poll_timeout
        self._stop = asyncio.Event()
        self.running = False
        self.last_error: str | None = None
        self.stats = Stats()

    def request_stop(self) -> None:
        self._stop.set()

    async def run(self) -> None:
        try:
            await self._store.start()
            await self._sink.start()
            await self._source.start()
            self.running = True
            log.info("event worker started")
            while not self._stop.is_set():
                message = await self._source.poll(self._poll_timeout)
                if message is None:
                    continue
                outcome = await self._processor.handle(message)
                await self._source.commit(message)
                self._record(outcome)
        except Exception as exc:
            self.last_error = f"{type(exc).__name__}: {exc}"
            log.exception("event worker stopped on error")
            raise
        finally:
            self.running = False
            for resource in (self._source, self._sink, self._store):
                try:
                    await resource.stop()
                except Exception:
                    log.exception("error while stopping %s", type(resource).__name__)

    def _record(self, outcome: Outcome) -> None:
        if outcome is Outcome.ANSWERED:
            self.stats.answered += 1
        elif outcome is Outcome.REPLAYED:
            self.stats.replayed += 1
        else:
            self.stats.dead_lettered += 1


def build_service(
    settings: WorkerSettings,
    *,
    broker: InMemoryBroker | None = None,
    responder: Responder | None = None,
) -> BackgroundService:
    source: MessageSource
    sink: MessageSink
    store: ResultStore
    if settings.backend == "azure":
        source, sink, store = KafkaSource(settings), KafkaSink(settings), BlobResultStore(settings)
    else:
        broker = broker or InMemoryBroker()
        source, sink, store = InMemorySource(broker), InMemorySink(broker), InMemoryResultStore()
    processor = TaskProcessor(
        responder=responder or build_responder(settings),
        sink=sink,
        store=store,
        settings=settings,
    )
    return BackgroundService(
        source=source,
        sink=sink,
        store=store,
        processor=processor,
        poll_timeout=settings.poll_timeout_seconds,
    )
