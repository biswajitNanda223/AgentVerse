import json

import pytest
from fastapi.testclient import TestClient

from event_worker.app import create_app
from event_worker.kafka_adapters import connection_kwargs
from event_worker.memory import InMemoryBroker
from event_worker.service import build_service
from event_worker.settings import WorkerSettings
from event_worker.testing import ScriptedResponder, running, wait_for


def task(
    event_id: str = "t1", question: str = "what is hybrid rag?", tenant: str = "acme"
) -> bytes:
    return json.dumps({"id": event_id, "tenant_id": tenant, "question": question}).encode()


async def test_answers_publishes_and_commits(
    settings: WorkerSettings, broker: InMemoryBroker
) -> None:
    responder = ScriptedResponder()
    service = build_service(settings, broker=broker, responder=responder)
    broker.send(task())
    async with running(service):
        await wait_for(lambda: len(broker.committed) == 1)
    [result] = [json.loads(v) for v in broker.topic(settings.topic_results)]
    assert result["event_id"] == "t1"
    assert result["status"] == "answered"
    assert result["citations"] == ["docs://x"]
    assert service.stats.answered == 1


async def test_duplicate_delivery_replays_stored_result_without_rerunning_agent(
    settings: WorkerSettings, broker: InMemoryBroker
) -> None:
    responder = ScriptedResponder()
    service = build_service(settings, broker=broker, responder=responder)
    broker.send(task())
    broker.send(task())
    async with running(service):
        await wait_for(lambda: len(broker.committed) == 2)
    assert responder.calls == 1
    first, second = broker.topic(settings.topic_results)
    assert first == second
    assert service.stats.replayed == 1


async def test_retries_transient_failures(settings: WorkerSettings, broker: InMemoryBroker) -> None:
    responder = ScriptedResponder(fail_times=2)
    service = build_service(settings, broker=broker, responder=responder)
    broker.send(task())
    async with running(service):
        await wait_for(lambda: len(broker.committed) == 1)
    [result] = [json.loads(v) for v in broker.topic(settings.topic_results)]
    assert result["attempts"] == 3
    assert not broker.topic(settings.topic_dead_letter)


async def test_exhausted_retries_go_to_dead_letter_topic(
    settings: WorkerSettings, broker: InMemoryBroker
) -> None:
    responder = ScriptedResponder(fail_times=99)
    service = build_service(settings, broker=broker, responder=responder)
    broker.send(task())
    async with running(service):
        await wait_for(lambda: len(broker.committed) == 1)
    [letter] = [json.loads(v) for v in broker.topic(settings.topic_dead_letter)]
    assert letter["event_id"] == "t1"
    assert letter["attempts"] == settings.max_attempts
    assert "model unavailable" in letter["reason"]
    assert not broker.topic(settings.topic_results)


@pytest.mark.parametrize(
    "payload",
    [b"not json", task(event_id="../escape"), task(tenant="a/b"), task(question="")],
)
async def test_poison_and_unsafe_messages_are_dead_lettered(
    payload: bytes, settings: WorkerSettings, broker: InMemoryBroker
) -> None:
    responder = ScriptedResponder()
    service = build_service(settings, broker=broker, responder=responder)
    broker.send(payload)
    async with running(service):
        await wait_for(lambda: len(broker.committed) == 1)
    assert responder.calls == 0
    assert len(broker.topic(settings.topic_dead_letter)) == 1


async def test_infrastructure_failure_stops_loop_and_leaves_message_uncommitted(
    settings: WorkerSettings, broker: InMemoryBroker
) -> None:
    service = build_service(settings, broker=broker, responder=ScriptedResponder())

    async def broken_publish(topic: str, key: str | None, value: bytes) -> None:
        raise ConnectionError("broker down")

    service._sink.publish = broken_publish  # type: ignore[method-assign]
    broker.send(task())
    async with running(service) as handle:
        await wait_for(handle.done)
    assert handle.exception() is not None
    assert not broker.committed
    assert service.running is False
    assert "broker down" in (service.last_error or "")


def test_real_content_flows_through_default_knowledge_responder(settings: WorkerSettings) -> None:
    broker = InMemoryBroker()
    service = build_service(settings, broker=broker)
    broker.send(task(question="hybrid rag retrieval"))
    with TestClient(create_app(service)) as client:
        for _ in range(100):
            if broker.topic(settings.topic_results):
                break
            import time

            time.sleep(0.02)
        assert client.get("/health/live").status_code == 200
        assert client.get("/health/ready").status_code == 200
        assert client.get("/v1/stats").json()["answered"] == 1
    [result] = [json.loads(v) for v in broker.topic(settings.topic_results)]
    assert result["citations"] == ["docs://agentverse/rag-handbook"]


def test_event_hubs_kafka_uses_sasl_plain_connection_string() -> None:
    settings = WorkerSettings(
        kafka_bootstrap_servers="ns.servicebus.windows.net:9093",
        kafka_security_protocol="SASL_SSL",
        eventhubs_connection_string="Endpoint=sb://ns.servicebus.windows.net/;SharedAccessKey=k",
    )
    kwargs = connection_kwargs(settings)
    assert kwargs["sasl_mechanism"] == "PLAIN"
    assert kwargs["sasl_plain_username"] == "$ConnectionString"
    assert kwargs["sasl_plain_password"].startswith("Endpoint=sb://")
    assert "SharedAccessKey" not in repr(settings)


def test_sasl_ssl_requires_a_connection_string() -> None:
    with pytest.raises(ValueError, match="EVENTHUBS_CONNECTION_STRING"):
        connection_kwargs(WorkerSettings(kafka_security_protocol="SASL_SSL"))
