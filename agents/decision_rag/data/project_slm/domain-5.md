# Domain 5: Frontend UX & Dual-Speed Responsiveness (00_SLM_Wireframe.png, AC-06, AC-07)

## [UX-01] Dual-Speed Experience (<2s Dashboard vs. 10s–60s Deep Agent Chat)

As shown in 00_SLM_Wireframe.png, clicking KPI cards (Capex Budget ₹6,240 Cr, Schedule Adherence 68%) or switching BU filters on the dashboard must load in <2 seconds from an operational cache/Lakebase/Postgres layer, never waiting 30 seconds for an LLM agent or cold SQL Warehouse.

## [UX-02] Real-Time Streaming of Intermediate Reasoning & Citations (SSE)

During a 45-second complex root-cause query (AC-07), the Split Chat UI must smoothly stream each ADK sub-agent's intermediate thought badge and progressively populate the right-hand Evidence Panel (04_Split_Chat_Evidence_Panel.png) without proxy buffering.

## [UX-03] Zero 502/504 Gateway Timeouts on 60s–180s Deep Queries

Multi-source cross-BU synthesis queries taking 60–180 seconds must never be killed prematurely by ingress load balancers, Azure Front Door, ACA Envoy proxies (240s limit), or Databricks Apps reverse proxies.

## [UX-04] Interactive Mind-Map / Knowledge Graph Drill-Down (<1s Node Expansion)

In the Knowledge Graph view (07_Split_Chat_Knowledge_Graph.png), clicking Delay in Land Acquisition → Impact on Piling → Vendor Claim must expand graph nodes instantaneously from pre-indexed dependency edges while syncing context with the chat pane.

## [UX-05] Deep-Linking from Evidence Citations to Original Source Pages

When a user clicks a citation badge ([Drawing Rev-04, Page 12] or [SAP PO #4500192]) in the Evidence Panel, the UI must render a secure inline PDF page preview or source record drawer within 2 seconds using short-lived signed URLs.

## [UX-06] Resilient Mobile / Site-Office Reconnection

When a Site Head at a remote construction site (e.g., Khavda or Navi Mumbai site office) experiences a 5-second cellular network blip mid-query, the frontend must automatically reconnect to the active session_id and resume streaming the in-flight ADK answer instead of losing the turn.

## [UX-07] Custom Corporate Domain (slm.adani.com) & Seamless SSO

Executives opening https://slm.adani.com on desktop or mobile must land directly in the app via corporate Entra ID SSO without seeing a raw platform URL (*.databricksapps.com), double-login prompts, or platform workspace chrome.

## [UX-08] Side-by-Side Scenario Comparison Pinning

When evaluating two recovery options in chat (Option A: Air-freight GIS vs. Option B: Resequence Civil Work), users must be able to pin both agent outputs side-by-side in the UI and export the comparison to PDF/PPTX.

## [UX-09] Asynchronous "Notify Me When Ready" for Ultra-Deep Portfolio Audits

If a Group Executive triggers an exhaustive 23-BU portfolio audit or 50-page monthly board pack generation that takes 3+ minutes, they must be able to navigate away to the Dashboard and receive an in-app toast notification when the agent completes.
