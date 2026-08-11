#!/usr/bin/env python3
"""Shared SQLite schema helpers for the FinPulse pushed_news state table.

`pushed_news` doubles as both the dedup ledger (prevents re-sending an
article) and the historical archive used to export data for the webpage.
"""
from __future__ import annotations

import sqlite3

# Columns beyond the original (url_hash, url, title, pushed_at) dedup ledger.
# Kept as ALTER TABLE ADD COLUMN migrations so existing databases upgrade
# in place without losing previously recorded rows.
EXTRA_COLUMNS: list[tuple[str, str]] = [
    ("category", "TEXT"),
    ("source", "TEXT"),
    ("snippet", "TEXT"),
    ("published", "TEXT"),
    ("feature_text", "TEXT"),
]


def ensure_schema(con: sqlite3.Connection) -> None:
    """Create the pushed_news table if missing, and migrate older databases
    that only have the original 4 dedup columns by adding the newer article
    detail columns needed to export historical data for the webpage."""
    con.execute("""
        CREATE TABLE IF NOT EXISTS pushed_news (
            url_hash TEXT PRIMARY KEY,
            url TEXT,
            title TEXT,
            pushed_at TEXT
        )
    """)

    existing = {row[1] for row in con.execute("PRAGMA table_info(pushed_news)")}
    for name, col_type in EXTRA_COLUMNS:
        if name not in existing:
            con.execute(f"ALTER TABLE pushed_news ADD COLUMN {name} {col_type}")

    con.commit()


def init_db(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    ensure_schema(con)
    return con
