from mcp.server.mcpserver import MCPServer

from agentverse.agents.tools import assess_risk, search_knowledge

mcp = MCPServer("agentverse-tools")


@mcp.tool()
def knowledge_search(query: str) -> dict[str, object]:
    """Search the public AgentVerse learning corpus."""

    return search_knowledge(query)


@mcp.tool()
def risk_assessment(action: str) -> dict[str, str | bool]:
    """Check whether an action requires human approval; does not perform the action."""

    return assess_risk(action)


if __name__ == "__main__":
    mcp.run(transport="stdio")
