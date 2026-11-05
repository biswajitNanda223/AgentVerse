"""Entry point for ADK and Agents CLI: builds the agent from its YAML definition."""

import os
from pathlib import Path
from typing import cast

from google.adk.agents import LlmAgent
from google.adk.agents.config_agent_utils import from_config

DEFINITION = Path(__file__).parent / "agent_definition" / "root_agent.yaml"

root_agent = cast(LlmAgent, from_config(str(DEFINITION)))

if os.environ.get("DECLARATIVE_AGENT_MODEL"):  # swap the model without touching the YAML
    root_agent.model = os.environ["DECLARATIVE_AGENT_MODEL"]
