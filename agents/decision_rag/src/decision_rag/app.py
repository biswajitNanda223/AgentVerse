from typing import Any

from fastapi import FastAPI
from pydantic import BaseModel, Field

from decision_rag.factory import build_pipeline
from decision_rag.pipeline import DecisionRagPipeline
from decision_rag.settings import get_settings


class AskIn(BaseModel):
    query: str = Field(min_length=1, max_length=2000)
    trace: bool = False


def create_app(pipeline: DecisionRagPipeline | None = None) -> FastAPI:
    """POST /v1/ask navigates the corpus. Queries are never logged or echoed in errors."""

    rag = pipeline or build_pipeline(get_settings())
    app = FastAPI(title="DecisionRAG")

    @app.get("/health/live")
    async def live() -> dict[str, str]:
        return {"status": "alive"}

    @app.post("/v1/ask")
    async def ask(body: AskIn) -> dict[str, Any]:
        answer = await rag.answer(body.query)
        nav = answer.navigation
        payload: dict[str, Any] = {
            "answer": answer.text,
            "abstained": answer.abstained,
            "reason": answer.reason,
            "citations": [
                {"path": c.path, "passage_id": c.passage_id, "probability": c.probability}
                for c in answer.citations
            ],
            "model_calls": nav.model_calls if nav else 0,
        }
        if body.trace and nav:
            payload["steps"] = [
                {
                    "step": s.step,
                    "model_calls": s.model_calls,
                    "candidates": [
                        {"title": c.title, "kind": c.kind, "p": c.probability, "kept": c.kept}
                        for c in s.candidates
                    ],
                }
                for s in nav.steps
            ]
        return payload

    return app
