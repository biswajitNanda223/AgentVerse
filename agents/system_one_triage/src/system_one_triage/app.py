from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from system_one_triage.client import SystemOneClient, build_client
from system_one_triage.settings import get_settings
from system_one_triage.triage import triage


class TicketIn(BaseModel):
    text: str = Field(min_length=1, max_length=8000)


def create_app(client: SystemOneClient | None = None) -> FastAPI:
    """POST /v1/triage -> routing decision. Ticket text is never logged or echoed on errors."""

    system_one = client or build_client(get_settings())
    app = FastAPI(title="System One triage")

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    @app.post("/v1/triage")
    async def post_triage(ticket: TicketIn) -> dict[str, Any]:
        return (await triage(ticket.text, system_one)).as_dict()

    return app
