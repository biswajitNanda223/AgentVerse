"""Keep the docs honest: embedded diagrams must match their sources, images must exist."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIAGRAMS = ROOT / "docs" / "diagrams"
FENCE = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)


def doc_files() -> list[Path]:
    return [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]


def test_every_embedded_diagram_matches_a_source_file() -> None:
    sources = {p.read_text(encoding="utf-8").rstrip("\n") for p in DIAGRAMS.glob("*.mmd")}
    embedded = 0
    for doc in doc_files():
        for block in FENCE.findall(doc.read_text(encoding="utf-8")):
            embedded += 1
            assert block.rstrip("\n") in sources, f"{doc.name} embeds a diagram with no .mmd source"
    assert embedded >= 8


def test_every_source_diagram_has_rendered_images() -> None:
    for source in DIAGRAMS.glob("*.mmd"):
        for suffix in (".png", ".svg"):
            image = ROOT / "docs" / "images" / (source.stem + suffix)
            assert image.exists() and image.stat().st_size > 1000, f"missing {image.name}"


def test_readme_image_links_resolve() -> None:
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    links = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", text)
    assert len(links) >= 3
    for link in links:
        assert (ROOT / link).exists(), link


def test_docs_state_the_paper_scope_caveat() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "not from the full text" in readme
    assert "own design" in readme
