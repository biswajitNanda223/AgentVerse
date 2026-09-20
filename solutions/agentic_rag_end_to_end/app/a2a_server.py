from typing import Any
from uuid import uuid4

from fastapi import FastAPI

from agentverse.protocols.a2a_card import build_agent_card
from solutions.agentic_rag_end_to_end.app.adk_agent import retrieve_knowledge

app = FastAPI(title="AgentVerse A2A knowledge peer")


@app.get("/.well-known/agent-card.json")
async def agent_card() -> dict[str, Any]:
    card = build_agent_card("http://localhost:8001")
    card["name"] = "AgentVerse Agentic RAG Peer"
    return card


@app.post("/")
async def message_send(envelope: dict[str, Any]) -> dict[str, Any]:
    """Minimal A2A JSON-RPC message/send example; add peer auth before public exposure."""

    request_id = envelope.get("id")
    if envelope.get("method") != "message/send":
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {"code": -32601, "message": "method not found"},
        }
    message = envelope.get("params", {}).get("message", {})
    text = " ".join(
        part.get("text", "") for part in message.get("parts", []) if part.get("kind") == "text"
    )
    result = retrieve_knowledge(text)
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "result": {
            "id": str(uuid4()),
            "contextId": message.get("contextId", str(uuid4())),
            "status": {"state": "completed"},
            "artifacts": [
                {
                    "artifactId": str(uuid4()),
                    "name": "grounded-answer",
                    "parts": [{"kind": "text", "text": str(result["answer"])}],
                    "metadata": {"citations": result["citations"], "steps": result["steps"]},
                }
            ],
        },
    }
