from pathlib import Path

import pytest

from decision_rag.loaders import load_corpus, parse_pdf
from decision_rag.local import LexicalDecisionModel
from decision_rag.navigator import DecisionNavigator
from decision_rag.sample_pdf import build_pdf, markdown_to_html
from decision_rag.testing import ScriptedModel

DATA = Path(__file__).resolve().parents[1] / "data"
SCENARIOS = DATA / "project_slm"
IDS = {"ADK": 10, "TEL": 8, "GOV": 9, "VEC": 8, "UX": 9, "BKD": 8, "SCL": 8}


def test_project_slm_markdown_has_exactly_the_sixty_scenarios_given() -> None:
    tree = load_corpus(SCENARIOS)
    sections = [n for n in tree.nodes.values() if n.kind == "section"]
    assert len(sections) == 60
    for prefix, expected in IDS.items():
        assert sum(s.title.startswith(f"[{prefix}-") for s in sections) == expected
    assert [c.title for c in tree.root.children] == ["project_slm"]  # files at the root: one topic
    assert len(tree.root.children[0].children) == 7  # seven domains


def test_pdf_round_trip_preserves_titles_sections_and_pages(tmp_path: Path) -> None:
    pdf = tmp_path / "pack.pdf"
    pages = build_pdf(sorted(SCENARIOS.glob("*.md")), pdf)
    assert pages >= 4
    documents = parse_pdf(pdf, "pack.pdf")
    assert len(documents) == 7
    titles = [d[0] for d in documents]
    assert titles[1] == "Domain 2: Agent Telemetry, Observability & FinOps (AC-12)"  # wrapped title
    assert "Write-Back" in titles[5] and "ﬂ" not in titles[5]  # ligature and hyphen wrap fixed
    section_titles = [t for _, sections in documents for t in sections]
    assert len(section_titles) == 60 and all(t.startswith("[") for t in section_titles)
    sources = {p[1] for _, sections in documents for ps in sections.values() for p in ps}  # type: ignore[index]
    assert any(s.endswith("p.1") for s in sources) and any(s.endswith("p.4") for s in sources)


def test_pdf_and_markdown_give_the_same_scenarios(tmp_path: Path) -> None:
    folder = tmp_path / "pdfs"
    folder.mkdir()
    build_pdf(sorted(SCENARIOS.glob("*.md")), folder / "Project_SLM_Scenarios.pdf")
    from_pdf = load_corpus(folder)
    from_md = load_corpus(SCENARIOS)

    def titles(tree: object) -> set[str]:
        return {n.title for n in tree.nodes.values() if n.kind == "section"}  # type: ignore[attr-defined]

    assert titles(from_pdf) == titles(from_md)


def test_committed_sample_pdf_loads_and_cites_pages() -> None:
    tree = load_corpus(DATA / "project_slm_pdf")
    sources = {p.source for p in tree.passages()}
    assert all(s and s.startswith("Project_SLM_Scenarios.pdf p.") for s in sources)
    assert len(tree.passages()) >= 60


def test_markdown_to_html_escapes_text() -> None:
    assert "&lt;2 seconds" in markdown_to_html("## [UX-01] x\n\nload in <2 seconds & fast")


def test_single_file_corpus_and_missing_content(tmp_path: Path) -> None:
    only = tmp_path / "one.md"
    only.write_text("# One\n\n## Part\n\nA paragraph that is certainly long enough to be kept.\n")
    assert len(load_corpus(only).passages()) == 1
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(ValueError, match="no Markdown or PDF passages"):
        load_corpus(empty)


async def test_navigation_skips_the_model_when_a_step_has_one_option() -> None:
    tree = load_corpus(SCENARIOS)
    model = ScriptedModel(lambda c: 0.9 if "[ADK-02]" in c.text or "Domain 1" in c.text else 0.1)
    result = await DecisionNavigator(tree, model).navigate("runaway loop")
    first = result.steps[0]  # one topic only: nothing to compare
    assert len(first.candidates) == 1 and first.model_calls == 0
    assert result.model_calls == sum(s.model_calls for s in result.steps)
    assert all(len(call) > 1 for call in model.calls)  # the model was never asked about one option


async def test_stand_in_finds_scenarios_in_the_sample_data() -> None:
    tree = load_corpus(SCENARIOS)
    nav = DecisionNavigator(tree, LexicalDecisionModel())
    result = await nav.navigate("How do we mask unit prices for site engineers?")
    assert result.passages[0].node.parent is not None
    assert result.passages[0].node.parent.title.startswith("[GOV-05]")
