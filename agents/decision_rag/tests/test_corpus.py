from pathlib import Path

import pytest

from decision_rag.corpus import CorpusTree
from decision_rag.markdown_loader import load_markdown_corpus
from decision_rag.sample_corpus import sample_tree


def test_sample_tree_has_four_levels_and_stable_ids() -> None:
    tree = sample_tree()
    kinds = {n.kind for n in tree.nodes.values()}
    assert kinds == {"corpus", "topic", "document", "section", "passage"}
    passage = tree.nodes["messaging/azure-event-hubs/kafka-compatibility/1"]
    assert passage.breadcrumb() == "Messaging > Azure Event Hubs > Kafka compatibility > Passage 1"
    assert passage.label().startswith("Event Hubs exposes a Kafka endpoint")
    assert len(tree.passages()) == 17


def test_descriptions_carry_structure_so_upper_levels_are_judgeable() -> None:
    tree = sample_tree()
    assert "Dead-letter queues" in tree.nodes["messaging"].description
    assert "When to dead-letter" in tree.nodes["messaging"].description
    assert "retries cannot fix" in tree.nodes["messaging/dead-letter-queues"].description


def test_duplicate_ids_are_rejected() -> None:
    outline = {"A": {"Doc": {"Sec": ["x" * 50]}}, "a": {"Doc": {"Sec": ["y" * 50]}}}
    with pytest.raises(ValueError, match="duplicate node id"):
        CorpusTree.from_outline(outline)


def test_markdown_loader_uses_folders_headings_and_paragraphs(tmp_path: Path) -> None:
    (tmp_path / "guides").mkdir()
    (tmp_path / "guides" / "deploy.md").write_text(
        "# Deploy guide\n\nIntro paragraph that is long enough to become a passage here.\n\n"
        "## Rollback\n\nRoll back by redeploying the previous image tag and verifying health.\n\n"
        "```bash\nkubectl rollout undo deployment/api\n```\n\nShort.\n",
        encoding="utf-8",
    )
    (tmp_path / "readme.md").write_text(
        "# Top\n\nA top level file with enough text to count as a passage.\n", encoding="utf-8"
    )
    (tmp_path / ".pytest_cache").mkdir()
    (tmp_path / ".pytest_cache" / "README.md").write_text(
        "# cache\n\n" + "hidden " * 20, encoding="utf-8"
    )
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "skip.md").write_text(
        "# X\n\n" + "skipped " * 20, encoding="utf-8"
    )

    tree = load_markdown_corpus(tmp_path)
    titles = {n.title for n in tree.nodes.values()}
    assert "guides" in titles and "(root)" in titles
    assert "Rollback" in titles and "Overview" in titles
    texts = " ".join(p.text or "" for p in tree.passages())
    assert "kubectl" not in texts  # fenced code dropped
    assert "Short." not in texts  # below the minimum passage length
    assert "skipped" not in texts  # ignored directory
    assert "hidden" not in texts  # hidden directories such as .pytest_cache


def test_markdown_loader_rejects_empty_folders(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="no Markdown passages"):
        load_markdown_corpus(tmp_path)
