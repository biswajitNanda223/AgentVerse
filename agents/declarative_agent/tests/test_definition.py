from pathlib import Path

import yaml
from google.adk.skills import load_skills_from_dir
from google.adk.tools.skill_toolset import SkillToolset

from declarative_agent.adk_agent import DEFINITION, root_agent
from declarative_agent.skill_set import SKILLS_DIR

EXPECTED_SKILLS = {
    "governed-sql",
    "evidence-and-citations",
    "write-back-approval",
    "loop-and-budget-discipline",
}


def test_the_agent_is_defined_by_the_yaml_file() -> None:
    raw = yaml.safe_load(Path(DEFINITION).read_text(encoding="utf-8"))
    assert raw["name"] == root_agent.name == "governed_project_agent"
    assert raw["model"] == "gemini-2.5-flash"
    assert "Never invent a number" in root_agent.instruction


def test_yaml_wires_the_toolset_and_both_callbacks_by_dotted_path() -> None:
    assert [type(t) for t in root_agent.tools] == [SkillToolset]
    assert [f.__name__ for f in root_agent.canonical_before_model_callbacks] == ["llm_call_budget"]
    assert [f.__name__ for f in root_agent.canonical_before_tool_callbacks] == ["tool_guardrail"]


def test_four_valid_skills_with_progressive_disclosure() -> None:
    skills = {s.name: s for s in load_skills_from_dir(SKILLS_DIR)}
    assert set(skills) == EXPECTED_SKILLS
    for skill in skills.values():
        assert len(skill.frontmatter.description) > 40  # level 1: when to use it
        assert len(skill.instructions) > 200  # level 2: how
    assert skills["governed-sql"].resources.references  # level 3: on-demand detail
    assert skills["write-back-approval"].resources.references


def test_skills_unlock_exactly_the_tools_that_exist() -> None:
    skills = {s.name: s for s in load_skills_from_dir(SKILLS_DIR)}
    unlocked = {
        name: s.frontmatter.metadata.get("adk_additional_tools")
        for name, s in skills.items()
        if s.frontmatter.metadata.get("adk_additional_tools")
    }
    assert unlocked == {
        "governed-sql": ["run_governed_sql"],
        "write-back-approval": ["stage_write_back"],
    }
