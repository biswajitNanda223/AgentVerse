"""A corpus as a tree: topics -> documents -> sections -> passages.

Navigation needs structure, not an index. The structure is the one the corpus already has
(folders or categories, titles, headings, paragraphs); nothing is embedded or precomputed except
short extractive descriptions of each branch, built from titles and first sentences.
"""

from __future__ import annotations

import re
from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass, field

ROOT_ID = "<corpus>"  # slugs contain only [a-z0-9-], so no node can collide with this
LEVELS = ("corpus", "topic", "document", "section", "passage")
Outline = Mapping[str, Mapping[str, Mapping[str, Sequence[str]]]]  # topic -> doc -> section -> text


def slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "x"


@dataclass(eq=False)
class Node:
    id: str
    kind: str  # one of LEVELS
    title: str
    description: str  # what this branch contains, shown to the decision model
    text: str | None = None  # full text, passages only
    children: list[Node] = field(default_factory=list)
    parent: Node | None = field(default=None, repr=False)

    @property
    def level(self) -> int:
        return LEVELS.index(self.kind)

    @property
    def is_leaf(self) -> bool:
        return not self.children

    def label(self) -> str:
        """Short human label: the title, or the opening words for a passage."""
        return _clip(self.text or self.title, 48) if self.kind == "passage" else self.title

    def breadcrumb(self) -> str:
        titles: list[str] = []
        node: Node | None = self
        while node is not None and node.kind != "corpus":
            titles.append(node.title)
            node = node.parent
        return " > ".join(reversed(titles))


class CorpusTree:
    def __init__(self, root: Node) -> None:
        self.root = root
        self.nodes: dict[str, Node] = {}
        for node in self._walk(root):
            if node.id in self.nodes:
                raise ValueError(f"duplicate node id {node.id!r}")
            self.nodes[node.id] = node

    @staticmethod
    def _walk(node: Node) -> Iterator[Node]:
        yield node
        for child in node.children:
            yield from CorpusTree._walk(child)

    def passages(self) -> list[Node]:
        return [n for n in self.nodes.values() if n.kind == "passage"]

    def __len__(self) -> int:
        return len(self.nodes)

    @classmethod
    def from_outline(cls, outline: Outline, name: str = "corpus") -> CorpusTree:
        root = Node(id=ROOT_ID, kind="corpus", title=name, description=name)
        for topic_title, documents in outline.items():
            topic = _attach(root, "topic", slug(topic_title), topic_title, "")
            for doc_title, sections in documents.items():
                doc = _attach(topic, "document", f"{topic.id}/{slug(doc_title)}", doc_title, "")
                for section_title, passages in sections.items():
                    section = _attach(
                        doc, "section", f"{doc.id}/{slug(section_title)}", section_title, ""
                    )
                    for index, text in enumerate(passages, start=1):
                        passage = _attach(
                            section, "passage", f"{section.id}/{index}", f"Passage {index}", ""
                        )
                        passage.text = text
                        passage.description = _clip(text, 240)
                    section.description = _clip(passages[0], 160) if passages else ""
                doc.description = "Sections: " + "; ".join(
                    f"{sec.title} ({_clip(sec.description, 110)})" for sec in doc.children
                )
            topic.description = "Documents: " + "; ".join(
                f"{d.title} [{', '.join(sec.title for sec in d.children)}]" for d in topic.children
            )
        return cls(root)


def _attach(parent: Node, kind: str, node_id: str, title: str, description: str) -> Node:
    node = Node(id=node_id, kind=kind, title=title, description=description, parent=parent)
    parent.children.append(node)
    return node


def _clip(text: str, limit: int) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"
