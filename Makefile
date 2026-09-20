.PHONY: install lint test api mcp compose-up compose-down
install:
	uv sync --extra dev --extra rag --extra ocr
lint:
	uv run ruff check .
	uv run ruff format --check .
test:
	uv run pytest --cov=agentverse --cov-report=term-missing
api:
	uv run uvicorn agentverse.api.app:create_app --factory --reload
mcp:
	uv run python -m agentverse.protocols.mcp_server
compose-up:
	docker compose -f deploy/docker-compose.yml up --build
compose-down:
	docker compose -f deploy/docker-compose.yml down

