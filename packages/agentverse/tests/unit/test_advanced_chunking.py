from agentverse.rag.advanced_chunking import (
    LateChunker,
    MarkdownChunker,
    ParentChildChunker,
    PythonCodeChunker,
    SemanticChunker,
    SentenceChunker,
    TableChunker,
)
from agentverse.rag.models import Document


def document(text: str) -> Document:
    return Document("d", text, "memory://d", "tenant")


def test_sentence_and_semantic_chunking() -> None:
    source = document("Cats purr softly. Cats sleep often. Databases store rows.")
    sentence = SentenceChunker(max_words=5).split(source)
    semantic = SemanticChunker(breakpoint=0.1).split(source)
    assert len(sentence) >= 2
    assert len(semantic) == 2
    assert all(chunk.metadata["chunking_strategy"] == "semantic" for chunk in semantic)


def test_document_code_and_table_chunkers() -> None:
    markdown = MarkdownChunker().split(document("# One\nText\n## Two\nMore"))
    code = PythonCodeChunker().split(document("x = 1\n\ndef one():\n    return 1\n"))
    table = TableChunker(rows_per_chunk=1).split(document("a,b\n1,2\n3,4\n"))
    assert len(markdown) == 2
    assert any("def one" in chunk.text for chunk in code)
    assert len(table) == 2 and all("a,b" in chunk.text for chunk in table)


def test_parent_child_and_late_keep_lineage() -> None:
    source = document(" ".join(f"word{i}" for i in range(50)))
    parents, children = ParentChildChunker(20, 8, 2).split(source)
    late = LateChunker().split(source)
    parent_ids = {parent.id for parent in parents}
    assert children and all(child.parent_id in parent_ids for child in children)
    assert all(chunk.text.startswith("Document context:") for chunk in late)
