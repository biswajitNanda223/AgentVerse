"""Tiny SYNTHETIC tables so the example runs offline. Not real project data."""

import sqlite3

ALL_TABLES = ("p6_activity_dc", "ariba_po_status")
SCHEMA = """
CREATE TABLE p6_activity_dc (
  id INTEGER PRIMARY KEY, activity_name TEXT, project TEXT,
  planned_finish TEXT, forecast_finish TEXT, variance_days INTEGER);
CREATE TABLE ariba_po_status (
  id INTEGER PRIMARY KEY, po_number TEXT, vendor_name TEXT, project TEXT,
  milestone TEXT, delivery_date TEXT, unit_price REAL, bid_margin REAL);
INSERT INTO p6_activity_dc VALUES
  (1, 'Foundation piling', 'Chennai DC-1', '2026-03-01', '2026-03-09', 8),
  (2, 'Structural steel', 'Chennai DC-1', '2026-04-15', '2026-04-15', 0),
  (3, 'GIS transformer delivery', 'Mumbai DC-1', '2026-05-20', '2026-06-04', 15);
INSERT INTO ariba_po_status VALUES
  (1, '4500192', 'Vendor A', 'Chennai DC-1', 'Delivery', '2026-03-30', 120.5, 0.12),
  (2, '4500193', 'Vendor B', 'Mumbai DC-1', 'Delivery', '2026-05-30', 98.0, 0.09);
"""


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(":memory:")
    connection.executescript(SCHEMA)
    connection.row_factory = sqlite3.Row
    return connection
