# Domain 7: Scalability & 100-User Burst Performance (AC-11, SC-09)

## [SCL-01] The Monday 9:30 AM 100-User Governance Burst (2,500+ LLM Calls)

When 100 project leaders across 23 BUs simultaneously run complex queries during Monday morning review meetings—generating 1,000 to 4,500 LLM calls and 200+ SQL queries within a 60-second window—the platform must keep simple queries ≤10s (AC-06) and complex queries ≤60s (AC-07).

## [SCL-02] Independent Horizontal Autoscaling of Frontend, Backend, and ADK Agent Tiers

Because ADK Agent pods are memory- and I/O-heavy (holding large semantic graphs and 45-step LLM contexts) while Frontend/Backend pods are lightweight, the platform must scale the ADK Agent tier independently to 10–30 replicas without hitting hard platform ceilings (such as Databricks Apps' 4 vCPU / 16 GB RAM and 5-replica cap).

## [SCL-03] Zero-Amnesia Pod Scaling & Load Balancing

When horizontal autoscaling spins up 8 new ADK agent pods mid-morning, Turn 2 of an active user's conversation must seamlessly execute on any pod by hydrating state from shared DatabaseSessionService / VertexAiSessionService without losing Turn 1 context.

## [SCL-04] Database Connection Pool Protection (PgBouncer / Lakebase Limits)

When 20 autoscaled ADK agent pods each run 20 async coroutines writing session state and telemetry, connection pooling must prevent too many clients already crashes on the underlying PostgreSQL / Lakebase instance.

## [SCL-05] Databricks SQL Warehouse Multi-Cluster Scaling & Result Caching

When 100 users ask overlapping portfolio questions, the underlying Databricks Serverless SQL Warehouse must auto-scale clusters instantly and serve identical semantic metric queries from result cache in <500ms.

## [SCL-06] Provisioned LLM Throughput & Priority Token Queuing

Under peak 100-user load (160M tokens/month), interactive executive chat turns must take priority over background batch tasks (like proactive alert scanning or document indexing) so background jobs never trigger 429 Too Many Requests errors for live users.

## [SCL-07] Pre-Warmed Replicas to Eliminate Cold-Start Penalties

At 8:55 AM before business hours begin, the hosting platform must maintain minimum warm instances (min-replicas >= 2) so the first executives logging in do not suffer a 25-second container or model-endpoint cold start.

## [SCL-08] Non-Blocking Async I/O Across All Tool Calls

Inside the ADK agent runtime, every LLM call, Databricks SQL execution, and Vector Search lookup must run asynchronously (async/await or thread-pool offloaded) so a single slow 20-second SQL query never blocks 15 other users sharing that container replica.
