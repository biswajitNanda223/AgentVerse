# Domain 4: Runtime User File Uploads, Vectorization & Multimodal RAG (Use Cases 3, 14, 16)

## [VEC-01] Uploading Large Engineering Documents (>10 MB to 100 MB)

When a Contracts Manager uploads a 35 MB multi-annexure EPC Contract PDF or large BOQ Excel workbook in chat, the platform must not reject the upload with a 413 Payload Too Large error (whereas Databricks Apps imposes a hard 10 MB proxy limit).

## [VEC-02] Sub-5-Second Runtime Vectorization (Bypassing Batch Index Lag)

When a user attaches a document and immediately asks a question in the same chat turn, the file must be parsed, chunked, embedded, and searchable in <5 seconds without waiting 5–15 minutes for a batch Databricks DELTA_SYNC vector index pipeline.

## [VEC-03] Strict Session Isolation of "What-If" Uploaded Files

When a Planner uploads a speculative "Draft Recovery Schedule v3.xlsx" to simulate milestone shifts (Use Case 3), those vector chunks must be strictly isolated to (user_id, session_id) so the BU Head's concurrent chat never mistakes the draft upload for official project data.

## [VEC-04] Cross-Referencing Uploaded Files Against Live Delta-Shared SQL Data

When a user uploads a vendor's delay-claim letter PDF and asks "Are the rain-delay dates claimed in this letter supported by our daily Safex site logs (DP-12) and P6 schedule (DP-10)?", the ADK agent must jointly query the ephemeral runtime vectors and live Unity Catalog SQL tables in a single turn.

## [VEC-05] Complex Table & Engineering Drawing Extraction (OCR / Vision)

Uploaded project files contain multi-page nested BOQ tables, scanned stamp signatures, and drawing revision blocks (DP-01 ACC); runtime parsing must preserve table row/column structure rather than mangling numbers with naive plain-text splitting.

## [VEC-06] Controlled Promotion of Verified Uploads to Permanent BU Knowledge Base

When a Project Director reviews a runtime-uploaded Mom/Claim analysis and clicks "Publish to Project Repository", the system must move the document from ephemeral session storage into governed Unity Catalog Volumes and trigger permanent BU-level indexing with full audit metadata.

## [VEC-07] Automatic Ephemeral Cleanup & TTL Governance

Abandoned runtime file uploads and temporary session vectors must automatically expire and purge after a configurable policy window (e.g., 24–72 hours) so unverified shadow documents do not accumulate forever.

## [VEC-08] CPU/Memory Isolation for Heavy Document Parsing

If 10 users simultaneously upload 40-page PDFs for runtime OCR and chunking, the CPU/memory spike must be isolated in dedicated worker pods or serverless functions so it does not starve the main FastAPI/ADK event loop serving 90 other chat users.
