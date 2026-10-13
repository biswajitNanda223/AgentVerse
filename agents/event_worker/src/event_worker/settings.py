from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class WorkerSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="EVENTS_", extra="ignore")

    # "memory" runs with no infrastructure; "azure" uses Kafka/Event Hubs and Azure Blob Storage.
    backend: Literal["memory", "azure"] = "memory"
    responder: Literal["knowledge", "adk"] = "knowledge"
    model_name: str = "gemini-2.5-flash"

    # Kafka. Azure Event Hubs exposes a Kafka endpoint at <namespace>.servicebus.windows.net:9093.
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_security_protocol: Literal["PLAINTEXT", "SASL_SSL"] = "PLAINTEXT"
    eventhubs_connection_string: SecretStr | None = Field(default=None, repr=False)
    topic_tasks: str = "agent.tasks"
    topic_results: str = "agent.results"
    topic_dead_letter: str = "agent.tasks.dlq"
    consumer_group: str = "agentverse-event-worker"

    # Azure Blob Storage for idempotent result records.
    blob_connection_string: SecretStr | None = Field(default=None, repr=False)
    blob_account_url: str | None = None
    blob_container: str = "agent-results"

    max_attempts: int = Field(default=3, ge=1, le=10)
    retry_backoff_seconds: float = Field(default=0.5, ge=0, le=30)
    task_timeout_seconds: float = Field(default=30.0, gt=0, le=300)
    poll_timeout_seconds: float = Field(default=1.0, gt=0, le=30)


@lru_cache
def get_settings() -> WorkerSettings:
    return WorkerSettings()
