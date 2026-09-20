# Chunking examples

| Directory | Strategies |
|---|---|
| `01_fixed` | fixed token-like word window with overlap |
| `02_sentence_paragraph` | sentence groups and paragraph boundaries |
| `03_recursive` | heading/paragraph/sentence fallback hierarchy |
| `04_semantic` | similarity-breakpoint grouping |
| `05_document_aware` | Markdown section boundaries |
| `06_parent_child` | large context parents with small searchable children |
| `07_contextual_late` | ingestion context prefix and whole-document late context |
| `08_code` | Python AST top-level definitions |
| `09_table` | repeated header plus bounded CSV row groups |
| `10_html_layout_proposition` | semantic HTML blocks, PDF/OCR layout elements, atomic facts |

Chunk size and overlap are starting hypotheses. Use a labeled retrieval set to select them by
document type; do not standardize one size across source code, contracts, tables and OCR pages.

