import json

import httpx
import pytest
from pydantic import SecretStr

from system_one_triage.errors import SystemOneError, WireFormatError
from system_one_triage.http_client import JevHttpClient
from system_one_triage.questions import Noul

QUESTIONS = {"is_urgent": Noul("The customer needs an answer today.")}


def client(handler: httpx.MockTransport) -> JevHttpClient:
    return JevHttpClient(SecretStr("sk-test"), transport=handler)


async def test_sends_bearer_auth_and_the_documented_body() -> None:
    seen: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["auth"] = request.headers["authorization"]
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json={"is_urgent": {"noul": 0.97}})

    answers = await client(httpx.MockTransport(handler)).evaluate("server is down", QUESTIONS)
    assert seen["url"] == "https://api.typesafe.ai/v1/systemone"
    assert seen["auth"] == "Bearer sk-test"
    assert seen["body"]["model"] == "jev-latest"  # type: ignore[index]
    assert seen["body"]["state"] == "server is down"  # type: ignore[index]
    assert answers["is_urgent"].noul == 0.97  # type: ignore[union-attr]


async def test_http_errors_do_not_leak_the_state_or_response_body() -> None:
    state_with_card = "my card is 4242 4242 4242 4242"

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, text=f"echo: {state_with_card}")

    with pytest.raises(SystemOneError) as info:
        await client(httpx.MockTransport(handler)).evaluate(state_with_card, QUESTIONS)
    assert "4242" not in str(info.value)
    assert "500" in str(info.value)


async def test_timeouts_become_system_one_errors() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(SystemOneError, match="ReadTimeout"):
        await client(httpx.MockTransport(handler)).evaluate("x", QUESTIONS)


async def test_non_json_and_misshapen_bodies_fail_closed() -> None:
    bad_json = httpx.MockTransport(lambda r: httpx.Response(200, text="<html>"))
    with pytest.raises(WireFormatError):
        await client(bad_json).evaluate("x", QUESTIONS)
    wrong = httpx.MockTransport(lambda r: httpx.Response(200, json={"other": {}}))
    with pytest.raises(WireFormatError):
        await client(wrong).evaluate("x", QUESTIONS)
