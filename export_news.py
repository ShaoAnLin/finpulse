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
import sys
from datetime import datetime, timedelta

from config import DB_PATH
from db import init_db
from send_messages import TZ_TPE

DEFAULT_OUTPUT = "news_export.json"
HISTORY_DAYS = 7

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
    con = init_db(db_path)
    try:
        cur = con.execute(
            f"SELECT {', '.join(EXPORT_COLUMNS)} FROM pushed_news ORDER BY pushed_at DESC"
        )
        return [dict(zip(EXPORT_COLUMNS, row)) for row in cur.fetchall()]
    finally:
        con.close()


def export_recent_features(
    db_path: str = DB_PATH,
    now: datetime | None = None,
    days: int = HISTORY_DAYS,
) -> dict:
    """Return the latest AI feature per category for each of the last `days`
    Taipei calendar dates, ordered newest-first."""
    current = (now or datetime.now(TZ_TPE)).astimezone(TZ_TPE)
    start = current.date() - timedelta(days=days - 1)
    end = current.date()
    con = init_db(db_path)
    try:
        rows = con.execute(
            """
            SELECT url, title, pushed_at, category, source, feature_text
            FROM pushed_news
            WHERE substr(pushed_at, 1, 10) >= ?
              AND substr(pushed_at, 1, 10) <= ?
              AND trim(COALESCE(feature_text, '')) != ''
              AND category IN ('international', 'taiwan')
            """,
            (
                (start - timedelta(days=1)).isoformat(),
                (end + timedelta(days=1)).isoformat(),
            ),
        ).fetchall()
    finally:
        con.close()

    normalized_rows = []
    for row in rows:
        try:
            pushed_at = datetime.fromisoformat(row[2].replace("Z", "+00:00"))
        except (AttributeError, ValueError):
            continue
        if pushed_at.tzinfo is None:
            pushed_at = pushed_at.replace(tzinfo=TZ_TPE)
        pushed_at = pushed_at.astimezone(TZ_TPE)
        if start <= pushed_at.date() <= end:
            normalized_rows.append((pushed_at, row))
    normalized_rows.sort(key=lambda item: item[0], reverse=True)

    grouped: dict[str, dict[str, dict]] = {}
    for pushed_at, (url, title, _, category, source, feature_text) in normalized_rows:
        date = pushed_at.date().isoformat()
        grouped.setdefault(date, {}).setdefault(category, {
            "category": category,
            "title": title or "",
            "feature": feature_text,
            "source": source or "",
            "link": url or "",
        })

    category_order = ("international", "taiwan")
    return {
        "days": [
            {
                "date": date,
                "featured": [
                    grouped[date][category]
                    for category in category_order
                    if category in grouped[date]
                ],
            }
            for date in sorted(grouped, reverse=True)
        ]
    }


def write_recent_features(output_path: str, db_path: str = DB_PATH) -> int:
    payload = export_recent_features(db_path)
    with open(output_path, "w", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write("\n")
    return sum(len(day["featured"]) for day in payload["days"])


def main() -> int:
    output_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_OUTPUT
    articles = export_articles()

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"articles": articles}, f, ensure_ascii=False, indent=2)

    print(f"[export_news] wrote {len(articles)} article(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
