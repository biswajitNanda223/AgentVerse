import asyncio
import logging
from enum import StrEnum

from pydantic import ValidationError

from event_worker.models import DeadLetter, ResultEvent, TaskEvent
from event_worker.ports import Message, MessageSink, Responder, ResultStore
from event_worker.settings import WorkerSettings

log = logging.getLogger(__name__)


class Outcome(StrEnum):
    ANSWERED = "answered"
    REPLAYED = "replayed"  # result already stored: republished, agent not run again
    DEAD_LETTERED = "dead_lettered"


class TaskProcessor:
    """Handles one message: validate, deduplicate, run the agent with retries, publish."""

    def __init__(
        self,
        *,
        responder: Responder,
        sink: MessageSink,
        store: ResultStore,
        settings: WorkerSettings,
    ) -> None:
        self._responder = responder
        self._sink = sink
        self._store = store
        self._s = settings

    async def handle(self, message: Message) -> Outcome:
        try:
            event = TaskEvent.model_validate_json(message.value)
        except ValidationError as exc:
            # Poison message: retrying cannot help, so park it and move on.
            await self._dead_letter(
                None, f"invalid event: {exc.error_count()} error(s)", 0, message
            )
            return Outcome.DEAD_LETTERED

        name = f"{event.tenant_id}/{event.id}.json"
        existing = await self._store.get(name)
        if existing is not None:
            await self._publish(event.id, existing)
            return Outcome.REPLAYED

        last_error = "unknown"
        for attempt in range(1, self._s.max_attempts + 1):
            try:
                answer = await asyncio.wait_for(
                    self._responder.respond(event), self._s.task_timeout_seconds
                )
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
                log.warning(
                    "attempt %d/%d failed for %s: %s",
                    attempt,
                    self._s.max_attempts,
                    event.id,
                    last_error,
                )
                if attempt < self._s.max_attempts:
                    await asyncio.sleep(self._s.retry_backoff_seconds * 2 ** (attempt - 1))
                continue
            result = ResultEvent(
                event_id=event.id,
                tenant_id=event.tenant_id,
                status="abstained" if answer.abstained else "answered",
                answer=answer.text,
                citations=answer.citations,
                attempts=attempt,
            )
            payload = result.model_dump_json().encode()
            if not await self._store.put_if_absent(name, payload):
                # Another worker won the race: publish its record so both agree.
                payload = await self._store.get(name) or payload
            await self._publish(event.id, payload)
            return Outcome.ANSWERED

        await self._dead_letter(event.id, last_error, self._s.max_attempts, message)
        return Outcome.DEAD_LETTERED

    async def _publish(self, event_id: str, payload: bytes) -> None:
        await self._sink.publish(self._s.topic_results, event_id, payload)

    async def _dead_letter(
        self, event_id: str | None, reason: str, attempts: int, message: Message
    ) -> None:
        letter = DeadLetter(
            event_id=event_id,
            reason=reason,
            attempts=attempts,
            payload=message.value.decode(errors="replace")[:4000],
        )
        await self._sink.publish(
            self._s.topic_dead_letter, event_id, letter.model_dump_json().encode()
        )
