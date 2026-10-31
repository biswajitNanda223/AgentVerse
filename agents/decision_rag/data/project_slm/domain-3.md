# Domain 3: Multi-BU Delta Sharing, Governance & Hiding Raw Data (AC-10, SC-08)

## [GOV-01] Blocking Raw Row Dumps While Serving Verifiable Evidence

When a user asks "Give me all rows of the SAP PO line-item table" or tries prompt-injection, the system must refuse to expose raw underlying table dumps while still serving curated, record-level citations (PO #, Vendor Name, Milestone Variance) in the Split-Screen Evidence Panel (04_Split_Chat_Evidence_Panel.png).

## [GOV-02] Enforcing Per-User BU & Project Isolation Over Delta Shares (AC-10)

Because Delta Sharing shares a BU's table with the central SLM workspace as a whole, the architecture must enforce per-user BU, Project (Chennai DC-1 vs. Mumbai DC-1), and Function (Commercial vs. Safety) filtering so a user can never query another BU's shared data.

## [GOV-03] Preserving Corporate Entra ID Claims Across the Backend → Agent → SQL Hop

Custom corporate Entra ID attributes (BU_Code, Assigned_Projects, DoA_Level, Department) must survive from user login all the way into the ADK Agent and Unity Catalog SQL session without being stripped by platform reverse proxies (a known limitation on Databricks Apps OBO).

## [GOV-04] Cross-BU Executive Rollup vs. Single-Site Restriction

When a Group Executive asks "Compare schedule adherence across Data Centre, Thermal, and Airports BUs", the system must seamlessly aggregate across 3 Delta Shares, whereas the exact same prompt from a Site Engineer must automatically scope only to their assigned site.

## [GOV-05] Column-Level Masking of Commercial & Margin Data

A Site Planning Engineer and a Chief Commercial Officer must be able to query the exact same Procurement Semantic Object (ariba_po_status), with the Engineer seeing technical delivery dates while unit prices and vendor bid margins are dynamically masked (NULL or REDACTED).

## [GOV-06] Graceful Degradation When One BU's Delta Share Is Stale or Broken

If the Thermal BU's Primavera P6 pipeline (DP-10) fails or changes schema overnight, a Group Executive's cross-BU query must still return accurate metrics for Data Centre and Airports while displaying a clear banner: "Thermal BU P6 data is 18 hours stale — excluded from rollup."

## [GOV-07] Cross-Cloud / Cross-Region Egress Control on Delta Shares

If BU Data Lakes reside on Azure Databricks (centralindia / southindia) while the ADK Agent runtime sits on GCP (GKE / Vertex AI), the architecture must push heavy joins and aggregations down into Databricks SQL so gigabytes of raw Delta rows never traverse cross-cloud internet links.

## [GOV-08] Unstructured Document Entitlement Parity (DP-01 ACC, DP-09 SharePoint)

A user who is blocked from seeing Mumbai DC-1 rows in structured SQL tables must also be strictly blocked from retrieving vector chunks of Mumbai DC-1's contracts, drawings, and NCR PDFs in Vector Search.

## [GOV-09] Zero-Copy Governance Without Duplicating 23 BU Warehouses

Adding a new BU via Delta Sharing must apply centralized Unity Catalog Row Filters and Semantic Views over the shared tables without copying terabytes of raw BU data into 23 separate physical databases.
