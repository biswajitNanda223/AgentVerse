"""Build a CorpusTree from the structure files already have: folders, headings, pages.

Folder -> topic (files directly under the root use the root folder's name), file -> document,
H2/H3 heading (Markdown) or bold sub-heading (PDF) -> section, paragraph -> passage. PDFs may
hold several documents (each large title starts one). Fenced code, hidden folders and caches are
skipped. Each passage records its source (file, and page for PDFs) for citations.
"""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path

from decision_rag.corpus import CorpusTree, Outline, PassageSpec

SKIP_DIRS = {"node_modules", "__pycache__", "site-packages", "dist", "build"}
FENCE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
MIN_PASSAGE_CHARS = 40
Sections = dict[str, list[PassageSpec]]


def parse_markdown(markdown: str, fallback_title: str, source: str) -> tuple[str, Sections]:
    text = FENCE.sub("", markdown)
    title = fallback_title
    sections: Sections = {}
    current = "Overview"
    buffer: list[str] = []

    def flush() -> None:
        paragraph = " ".join(" ".join(buffer).split())
        buffer.clear()
        if len(paragraph) >= MIN_PASSAGE_CHARS:
            sections.setdefault(current, []).append((paragraph, source))

    for line in text.splitlines():
        heading = re.match(r"^(#{1,3})\s+(.*)", line)
        if heading:
            flush()
            if len(heading.group(1)) == 1 and title == fallback_title:
                title = heading.group(2).strip()
            else:
                current = heading.group(2).strip()
        elif not line.strip():
            flush()
        else:
            buffer.append(line.strip())
    flush()
    return title, sections


def parse_pdf(path: Path, source: str) -> list[tuple[str, Sections]]:
    """Return the documents in a PDF. Structure comes from font size and weight.

    The most common size is the body. A much larger block is a document title, a short bold
    block is a section heading, everything else is a paragraph. Bare page numbers are dropped.
    Tables and images are not interpreted: table text is read as ordinary paragraphs.
    """

    import pymupdf

    blocks: list[tuple[int, str, float, bool]] = []
    with pymupdf.open(path) as pdf:
        for page in pdf:
            for block in page.get_text("dict")["blocks"]:
                if block.get("type") != 0:
                    continue
                lines = [
                    " ".join(s["text"] for s in line["spans"]).strip() for line in block["lines"]
                ]
                spans = [s for line in block["lines"] for s in line["spans"] if s["text"].strip()]
                text = _join_lines([unicodedata.normalize("NFKC", t) for t in lines if t])
                if not spans or not text or re.fullmatch(r"(?i)(page\s*)?\d+", text):
                    continue
                size = max(s["size"] for s in spans)
                bold = all((s["flags"] & 16) or "bold" in s["font"].lower() for s in spans)
                blocks.append((page.number + 1, text, size, bool(bold)))

    if not blocks:
        return []
    weights: Counter[float] = Counter()
    for _, text, size, _ in blocks:
        weights[round(size, 1)] += len(text)
    body = weights.most_common(1)[0][0]

    def kind(size: float, bold: bool) -> str:
        if size >= body * 1.35:
            return "title"
        if bold and size >= body * 1.05:
            return "heading"
        return "text"

    # A long title or heading can wrap into several blocks: merge neighbours of the same kind.
    merged: list[tuple[int, str, str]] = []
    for page_no, text, size, bold in blocks:
        k = kind(size, bold)
        if merged and k != "text" and merged[-1][2] == k:
            merged[-1] = (merged[-1][0], f"{merged[-1][1]} {text}", k)
        else:
            merged.append((page_no, text, k))

    documents: list[tuple[str, Sections]] = []
    title, current = path.stem, "Overview"
    sections: Sections = {}
    started = False
    for page_no, text, k in merged:
        if k == "title":
            if started and sections:
                documents.append((title, sections))
            title, sections, current, started = text, {}, "Overview", True
        elif k == "heading":
            current = text
        elif len(text) >= MIN_PASSAGE_CHARS:
            sections.setdefault(current, []).append((text, f"{source} p.{page_no}"))
    if sections:
        documents.append((title, sections))
    return documents


def _join_lines(lines: list[str]) -> str:
    """Join wrapped lines; a line ending in "-" or "/" joins the next without a space."""

    text = ""
    for line in lines:
        text = f"{text}{line}" if text.endswith(("-", "/")) else f"{text} {line}"
    return " ".join(text.split())


def load_corpus(root: Path, name: str | None = None) -> CorpusTree:
    """Load a folder (recursively) or a single .md/.pdf file."""

    root = root.resolve()
    base = root if root.is_dir() else root.parent
    files = (
        sorted(p for ext in ("*.md", "*.pdf") for p in root.rglob(ext)) if root.is_dir() else [root]
    )
    outline: dict[str, dict[str, Sections]] = {}
    for path in files:
        relative = path.relative_to(base)
        if any(part in SKIP_DIRS or part.startswith(".") for part in relative.parts[:-1]):
            continue
        topic = relative.parts[0] if len(relative.parts) > 1 else base.name
        source = relative.as_posix()
        if path.suffix.lower() == ".pdf":
            parsed = parse_pdf(path, source)
        else:
            parsed = [parse_markdown(path.read_text(encoding="utf-8"), path.stem, source)]
        for title, sections in parsed:
            if sections:
                outline.setdefault(topic, {})[f"{title} ({source})"] = sections
    if not outline:
        raise ValueError(f"no Markdown or PDF passages found under {root}")
    return CorpusTree.from_outline(_as_outline(outline), name or base.name)


def load_markdown_corpus(root: Path, name: str | None = None) -> CorpusTree:
    return load_corpus(root, name)


def _as_outline(outline: dict[str, dict[str, Sections]]) -> Outline:
    return outline
