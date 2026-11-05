"""Deterministic SQL guardrail: inspects the parsed query, never trusts the model.

The query is parsed into an AST with sqlglot and checked by rules, not by asking an LLM.
Anything that does not parse, or is not clearly allowed, is blocked (fail closed). This is
defence in depth: the database must still enforce row filters and column masks itself.
"""

from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass

import sqlglot
from sqlglot import exp
from sqlglot.errors import SqlglotError

ROW_CAP = 20
FORBIDDEN = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Drop,
    exp.Create,
    exp.Alter,
    exp.Merge,
    exp.Command,
    exp.TruncateTable,
)


@dataclass(frozen=True)
class GuardResult:
    ok: bool
    reason: str = ""


def _block(reason: str) -> GuardResult:
    return GuardResult(False, reason)


def check_sql(
    sql: str,
    allowed_tables: Collection[str],
    masked_columns: Collection[str] = (),
    row_cap: int = ROW_CAP,
) -> GuardResult:
    try:
        statements = [s for s in sqlglot.parse(sql, read="databricks") if s is not None]
    except SqlglotError:
        return _block("the query could not be parsed")
    if len(statements) != 1:
        return _block("only one statement is allowed")
    root = statements[0]
    if any(root.find(kind) for kind in FORBIDDEN) or not isinstance(root, exp.Select):
        return _block("only a read-only SELECT is allowed (no DDL, DML or commands)")

    if root.find(exp.Star) is not None and root.find(exp.Count) is None:
        return _block("SELECT * is not allowed; name the columns you need")

    cte_names = {cte.alias_or_name.lower() for cte in root.find_all(exp.CTE)}
    tables = {t.name.lower() for t in root.find_all(exp.Table) if t.name.lower() not in cte_names}
    allowed = {t.lower() for t in allowed_tables}
    outside = sorted(tables - allowed)
    if not tables:
        return _block("the query reads no table")
    if outside:
        return _block(f"table(s) not available to this user: {', '.join(outside)}")

    columns = {c.name.lower() for c in root.find_all(exp.Column)}
    hidden = sorted(columns & {c.lower() for c in masked_columns})
    if hidden:
        return _block(f"column(s) are masked for this user: {', '.join(hidden)}")

    aggregates = root.find(exp.AggFunc) is not None or root.args.get("group") is not None
    limit = root.args.get("limit")
    if limit is not None:
        value = limit.expression
        try:
            rows = int(value.name) if isinstance(value, exp.Literal) else None
        except ValueError:
            rows = None
        if rows is None or rows > row_cap:
            return _block(f"LIMIT must be a number no greater than {row_cap}")
    elif not aggregates:
        return _block(f"an unbounded query is a raw table scan; add LIMIT {row_cap} or aggregate")
    return GuardResult(True)
