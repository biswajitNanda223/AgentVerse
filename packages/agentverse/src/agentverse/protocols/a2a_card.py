"""A2A discovery metadata kept separate from transport/runtime wiring."""

from typing import Any


def build_agent_card(base_url: str) -> dict[str, Any]:
    """Return a JSON-serializable Agent Card for a read-only knowledge agent."""

    return {
        "name": "AgentVerse Knowledge Agent",
        "description": "Answers production ADK and RAG architecture questions with evidence.",
        "url": base_url.rstrip("/"),
        "version": "0.1.0",
        "protocolVersion": "0.3.0",
        "capabilities": {"streaming": False, "pushNotifications": False},
        "defaultInputModes": ["text/plain"],
        "defaultOutputModes": ["text/plain", "application/json"],
        "skills": [
            {
                "id": "architecture_qa",
                "name": "Architecture Q&A",
                "description": "Retrieves evidence about ADK, RAG, MCP, A2A and production AI.",
                "tags": ["adk", "rag", "mcp", "a2a"],
                "examples": ["How should I evaluate a corrective RAG pipeline?"],
            }
        ],
    }
