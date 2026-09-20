from mcp.server.mcpserver import MCPServer

from solutions.agentic_rag_end_to_end.app.adk_agent import retrieve_knowledge

mcp = MCPServer(
    "agentverse-agentic-rag",
    instructions="Read-only grounded retrieval tools. Clients must supply a tenant scope.",
)


@mcp.tool()
def search_knowledge(question: str, tenant_id: str = "public") -> dict[str, object]:
    """Retrieve grounded evidence with citations. This tool performs no external writes."""

    return retrieve_knowledge(question, tenant_id)


if __name__ == "__main__":
    mcp.run(transport="stdio")
