import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FENCE = re.compile(r"```mermaid\n(.*?)```", re.DOTALL)


def test_readme_embeds_the_real_yaml_and_the_diagram_source() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    yaml_text = (ROOT / "src/declarative_agent/agent_definition/root_agent.yaml").read_text()
    assert yaml_text.strip() in readme  # the README can never drift from the real agent
    sources = {p.read_text().rstrip("\n") for p in (ROOT / "docs/diagrams").glob("*.mmd")}
    blocks = FENCE.findall(readme)
    assert blocks and all(b.rstrip("\n") in sources for b in blocks)


def test_images_exist_and_links_resolve() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for link in re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme):
        image = ROOT / link
        assert image.exists() and image.stat().st_size > 50_000, link


def test_docs_state_the_limits_honestly() -> None:
    readme = " ".join((ROOT / "README.md").read_text(encoding="utf-8").split())
    assert "Not run with a real model" in readme
    assert "Defence in depth" in readme
    assert "Synthetic data" in readme


def test_the_skill_guide_matches_the_loader_rules() -> None:
    guide = (ROOT / "docs/add-a-skill.md").read_text(encoding="utf-8")
    assert "folder name must equal" in guide and "adk_additional_tools" in guide
