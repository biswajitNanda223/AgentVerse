import pytest

from declarative_agent.sql_guard import check_sql

TABLES = ("p6_activity_dc", "ariba_po_status")


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT id, activity_name FROM p6_activity_dc WHERE project = 'Chennai DC-1' LIMIT 5",
        "SELECT COUNT(*) FROM ariba_po_status",
        "SELECT project, SUM(variance_days) FROM p6_activity_dc GROUP BY project",
        "WITH x AS (SELECT po_number FROM ariba_po_status) SELECT po_number FROM x LIMIT 3",
    ],
)
def test_allowed_queries(sql: str) -> None:
    assert check_sql(sql, TABLES).ok


@pytest.mark.parametrize(
    ("sql", "fragment"),
    [
        ("DROP TABLE p6_activity_dc", "read-only"),
        ("DELETE FROM ariba_po_status WHERE id = 1", "read-only"),
        ("UPDATE p6_activity_dc SET variance_days = 0", "read-only"),
        ("SELECT 1; DROP TABLE p6_activity_dc", "one statement"),
        ("SELECT * FROM p6_activity_dc LIMIT 5", "SELECT *"),
        ("SELECT activity_name FROM p6_activity_dc", "raw table scan"),
        ("SELECT activity_name FROM p6_activity_dc LIMIT 500", "no greater than 20"),
        ("SELECT po_number FROM other_bu_pos LIMIT 5", "not available"),
        (
            "SELECT a.id FROM p6_activity_dc a JOIN other_bu_pos b ON a.id = b.id LIMIT 5",
            "not available",
        ),
        (
            "WITH x AS (SELECT po_number FROM ariba_po_status LIMIT 3) SELECT po_number FROM x",
            "raw",
        ),
        ("SELEC oops FROM", "parsed"),
        ("", "one statement"),
    ],
)
def test_blocked_queries(sql: str, fragment: str) -> None:
    result = check_sql(sql, TABLES)
    assert not result.ok and fragment in result.reason


def test_masked_columns_are_blocked_by_name() -> None:
    sql = "SELECT po_number, unit_price FROM ariba_po_status LIMIT 5"
    assert check_sql(sql, TABLES).ok
    blocked = check_sql(sql, TABLES, masked_columns=("unit_price", "bid_margin"))
    assert not blocked.ok and "unit_price" in blocked.reason


def test_a_user_with_no_allowed_tables_can_query_nothing() -> None:
    assert not check_sql("SELECT activity_name FROM p6_activity_dc LIMIT 3", ()).ok
