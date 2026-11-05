"""The skills this agent can load, and the tools that only appear when a skill is loaded."""

from pathlib import Path

from google.adk.skills import load_skills_from_dir
from google.adk.tools.skill_toolset import SkillToolset

from declarative_agent.tools import run_governed_sql, stage_write_back

SKILLS_DIR = Path(__file__).parent / "skills"

# Referenced from root_agent.yaml by dotted path. Each skill names the tools it unlocks in its
# SKILL.md metadata (adk_additional_tools); until it is loaded the model cannot see them.
skill_toolset = SkillToolset(
    skills=load_skills_from_dir(SKILLS_DIR),
    additional_tools=[run_governed_sql, stage_write_back],
)
