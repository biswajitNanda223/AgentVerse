import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
DATA = REPO / "agents" / "decision_rag" / "data" / "project_slm"
DOCS = REPO / "docs" / "project-slm"


def scenario_ids() -> list[str]:
    ids: list[str] = []
    for path in sorted(DATA.glob("domain-*.md")):
        ids += re.findall(r"^## \[([A-Z]+-\d+)\]", path.read_text(encoding="utf-8"), re.M)
    return ids


def test_every_supplied_scenario_appears_in_the_architecture_diagram() -> None:
    ids = scenario_ids()
    assert len(ids) == 60 and len(set(ids)) == 60
    page = (DOCS / "diagrams" / "01-adk-agent-end-to-end.html").read_text(encoding="utf-8")
    missing = [i for i in ids if f"[{i}]" not in page]
    assert not missing, f"scenarios missing from the diagram: {missing}"


def test_traceability_table_lists_all_scenarios_and_images_exist() -> None:
    readme = (DOCS / "README.md").read_text(encoding="utf-8")
    for sid in scenario_ids():
        assert f"| {sid} |" in readme
    for name in ("01-adk-agent-end-to-end.png", "02-agent-engine-advantages.png"):
        image = DOCS / "images" / name
        assert image.exists() and image.stat().st_size > 50_000
        assert name in readme


def test_diagram_does_not_claim_the_cost_hypothesis_is_true() -> None:
    page = (DOCS / "diagrams" / "02-agent-engine-advantages.html").read_text(encoding="utf-8")
    assert "Not supported by what I found" in page
