#!/usr/bin/env python3
"""Export historical FinPulse articles from state.sqlite3 to JSON for the webpage.

Usage:
    python export_news.py [output_path]

Defaults to writing news_export.json in the current directory. Each record
contains the full article detail captured at push time: title, url, category,
source, snippet, published date, the AI-written feature text, and the
timestamp it was pushed to LINE.
"""
from __future__ import annotations

import json
import sqlite3
import sys

from config import DB_PATH
from db import ensure_schema

DEFAULT_OUTPUT = "news_export.json"

EXPORT_COLUMNS = [
    "url_hash",
    "url",
    "title",
    "pushed_at",
    "category",
    "source",
    "snippet",
    "published",
    "feature_text",
]


def export_articles(db_path: str = DB_PATH) -> list[dict]:
    """Read all rows from pushed_news and return them as a list of dicts,
    ordered newest-first by pushed_at."""
    con = sqlite3.connect(db_path)
    try:
        ensure_schema(con)
        cur = con.execute(
            f"SELECT {', '.join(EXPORT_COLUMNS)} FROM pushed_news ORDER BY pushed_at DESC"
        )
        return [dict(zip(EXPORT_COLUMNS, row)) for row in cur.fetchall()]
    finally:
        con.close()


def main() -> int:
    output_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT
    articles = export_articles()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"articles": articles}, f, ensure_ascii=False, indent=2)

    print(f"[export_news] wrote {len(articles)} article(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
