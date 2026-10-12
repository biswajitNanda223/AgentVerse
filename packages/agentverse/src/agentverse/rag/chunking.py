import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from hashlib import sha256
from typing import Protocol

from agentverse.rag.models import Chunk, Document


class Chunker(Protocol):
    def split(self, document: Document) -> list[Chunk]: ...


def _chunk_id(document_id: str, ordinal: int, text: str) -> str:
    digest = sha256(f"{document_id}\0{ordinal}\0{text}".encode()).hexdigest()[:16]
    return f"{document_id}:{ordinal}:{digest}"


def _make_chunk(document: Document, ordinal: int, text: str, start: int) -> Chunk:
    return Chunk(
        id=_chunk_id(document.id, ordinal, text),
        document_id=document.id,
        text=text,
        ordinal=ordinal,
        source_uri=document.source_uri,
        tenant_id=document.tenant_id,
        start_char=start,
        end_char=start + len(text),
        metadata=document.metadata,
    )


@dataclass(frozen=True, slots=True)
class FixedWindowChunker:
    """Whitespace-token window; deterministic and dependency-free for baselines."""

    size: int = 400
    overlap: int = 60

    def __post_init__(self) -> None:
        if self.size < 1 or self.overlap < 0 or self.overlap >= self.size:
            raise ValueError("require size > 0 and 0 <= overlap < size")

    def split(self, document: Document) -> list[Chunk]:
        matches = list(re.finditer(r"\S+", document.text))
        if not matches:
            return []
        chunks: list[Chunk] = []
        step = self.size - self.overlap
        for ordinal, token_start in enumerate(range(0, len(matches), step)):
            window = matches[token_start : token_start + self.size]
            if not window:
                break
            start, end = window[0].start(), window[-1].end()
            chunks.append(_make_chunk(document, ordinal, document.text[start:end], start))
            if token_start + self.size >= len(matches):
                break
        return chunks


@dataclass(frozen=True, slots=True)
class RecursiveChunker:
    """Preserve coarse document structure, then fall back to token windows."""

    max_words: int = 400
    overlap: int = 40
    separators: Sequence[str] = ("\n## ", "\n\n", "\n", ". ")

    def split(self, document: Document) -> list[Chunk]:
        pieces = self._split_text(document.text, self.separators)
        chunks: list[Chunk] = []
        cursor = 0
        for piece in pieces:
            piece = piece.strip()
            if not piece:
                continue
            start = document.text.find(piece, cursor)
            start = max(start, cursor)
            subdoc = Document(
                id=document.id,
                text=piece,
                source_uri=document.source_uri,
                tenant_id=document.tenant_id,
                metadata=document.metadata,
            )
            windows = FixedWindowChunker(self.max_words, self.overlap).split(subdoc)
            for window in windows:
                chunks.append(
                    _make_chunk(document, len(chunks), window.text, start + window.start_char)
                )
            cursor = start + len(piece)
        return chunks

    def _split_text(self, text: str, separators: Sequence[str]) -> list[str]:
        if len(text.split()) <= self.max_words or not separators:
            return [text]
        separator, *remaining = separators
        parts = text.split(separator)
        if len(parts) == 1:
            return self._split_text(text, remaining)
        rebuilt: list[str] = []
        for index, part in enumerate(parts):
            suffix = separator if index < len(parts) - 1 else ""
            rebuilt.extend(self._split_text(part + suffix, remaining))
        return rebuilt


def contextualize(chunks: Iterable[Chunk], context: str) -> list[Chunk]:
    """Prepend bounded stable context while retaining original provenance."""

    prefix = " ".join(context.split())[:500]
    return [
        Chunk(
            id=chunk.id,
            document_id=chunk.document_id,
            text=f"Context: {prefix}\n\n{chunk.text}",
            ordinal=chunk.ordinal,
            source_uri=chunk.source_uri,
            tenant_id=chunk.tenant_id,
            start_char=chunk.start_char,
            end_char=chunk.end_char,
            parent_id=chunk.parent_id,
            metadata=chunk.metadata,
        )
        for chunk in chunks
    ]
