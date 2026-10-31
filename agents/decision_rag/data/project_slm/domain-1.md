# Domain 1: Google ADK Native Capabilities & GenAI Orchestration

## [ADK-01] Sub-Agent Hand-Off Visibility

When a complex query passes through 6 ADK sub-agents (Supervisor → Orchestrator → Dispatcher → Selector → Planner → Synthesizer), the user must see live step-by-step progress ("Checking Primavera P6 schedule...", "Cross-checking SAP POs...") rather than staring at a frozen spinner for 45 seconds.

## [ADK-02] Runaway Agent Loop Protection (max_llm_calls=45)

When ambiguous project data causes Object_Selector and Query_Planner to loop repeatedly, the runtime must enforce hard token/iteration circuit breakers (before_model_callback) and return a partial grounded synthesis rather than timing out or burning $5 in tokens on a single question.

## [ADK-03] User Mid-Flight Cancellation ("Stop Generating")

When an executive realizes they typed "Mumbai DC-1" instead of "Chennai DC-1" and clicks Stop 8 seconds into a 60-second query, the backend must immediately terminate the active ADK Runner task and cancel downstream LLM/SQL calls to prevent wasted compute and session state corruption.

## [ADK-04] Cross-Session Executive Memory (MemoryService)

When a BU Head logs in on Wednesday after discussing "Package 4 GIS transformer delays" on Monday, the agent must recall their role, active project focus, and prior action items without forcing them to re-explain context from scratch.

## [ADK-05] Versioned Session Artifacts (ArtifactService)

When a Planner runs three "What-If" schedule recovery simulations in a single chat session (v1, v2, v3), the platform must store and retrieve each generated comparison table or chart as a versioned artifact without overwriting earlier iterations.

## [ADK-06] Multi-Model Routing & Automatic Failover

When the primary reasoning model (e.g., Gemini 2.5 Pro / Claude / GPT-4o) hits a regional quota spike or latency degradation during a Monday morning review, the ADK model layer must seamlessly fail over to a secondary region or fallback model without dropping the user's chat turn.

## [ADK-07] Deterministic Guardrail Callbacks (before_tool_callback)

Before any LLM-generated SQL query executes against Databricks, an ADK before_tool_callback must deterministically inspect the AST to block raw table scans, unauthorized cross-BU joins, or DDL/DML statements.

## [ADK-08] Golden Trajectory Regression Testing (adk eval)

Whenever a developer modifies a prompt in build_v42_agents.py or updates a semantic YAML file, CI/CD must automatically verify that the ADK agent still selects the exact right sequence of semantic objects and tools (≥95% grounded accuracy, AC-03) before deploying to production.

## [ADK-09] Future Cross-BU Agent Federation (A2A Protocol)

When Adani's central Finance or Procurement team deploys their own standalone AI agent next year, Project SLM's ADK Orchestrator must be able to invoke that external agent via standardized Agent-to-Agent (A2A) protocol without rewriting the core platform.

## [ADK-10] Hot-Reloading Prompts & Semantic YAMLs

When a domain SME fixes a KPI formula description or business glossary synonym in the Semantic Engine YAML (prism_semantic_layer), the change should take effect within minutes without requiring a full 20-minute container rebuild and cluster redeployment.
