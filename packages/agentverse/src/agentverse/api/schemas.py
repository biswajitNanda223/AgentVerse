from pydantic import BaseModel, Field


class DocumentInput(BaseModel):
    id: str = Field(min_length=1, max_length=128)
    text: str = Field(min_length=1, max_length=1_000_000)
    source_uri: str = Field(min_length=1, max_length=2_048)


class IngestRequest(BaseModel):
    documents: list[DocumentInput] = Field(min_length=1, max_length=100)


class QueryRequest(BaseModel):
    query: str = Field(min_length=1, max_length=8_000)
    top_k: int = Field(default=5, ge=1, le=20)


class QueryResponse(BaseModel):
    query: str
    context: str
    citations: list[str]
    corrected: bool
    request_id: str
