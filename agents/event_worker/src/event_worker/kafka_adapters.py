"""Kafka adapters on aiokafka. Works with Apache Kafka and Azure Event Hubs' Kafka endpoint."""

from __future__ import annotations

import ssl
from typing import Any

from event_worker.ports import Message
from event_worker.settings import WorkerSettings


def connection_kwargs(settings: WorkerSettings) -> dict[str, Any]:
    """Event Hubs authenticates Kafka clients with SASL PLAIN: user `$ConnectionString`."""

    kwargs: dict[str, Any] = {
        "bootstrap_servers": settings.kafka_bootstrap_servers,
        "security_protocol": settings.kafka_security_protocol,
    }
    if settings.kafka_security_protocol == "SASL_SSL":
        if settings.eventhubs_connection_string is None:
            raise ValueError("EVENTS_EVENTHUBS_CONNECTION_STRING is required for SASL_SSL")
        kwargs.update(
            sasl_mechanism="PLAIN",
            sasl_plain_username="$ConnectionString",
            sasl_plain_password=settings.eventhubs_connection_string.get_secret_value(),
            ssl_context=ssl.create_default_context(),
        )
    return kwargs


class KafkaSource:
    """Manual-commit consumer: an offset is committed only after the message is fully handled."""

    def __init__(self, settings: WorkerSettings) -> None:
        self._settings = settings
        self._consumer: Any = None

    async def start(self) -> None:
        from aiokafka import AIOKafkaConsumer

        self._consumer = AIOKafkaConsumer(
            self._settings.topic_tasks,
            group_id=self._settings.consumer_group,
            enable_auto_commit=False,
            auto_offset_reset="earliest",
            **connection_kwargs(self._settings),
        )
        await self._consumer.start()

    async def stop(self) -> None:
        if self._consumer is not None:
            await self._consumer.stop()

    async def poll(self, timeout: float) -> Message | None:
        batches = await self._consumer.getmany(timeout_ms=int(timeout * 1000), max_records=1)
        for partition, records in batches.items():
            for record in records:
                key = record.key.decode() if record.key else None
                return Message(key=key, value=record.value, token=(partition, record.offset))
        return None

    async def commit(self, message: Message) -> None:
        partition, offset = message.token
        await self._consumer.commit({partition: offset + 1})


class KafkaSink:
    def __init__(self, settings: WorkerSettings) -> None:
        self._settings = settings
        self._producer: Any = None

    async def start(self) -> None:
        from aiokafka import AIOKafkaProducer

        self._producer = AIOKafkaProducer(
            acks="all", enable_idempotence=True, **connection_kwargs(self._settings)
        )
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()

    async def publish(self, topic: str, key: str | None, value: bytes) -> None:
        await self._producer.send_and_wait(topic, value=value, key=key.encode() if key else None)
