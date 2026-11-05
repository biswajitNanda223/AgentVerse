---
name: governed-sql
description: Use when the user asks for figures, dates or counts that live in governed tables such as p6_activity_dc or ariba_po_status. Unlocks the run_governed_sql tool and explains what a query must look like to be allowed.
license: Apache-2.0
metadata:
  adk_additional_tools:
    - run_governed_sql
---

# Governed SQL

You can only query through `run_governed_sql`. Every call is inspected by a deterministic
guardrail before it runs, so write queries that pass it the first time.

## A query is allowed only if it

1. is a single `SELECT` (no DDL or DML, no second statement);
2. names explicit columns (no `SELECT *`), including the `id` or `po_number` column so every row
   can be cited;
3. reads only the tables you are allowed to use in this session;
4. avoids masked columns for this user (the guardrail names them if you try);
5. is bounded: it has a `LIMIT` of at most 20 rows, or it aggregates (`GROUP BY`, `COUNT`, `SUM`).

## How to work

- Prefer aggregates and filters so the database does the heavy work and few rows come back.
- Ask for the smallest set of columns that answers the question.
- If the guardrail blocks a query, read the reason, fix that one thing, and try once more. Do not
  retry the same query, and do not try to rephrase a blocked request to get around the rule.
- Report results with the citations the tool returns. See `references/rules.md` for the full rules.
