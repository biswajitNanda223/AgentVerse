"""Production-oriented chunking strategies with deterministic local defaults.

The local implementations are intentionally dependency-light. Embedding-backed semantic and
late chunking accept injected functions so a production model can be substituted without
coupling document parsing to a specific provider.
"""

import ast
import csv
import io
import re
from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass, replace
from hashlib import sha256
from html.parser import HTMLParser
from itertools import pairwise

from agentverse.rag.chunking import FixedWindowChunker
from agentverse.rag.models import Chunk, Document
from agentverse.rag.retrieval import tokenize

Similarity = Callable[[str, str], float]


def _id(document_id: str, kind: str, ordinal: int, text: str) -> str:
    digest = sha256(f"{document_id}\0{kind}\0{ordinal}\0{text}".encode()).hexdigest()[:12]
    return f"{document_id}:{kind}:{ordinal}:{digest}"


def _chunks(document: Document, parts: Iterable[tuple[str, int]], kind: str) -> list[Chunk]:
    output: list[Chunk] = []
    for ordinal, (text, start) in enumerate(parts):
        clean = text.strip()
        if not clean:
            continue
        actual_start = document.text.find(clean, max(0, start))
        actual_start = start if actual_start < 0 else actual_start
        output.append(
            Chunk(
                id=_id(document.id, kind, ordinal, clean),
                document_id=document.id,
                text=clean,
                ordinal=ordinal,
                source_uri=document.source_uri,
                tenant_id=document.tenant_id,
                start_char=actual_start,
                end_char=actual_start + len(clean),
                metadata={**document.metadata, "chunking_strategy": kind},
            )
        )
    return output


@dataclass(frozen=True, slots=True)
class SentenceChunker:
    max_words: int = 180
    overlap_sentences: int = 1

    def split(self, document: Document) -> list[Chunk]:
        sentences = [part for part in re.split(r"(?<=[.!?])\s+", document.text) if part.strip()]
        groups: list[tuple[str, int]] = []
        current: list[str] = []
        cursor = 0
        for sentence in sentences:
            if current and len(tokenize(" ".join([*current, sentence]))) > self.max_words:
                text = " ".join(current)
                groups.append((text, document.text.find(current[0], cursor)))
                cursor = groups[-1][1] + len(text)
                current = current[-self.overlap_sentences :] if self.overlap_sentences else []
            current.append(sentence)
        if current:
            groups.append((" ".join(current), document.text.find(current[0], cursor)))
        return _chunks(document, groups, "sentence")


@dataclass(frozen=True, slots=True)
class ParagraphChunker:
    max_words: int = 350

    def split(self, document: Document) -> list[Chunk]:
        parts: list[tuple[str, int]] = []
        for match in re.finditer(r"(?:^|\n\s*\n)(.+?)(?=\n\s*\n|$)", document.text, re.S):
            paragraph = match.group(1).strip()
            if len(tokenize(paragraph)) <= self.max_words:
                parts.append((paragraph, match.start(1)))
            else:
                subdoc = replace(document, text=paragraph)
                for chunk in FixedWindowChunker(self.max_words, 0).split(subdoc):
                    parts.append((chunk.text, match.start(1) + chunk.start_char))
        return _chunks(document, parts, "paragraph")


def lexical_jaccard(left: str, right: str) -> float:
    left_terms, right_terms = set(tokenize(left)), set(tokenize(right))
    union = left_terms | right_terms
    return len(left_terms & right_terms) / len(union) if union else 1.0


@dataclass(frozen=True, slots=True)
class SemanticChunker:
    """Break at sentence transitions below a similarity threshold."""

    similarity: Similarity = lexical_jaccard
    breakpoint: float = 0.08
    max_words: int = 400

    def split(self, document: Document) -> list[Chunk]:
        sentences = [part for part in re.split(r"(?<=[.!?])\s+", document.text) if part.strip()]
        if not sentences:
            return []
        grouped: list[list[str]] = [[sentences[0]]]
        for previous, sentence in pairwise(sentences):
            too_large = len(tokenize(" ".join([*grouped[-1], sentence]))) > self.max_words
            if too_large or self.similarity(previous, sentence) < self.breakpoint:
                grouped.append([sentence])
            else:
                grouped[-1].append(sentence)
        cursor = 0
        parts = []
        for group in grouped:
            text = " ".join(group)
            start = document.text.find(group[0], cursor)
            parts.append((text, start))
            cursor = start + len(text)
        return _chunks(document, parts, "semantic")


@dataclass(frozen=True, slots=True)
class MarkdownChunker:
    """Keep headings with their section and preserve fenced code blocks."""

    max_words: int = 450

    def split(self, document: Document) -> list[Chunk]:
        starts = [match.start() for match in re.finditer(r"(?m)^#{1,6}\s+", document.text)]
        if not starts:
            return ParagraphChunker(self.max_words).split(document)
        starts.append(len(document.text))
        parts = [(document.text[a:b], a) for a, b in pairwise(starts)]
        return _chunks(document, parts, "markdown")


class _BlockHtmlParser(HTMLParser):
    block_tags = frozenset(
        {"article", "section", "p", "li", "h1", "h2", "h3", "h4", "pre", "table"}
    )

    def __init__(self) -> None:
        super().__init__()
        self.blocks: list[str] = []
        self._current: list[str] = []
        self._depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        if tag in self.block_tags:
            self._depth += 1

    def handle_data(self, data: str) -> None:
        if self._depth:
            self._current.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in self.block_tags and self._depth:
            self._depth -= 1
            if self._depth == 0:
                text = " ".join("".join(self._current).split())
                if text:
                    self.blocks.append(text)
                self._current = []


class HtmlChunker:
    """Extract semantic HTML blocks while excluding scripts/styles by omission."""

    def split(self, document: Document) -> list[Chunk]:
        parser = _BlockHtmlParser()
        parser.feed(document.text)
        cursor = 0
        parts = []
        for block in parser.blocks:
            start = document.text.find(block, cursor)
            start = cursor if start < 0 else start
            parts.append((block, start))
            cursor = start
        return _chunks(document, parts, "html")


@dataclass(frozen=True, slots=True)
class LayoutElement:
    text: str
    page: int
    kind: str
    coordinates: tuple[float, float, float, float] | None = None


class LayoutAwareChunker:
    """Convert PDF/OCR parser elements without mixing pages, tables or headings."""

    def split_elements(self, document: Document, elements: Sequence[LayoutElement]) -> list[Chunk]:
        chunks = _chunks(document, ((element.text, 0) for element in elements), "layout")
        return [
            replace(
                chunk,
                metadata={
                    **chunk.metadata,
                    "page": element.page,
                    "element_kind": element.kind,
                    "coordinates": element.coordinates,
                },
            )
            for chunk, element in zip(chunks, elements, strict=True)
        ]


@dataclass(frozen=True, slots=True)
class PropositionChunker:
    """Use an injected, evaluated decomposer to index atomic factual propositions."""

    decompose: Callable[[str], Sequence[str]]

    def split(self, document: Document) -> list[Chunk]:
        propositions = list(
            dict.fromkeys(item.strip() for item in self.decompose(document.text) if item.strip())
        )
        return _chunks(document, ((item, 0) for item in propositions), "proposition")


class PythonCodeChunker:
    """Split Python at top-level definitions while preserving decorators and docstrings."""

    def split(self, document: Document) -> list[Chunk]:
        try:
            tree = ast.parse(document.text)
        except SyntaxError:
            return FixedWindowChunker(200, 20).split(document)
        lines = document.text.splitlines(keepends=True)
        offsets = [0]
        for line in lines:
            offsets.append(offsets[-1] + len(line))
        nodes = [
            node
            for node in tree.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        ]
        parts: list[tuple[str, int]] = []
        if nodes and nodes[0].lineno > 1:
            parts.append(("".join(lines[: nodes[0].lineno - 1]), 0))
        for node in nodes:
            start_line = min([node.lineno, *(d.lineno for d in node.decorator_list)]) - 1
            end_line = node.end_lineno or node.lineno
            parts.append(("".join(lines[start_line:end_line]), offsets[start_line]))
        return _chunks(document, parts or [(document.text, 0)], "python-code")


@dataclass(frozen=True, slots=True)
class TableChunker:
    rows_per_chunk: int = 25

    def split(self, document: Document) -> list[Chunk]:
        rows = list(csv.reader(io.StringIO(document.text)))
        if not rows:
            return []
        header, data = rows[0], rows[1:]
        parts = []
        cursor = 0
        for start in range(0, len(data), self.rows_per_chunk):
            buffer = io.StringIO()
            csv.writer(buffer, lineterminator="\n").writerows(
                [header, *data[start : start + self.rows_per_chunk]]
            )
            text = buffer.getvalue().strip()
            parts.append((text, cursor))
            cursor += len(text)
        return _chunks(document, parts, "table")


@dataclass(frozen=True, slots=True)
class ParentChildChunker:
    parent_words: int = 800
    child_words: int = 180
    child_overlap: int = 30

    def split(self, document: Document) -> tuple[list[Chunk], list[Chunk]]:
        parents = FixedWindowChunker(self.parent_words, 0).split(document)
        children: list[Chunk] = []
        for parent in parents:
            subdoc = replace(document, text=parent.text)
            for child in FixedWindowChunker(self.child_words, self.child_overlap).split(subdoc):
                children.append(
                    replace(
                        child,
                        id=_id(document.id, "child", len(children), child.text),
                        ordinal=len(children),
                        start_char=parent.start_char + child.start_char,
                        end_char=parent.start_char + child.end_char,
                        parent_id=parent.id,
                        metadata={**child.metadata, "chunking_strategy": "parent-child"},
                    )
                )
        return parents, children


@dataclass(frozen=True, slots=True)
class LateChunker:
    """Attach whole-document context produced after full-document encoding/summarization."""

    base: SentenceChunker = SentenceChunker()
    context_builder: Callable[[str], str] = lambda text: " ".join(text.split())[:500]

    def split(self, document: Document) -> list[Chunk]:
        context = self.context_builder(document.text)
        return [
            replace(
                chunk,
                text=f"Document context: {context}\n\n{chunk.text}",
                metadata={**chunk.metadata, "chunking_strategy": "late"},
            )
            for chunk in self.base.split(document)
        ]
