# Domain 2: Agent Telemetry, Observability & FinOps (AC-12)

## [TEL-01] End-to-End Trace Correlation (UI → ADK → SQL)

When a CFO reports that a ₹120 Cr capex variance number looks wrong, an engineer must be able to paste a single conversation_id and see the exact React request, all 15 ADK sub-agent spans, the exact compiled SQL sent to Databricks, and the SQL Warehouse query profile in one unified trace view within 5 minutes.

## [TEL-02] Per-BU & Per-Project Token Chargeback (160M Tokens/Mo)

At group scale across 23 BUs, Finance must receive an automated monthly breakdown of LLM token consumption, Vector Search queries, and Databricks SQL DBU spend attributed accurately to each BU, Project, and User Role.

## [TEL-03] Sub-Agent Bottleneck Pinpointing

When complex query latency creeps above the 60s P95 SLA (AC-07), operations teams must immediately see whether the slowdown is happening inside Object_Selector LLM reasoning, Databricks SQL execution, or cold-start queuing.

## [TEL-04] Automated Hallucination & Citation Drift Alerts (AC-02, AC-04)

Every production response must be asynchronously scored (or sampled) by an automated LLM-as-a-Judge pipeline to verify that every number in the final synthesis actually appeared in the Evidence_Builder tool output, alerting ops if unsupported claims exceed 5%.

## [TEL-05] Sensitive Data Redaction in Telemetry Spans

When an authorized executive queries sensitive L1 commercial bid values or employee safety incident details, those raw values must be masked or access-controlled inside OpenTelemetry / MLflow trace logs so DevOps engineers viewing traces cannot read confidential commercial data.

## [TEL-06] Negative Feedback & "Thumbs Down" Replay

When a Project Manager clicks "Thumbs Down" on an answer, the platform must capture the full ADK session state, semantic YAML version, and tool outputs into an evaluation dataset so engineers can replay and fix the exact failure.

## [TEL-07] Real-Time Quota & Cost Anomaly Circuit Breaker

If a compromised account or buggy client script triggers 5,000 rapid chat queries from a single user, telemetry must trigger an automatic per-user rate limit before exhausting the BU's monthly token budget.

## [TEL-08] Tool Error Rate & SQL Compilation Failure Dashboards

When a source pipeline change causes Query_Planner's generated SQL to fail syntax or schema validation, operations must receive an immediate alert showing which semantic object (e.g., p6_activity_dc) is failing before users complain.
