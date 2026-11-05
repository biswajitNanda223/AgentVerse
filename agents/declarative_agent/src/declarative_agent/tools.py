"""The two tools that skills unlock. Neither can change an enterprise system."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from google.adk.tools.tool_context import ToolContext

from declarative_agent.demo_data import connect
from declarative_agent.sql_guard import ROW_CAP

SYSTEMS = ("SAP", "Primavera", "Clapia")


def run_governed_sql(sql: str, tool_context: ToolContext) -> dict[str, Any]:
    """Run a read-only SQL query on governed tables and return rows with citation ids.

    The query is checked by a guardrail before it runs. Returns at most 20 rows.
    """

    connection = connect()
    try:
        cursor = connection.execute(sql)
        fetched = cursor.fetchmany(ROW_CAP)
    finally:
        connection.close()
    columns = [d[0] for d in cursor.description or []]
    rows = [dict(zip(columns, tuple(row), strict=True)) for row in fetched]
    table = _first_table(sql)
    citations = [
        f"{table}:{row.get('po_number') or row.get('id')}"
        for row in rows
        if row.get("po_number") or row.get("id")
    ]
    result: dict[str, Any] = {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "citations": citations,
    }
    if rows and not citations:
        # Rows can only be cited by a key, so say so instead of returning uncitable evidence.
        result["citation_hint"] = "select the id (or po_number) column so each row can be cited"
    return result


def stage_write_back(
    system: str, record_id: str, field: str, new_value: str, tool_context: ToolContext
) -> dict[str, Any]:
    """Draft a change to a record in SAP, Primavera or Clapia for human approval.

    This never makes the change. It returns a draft id that is the same for identical details.
    """

    if system not in SYSTEMS:
        return {"error": f"system must be one of {', '.join(SYSTEMS)}", "executed": False}
    payload = {"system": system, "record_id": record_id, "field": field, "new_value": new_value}
    draft_id = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]
    drafts = dict(tool_context.state.get("write_back_drafts") or {})
    duplicate = draft_id in drafts
    drafts[draft_id] = payload
    tool_context.state["write_back_drafts"] = drafts
    return {
        "status": "awaiting_approval",
        "draft_id": draft_id,
        "duplicate": duplicate,
        "executed": False,
        "note": "An authorized human must approve this draft before anything changes.",
    }


def _first_table(sql: str) -> str:
    import sqlglot
    from sqlglot import exp

    tree = sqlglot.parse_one(sql, read="databricks")
    table = tree.find(exp.Table)
    return table.name if table is not None else "result"
