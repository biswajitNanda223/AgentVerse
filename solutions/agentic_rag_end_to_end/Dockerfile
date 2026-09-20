FROM python:3.13-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.9.0 /uv /usr/local/bin/uv
WORKDIR /workspace
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
COPY solutions ./solutions
RUN uv sync --frozen --no-dev --no-editable

FROM python:3.13-slim
ENV PATH="/workspace/.venv/bin:$PATH" PYTHONUNBUFFERED=1
RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app app
WORKDIR /workspace
COPY --from=builder --chown=app:app /workspace /workspace
USER 10001:10001
EXPOSE 8000
ENTRYPOINT ["uvicorn", "solutions.agentic_rag_end_to_end.app.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]

