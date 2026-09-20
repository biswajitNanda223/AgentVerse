from fastapi.testclient import TestClient

from solutions.agentic_rag_end_to_end.app.a2a_server import app


def test_agent_card_and_a2a_error_contract() -> None:
    client = TestClient(app)
    card = client.get("/.well-known/agent-card.json")
    assert card.status_code == 200
    assert card.json()["skills"][0]["id"] == "architecture_qa"
    error = client.post("/", json={"jsonrpc": "2.0", "id": "1", "method": "unknown"})
    assert error.json()["error"]["code"] == -32601


def test_a2a_message_send_contract() -> None:
    client = TestClient(app)
    response = client.post(
        "/",
        json={
            "jsonrpc": "2.0",
            "id": "request-1",
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "messageId": "message-1",
                    "contextId": "context-1",
                    "parts": [{"kind": "text", "text": "What is semantic RAG?"}],
                }
            },
        },
    )
    body = response.json()
    assert body["id"] == "request-1"
    assert body["result"]["status"]["state"] == "completed"
    assert body["result"]["artifacts"][0]["name"] == "grounded-answer"
