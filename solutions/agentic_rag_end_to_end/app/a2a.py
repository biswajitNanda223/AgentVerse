from dataclasses import dataclass
from typing import Any
from uuid import uuid4

import httpx


@dataclass(frozen=True, slots=True)
class DelegatedArtifact:
    text: str
    source: str


class A2ADelegateClient:
    """Small A2A JSON-RPC client with deadlines and no credential forwarding."""

    def __init__(self, base_url: str, timeout_seconds: float = 8.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout_seconds

    async def discover(self) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(f"{self.base_url}/.well-known/agent-card.json")
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise TypeError("A2A Agent Card must be a JSON object")
            return dict(data)

    async def delegate(self, text: str, context_id: str) -> DelegatedArtifact:
        payload = {
            "jsonrpc": "2.0",
            "id": str(uuid4()),
            "method": "message/send",
            "params": {
                "message": {
                    "role": "user",
                    "messageId": str(uuid4()),
                    "contextId": context_id,
                    "parts": [{"kind": "text", "text": text}],
                }
            },
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(self.base_url, json=payload)
            response.raise_for_status()
            body = response.json()
        if "error" in body:
            raise RuntimeError(f"A2A peer rejected task: {body['error'].get('code', 'unknown')}")
        result = body.get("result", {})
        artifacts = result.get("artifacts", [])
        texts = [part.get("text", "") for item in artifacts for part in item.get("parts", [])]
        return DelegatedArtifact("\n".join(filter(None, texts)), self.base_url)
