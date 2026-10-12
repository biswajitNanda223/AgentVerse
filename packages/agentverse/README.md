# agentverse (shared library)

Shared building blocks used by every agent in this monorepo: RAG pipeline and chunking,
ADK tools and guardrails, reliability controls, MCP/A2A protocol helpers, FastAPI app and
OpenTelemetry setup.

Reference agent for Agents CLI: `agentverse.agents.agent:root_agent`
(see `agents-cli-manifest.yaml`). Run tests from the repo root with `make test`.
