# Domain 6: Backend Orchestration, Controlled Write-Back & Proactive Workflows (AC-09, Use Cases 6, 7, 15)

## [BKD-01] Human-in-the-Loop Approval Gate Before Enterprise Write-Back (AC-09)

Under Use Case 15 (Controlled Enterprise Action & Write-Back), when a user asks the agent to update a milestone forecast or create an action item in SAP/Primavera/Clapia, the agent must never execute the write directly—it must stage a draft payload and pause until an authorized human clicks Approve.

## [BKD-02] Long-Lived Durable Agent Pause (Hours/Days) Across Approval Routing

If a Project Engineer proposes a schedule baseline change in chat that requires the BU Head's approval under Delegation of Authority (DoA), the paused workflow state must survive in durable storage for hours or days (including across container restarts) and resume once approved.

## [BKD-03] 100% Tamper-Proof Before/After Write-Back Audit Trail (AC-09)

Every approved write-back action must atomically record who requested, who approved, timestamp, source agent reasoning, exact old value, and exact new value in an immutable audit table.

## [BKD-04] Transactional Idempotency on External ERP/P6 APIs

If a user double-clicks "Approve Write-Back" or an SAP BTP API call times out and retries, idempotency keys must guarantee that duplicate Purchase Requisitions or duplicate NCR records are never created in source systems.

## [BKD-05] Event-Driven Proactive Threshold Alerts (Use Case 6)

Without waiting for a user to open chat, when a fresh Delta Share sync reveals that a critical-path milestone slipped by >7 days or a safety NCR was logged in T-Pulse/Safex, a background worker must invoke the ADK agent to draft an impact brief and push a notification to the Project Head.

## [BKD-06] Automated Monday 8:00 AM PMO Governance Pack Generation (Use Case 7)

A scheduled cron workflow must run the ADK synthesis pipeline headless across all active projects every Monday morning to pre-generate standardized Weekly Progress Reports (PDF/Word) and executive morning digests.

## [BKD-07] Read/Write Workload Separation (Transactional OLTP vs. Analytical OLAP)

High-frequency application writes (saving chat messages, user bookmarks, alert acknowledgments, write-back state machines) must execute in <10ms against an OLTP database (Lakebase / Cloud SQL / Azure Postgres) rather than queuing behind analytical Delta Lake queries.

## [BKD-08] Outbound Enterprise Connector Hub (SAP BTP, Primavera P6, Teams/Email)

The backend runtime must securely reach on-premises / private-cloud SAP BTP, Oracle Primavera P6 APIs, and Microsoft Graph (Teams/Outlook notifications) via private hybrid connectivity.
