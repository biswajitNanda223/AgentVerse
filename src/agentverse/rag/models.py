from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


@dataclass(frozen=True, slots=True)
class Document:
    id: str
    text: str
    source_uri: str
    tenant_id: str
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class Chunk:
    id: str
    document_id: str
    text: str
    ordinal: int
    source_uri: str
    tenant_id: str
    start_char: int
    end_char: int
    parent_id: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))


@dataclass(frozen=True, slots=True)
class RetrievalCandidate:
    chunk: Chunk
    score: float
    dense_rank: int | None = None
    lexical_rank: int | None = None
    rationale: str | None = None
