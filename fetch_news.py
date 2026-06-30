#!/usr/bin/env python3
"""Fetch financial news from RSS feeds, deduplicate against SQLite state."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import sys
from datetime import datetime, timedelta, timezone

import feedparser
import requests

from config import DB_PATH, MAX_NEWS_INTERNATIONAL, MAX_NEWS_TAIWAN, RSS_FEEDS

TZ_TPE = timezone(timedelta(hours=8))


def init_db(db_path: str) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.execute("""
        CREATE TABLE IF NOT EXISTS pushed_news (
            url_hash TEXT PRIMARY KEY,
            url TEXT,
            title TEXT,
            pushed_at TEXT
        )
    """)
    con.commit()
    return con


def url_hash(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


def is_pushed(con: sqlite3.Connection, url: str) -> bool:
    row = con.execute("SELECT 1 FROM pushed_news WHERE url_hash=?", (url_hash(url),)).fetchone()
    return row is not None


def fetch_feed(feed_info: dict) -> list[dict]:
    """Fetch and parse a single RSS feed."""
    try:
        resp = requests.get(feed_info["url"], timeout=15, headers={"User-Agent": "FinPulse/1.0"})
        resp.raise_for_status()
        parsed = feedparser.parse(resp.text)
    except Exception as e:
        print(f"[warn] Failed to fetch {feed_info['name']}: {e}", file=sys.stderr)
        return []

    articles = []
    cutoff = datetime.now(TZ_TPE) - timedelta(hours=24)

    for entry in parsed.entries:
        published = None
        if hasattr(entry, "published_parsed") and entry.published_parsed:
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            published = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

        if published and published.astimezone(TZ_TPE) < cutoff:
            continue

        link = entry.get("link", "")
        title = entry.get("title", "").strip()
        snippet = entry.get("summary", entry.get("description", "")).strip()
        snippet = re.sub(r"<[^>]+>", "", snippet)[:300]

        if not title or not link:
            continue

        articles.append({
            "title": title,
            "link": link,
            "source": feed_info["name"],
            "published": published.isoformat() if published else None,
            "snippet": snippet,
        })

    return articles


def select_top_news(articles: list[dict], max_count: int, con: sqlite3.Connection) -> list[dict]:
    """Select top N news that haven't been pushed yet, sorted by recency."""
    unseen = [a for a in articles if not is_pushed(con, a["link"])]
    unseen.sort(key=lambda a: a.get("published") or "", reverse=True)
    return unseen[:max_count]


def main() -> int:
    con = init_db(DB_PATH)

    international_articles = []
    for feed in RSS_FEEDS["international"]:
        international_articles.extend(fetch_feed(feed))

    taiwan_articles = []
    for feed in RSS_FEEDS["taiwan"]:
        taiwan_articles.extend(fetch_feed(feed))

    selected_international = select_top_news(international_articles, MAX_NEWS_INTERNATIONAL, con)
    selected_taiwan = select_top_news(taiwan_articles, MAX_NEWS_TAIWAN, con)

    for item in selected_international:
        item["category"] = "international"
    for item in selected_taiwan:
        item["category"] = "taiwan"

    result = selected_international + selected_taiwan

    if not result:
        print(json.dumps({"articles": [], "summary": "no new articles found"}))
    else:
        print(json.dumps({"articles": result, "summary": f"{len(selected_international)} intl + {len(selected_taiwan)} tw"}, ensure_ascii=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
