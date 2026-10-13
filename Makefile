.PHONY: install lint typecheck test eval docs check api rag-api security-api mcp compose-up compose-down lock
install:
	uv sync --all-packages --all-extras
lock:
	uv lock
lint:
	uv run ruff check .
	uv run ruff format --check .
typecheck:
	uv run mypy
test:
	uv run pytest --cov=agentverse --cov=agentic_rag --cov=production_security --cov-report=term-missing
eval:
	uv run python agents/production_security/evals/run.py
docs:
	uv run python scripts/check_docs.py
check: lint typecheck eval docs test
api:
	uv run --package agentverse uvicorn agentverse.api.app:create_app --factory --reload
rag-api:
	uv run --package agentverse-agentic-rag uvicorn agentic_rag.api:create_app --factory --reload
security-api:
	uv run --package agentverse-production-security uvicorn production_security.api:app --reload
mcp:
	uv run --package agentverse python -m agentverse.protocols.mcp_server
compose-up:
	docker compose -f deploy/docker-compose.yml up --build
compose-down:
	docker compose -f deploy/docker-compose.yml down
