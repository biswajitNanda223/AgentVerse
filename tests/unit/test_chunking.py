from agentverse.rag.chunking import FixedWindowChunker, RecursiveChunker
from agentverse.rag.models import Document


def test_fixed_window_is_bounded_and_overlaps() -> None:
    document = Document("d", "one two three four five six", "memory://d", "t")
    chunks = FixedWindowChunker(size=4, overlap=2).split(document)
    assert [chunk.text for chunk in chunks] == ["one two three four", "three four five six"]
    assert chunks[0].end_char == len("one two three four")


def test_recursive_preserves_all_sections() -> None:
    document = Document("d", "First section.\n\nSecond section.", "memory://d", "t")
    chunks = RecursiveChunker(max_words=2, overlap=0).split(document)
    combined = " ".join(chunk.text for chunk in chunks)
    assert "First" in combined and "Second" in combined
