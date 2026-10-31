"""Build a CorpusTree from a folder of Markdown files, using the structure already there.

Folder name -> topic, file -> document (first H1 or file name), H2/H3 headings -> sections,
paragraphs -> passages. Fenced code blocks (including Mermaid) are dropped.
"""

from __future__ import annotations

import re
from pathlib import Path

from decision_rag.corpus import CorpusTree, Outline

SKIP_DIRS = {"node_modules", "__pycache__", "site-packages", "dist", "build"}
FENCE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
MIN_PASSAGE_CHARS = 40


def load_markdown_corpus(root: Path, name: str | None = None) -> CorpusTree:
    root = root.resolve()
    outline: dict[str, dict[str, dict[str, list[str]]]] = {}
    for path in sorted(root.rglob("*.md")):
        relative = path.relative_to(root)
        if any(part in SKIP_DIRS or part.startswith(".") for part in relative.parts[:-1]):
            continue
        title, sections = _parse(path.read_text(encoding="utf-8"), path.stem)
        if not sections:
            continue
        topic = relative.parts[0] if len(relative.parts) > 1 else "(root)"
        doc = f"{title} ({relative.as_posix()})"
        outline.setdefault(topic, {})[doc] = sections
    if not outline:
        raise ValueError(f"no Markdown passages found under {root}")
    return CorpusTree.from_outline(_as_outline(outline), name or root.name)


def _as_outline(outline: dict[str, dict[str, dict[str, list[str]]]]) -> Outline:
    return outline


def _parse(markdown: str, fallback_title: str) -> tuple[str, dict[str, list[str]]]:
    text = FENCE.sub("", markdown)
    title = fallback_title
    sections: dict[str, list[str]] = {}
    current = "Overview"
    buffer: list[str] = []

    def flush() -> None:
        paragraph = " ".join(" ".join(buffer).split())
        buffer.clear()
        if len(paragraph) >= MIN_PASSAGE_CHARS:
            sections.setdefault(current, []).append(paragraph)

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
