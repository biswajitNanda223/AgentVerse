FROM python:3.13-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY --from=ghcr.io/astral-sh/uv:0.9.0 /uv /usr/local/bin/uv
WORKDIR /workspace
COPY pyproject.toml uv.lock README.md ./
COPY packages ./packages
COPY agents ./agents
RUN uv sync --frozen --no-dev --no-editable --package agentverse-event-worker

FROM python:3.13-slim AS runtime
ENV PATH="/workspace/.venv/bin:$PATH" PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app app
WORKDIR /workspace
COPY --from=builder --chown=app:app /workspace/.venv /workspace/.venv
USER 10001:10001
EXPOSE 8000
ENTRYPOINT ["uvicorn", "event_worker.app:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
