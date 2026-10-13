from typing import Literal

from pydantic import BaseModel, Field

SAFE_ID = r"^[A-Za-z0-9._-]+$"  # ids become blob names: no slashes or traversal


class TaskEvent(BaseModel):
    """Inbound Kafka message. `id` is the idempotency key within a tenant."""

    id: str = Field(min_length=1, max_length=128, pattern=SAFE_ID)
    tenant_id: str = Field(default="public", min_length=1, max_length=64, pattern=SAFE_ID)
    question: str = Field(min_length=1, max_length=4000)


class Answer(BaseModel):
    text: str
    citations: list[str] = Field(default_factory=list)
    abstained: bool = False


class ResultEvent(BaseModel):
    event_id: str
    tenant_id: str
    status: Literal["answered", "abstained"]
    answer: str
    citations: list[str]
    attempts: int


class DeadLetter(BaseModel):
    event_id: str | None
    reason: str
    attempts: int
    payload: str
