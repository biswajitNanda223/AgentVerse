import pytest

from event_worker.memory import InMemoryBroker
from event_worker.settings import WorkerSettings


@pytest.fixture
def settings() -> WorkerSettings:
    return WorkerSettings(backend="memory", retry_backoff_seconds=0, poll_timeout_seconds=0.05)


@pytest.fixture
def broker() -> InMemoryBroker:
    return InMemoryBroker()
