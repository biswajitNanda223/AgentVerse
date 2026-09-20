from enum import StrEnum

from pydantic import BaseModel, Field


class RetrievalMode(StrEnum):
    AUTO = "auto"
    RAGLESS = "ragless"
    SEMANTIC = "semantic"
    GRAPH = "graph"
    AGENTIC = "agentic"


class AskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=8_000)
    mode: RetrievalMode = RetrievalMode.AUTO
    conversation: list[str] = Field(default_factory=list, max_length=20)


class Citation(BaseModel):
    source_uri: str
    chunk_id: str
    score: float = Field(ge=0)


class AskResponse(BaseModel):
    answer: str
    mode: RetrievalMode
    citations: list[Citation]
    request_id: str
    steps: list[str]
    abstained: bool = False


class IngestDocument(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=2_000_000)
    source_uri: str = Field(min_length=1, max_length=2_048)


class IngestRequest(BaseModel):
    documents: list[IngestDocument] = Field(min_length=1, max_length=100)
