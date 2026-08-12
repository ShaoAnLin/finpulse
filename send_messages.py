#!/usr/bin/env python3
"""Send FinPulse messages via the LINE Messaging API push endpoint."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

from config import DB_PATH, LINE_CHANNEL_ACCESS_TOKEN, LINE_TARGET
from db import init_db

# Windows defaults stdout to cp1252, which cannot encode the CJK/emoji payload.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

TZ_TPE = timezone(timedelta(hours=8))
LINE_MAX_LENGTH = 5000
LINE_PUSH_URL = "https://api.line.me/v2/bot/message/push"
NEWS_TODAY_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs", "news-today.json")


def send_message(message: str, silent: bool = False, dry_run: bool = False) -> bool:
    if dry_run:
        print(json.dumps({"dry_run": True, "message_length": len(message)}, ensure_ascii=False))
        return True

    headers = {
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    body = {
        "to": LINE_TARGET,
        "messages": [{"type": "text", "text": message}],
        "notificationDisabled": silent,
    }

    try:
        resp = requests.post(LINE_PUSH_URL, headers=headers, json=body, timeout=15)
    except requests.RequestException as e:
        print(f"[error] send failed: {e}", file=sys.stderr)
        return False

    if resp.status_code != 200:
        print(f"[error] LINE push failed ({resp.status_code}): {resp.text}", file=sys.stderr)
        return False

    return True


def split_message(text: str, max_len: int = LINE_MAX_LENGTH) -> list[str]:
    """Split long messages at line boundaries."""
    if len(text) <= max_len:
        return [text]

    chunks = []
    current = ""
    for line in text.split("\n"):
        if len(current) + len(line) + 1 > max_len:
            if current:
                chunks.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line
    if current:
        chunks.append(current)
    return chunks


def mark_pushed(articles: list[dict]) -> None:
    """Record delivered articles in SQLite to avoid duplicates. Also persists
    the full article details (category, source, snippet, published date, and
    the AI-written feature text) so this table can double as a historical
    archive exportable for the webpage, not just a dedup ledger."""
    con = init_db(DB_PATH)
    now = datetime.now(TZ_TPE).isoformat(timespec="seconds")
    for a in articles:
        url = a.get("link", "")
        title = a.get("title", "").encode("utf-8", errors="replace").decode("utf-8")
        h = hashlib.sha256(url.encode()).hexdigest()[:16]
        con.execute(
            """
            INSERT OR IGNORE INTO pushed_news
                (url_hash, url, title, pushed_at, category, source, snippet, published, feature_text)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                h,
                url,
                title,
                now,
                a.get("category", ""),
                a.get("source", ""),
                a.get("snippet", ""),
                a.get("published", ""),
                a.get("feature_text", ""),
            ),
        )
    con.commit()
    con.close()


def _dedup_news_items(items: list[dict]) -> list[dict]:
    deduped: list[dict] = []
    seen: set[str] = set()
    for item in items:
        key = (item.get("link") or "").strip() or (item.get("title") or "").strip()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def _merge_same_day_payload(existing: dict, new_payload: dict) -> dict:
    featured_by_category: dict[str, dict] = {}
    for article in existing.get("featured", []):
        category = (article.get("category") or "").strip()
        if category:
            featured_by_category[category] = article
    for article in new_payload.get("featured", []):
        category = (article.get("category") or "").strip()
        if category:
            featured_by_category[category] = article
    merged_featured = [
        featured_by_category[category]
        for category in ("international", "taiwan")
        if category in featured_by_category
    ]

    # Keep new rerun output first so dedup prefers the newest regenerated item
    # when link/title collisions happen with today's previous cache.
    raw_candidates = new_payload.get("candidates", []) + existing.get("candidates", [])
    merged_candidates = _dedup_news_items(raw_candidates)
    featured_links = {article.get("link", "") for article in merged_featured}
    merged_candidates = [
        article for article in merged_candidates
        if article.get("link", "") not in featured_links
    ][:10]

    return {
        "date": new_payload["date"],
        "featured": merged_featured,
        "candidates": merged_candidates,
    }


def write_news_today(featured: list[dict], candidates: list[dict],
                     path: str = NEWS_TODAY_PATH) -> None:
    """Write today's web cache, merging same-day reruns instead of replacing all."""
    today = datetime.now(TZ_TPE).strftime("%Y-%m-%d")
    payload = {
        "date": today,
        "featured": [
            {
                "category": article.get("category", ""),
                "title": article.get("title", ""),
                "feature": article.get("feature_text", ""),
                "source": article.get("source", ""),
                "link": article.get("link", ""),
            }
            for article in featured
        ],
        "candidates": [
            {
                "title": article.get("title", ""),
                "snippet": article.get("snippet", ""),
                "category": article.get("category", ""),
                "source": article.get("source", ""),
                "link": article.get("link", ""),
            }
            for article in candidates[:10]
        ],
    }

    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as source:
                existing_payload = json.load(source)
            if isinstance(existing_payload, dict) and existing_payload.get("date") == today:
                payload = _merge_same_day_payload(existing_payload, payload)
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            pass

    os.makedirs(os.path.dirname(path), exist_ok=True)
    temporary_path = f"{path}.tmp"
    with open(temporary_path, "w", encoding="utf-8") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write("\n")
    os.replace(temporary_path, path)


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[error] Invalid JSON input: {e}", file=sys.stderr)
        return 1

    messages = data.get("messages", [])
    articles = data.get("articles", [])
    candidates = data.get("candidates", [])
    dry_run = "--dry-run" in sys.argv

    if not dry_run and (not LINE_CHANNEL_ACCESS_TOKEN or not LINE_TARGET):
        print("[error] LINE_CHANNEL_ACCESS_TOKEN and FINPULSE_LINE_TARGET must be set", file=sys.stderr)
        return 1

    success = True
    for item in messages:
        text = item.get("message", "")
        silent = item.get("silent", False)
        for chunk in split_message(text):
            if not send_message(chunk, silent=silent, dry_run=dry_run):
                success = False

    if success and not dry_run:
        if articles:
            mark_pushed(articles)
        write_news_today(articles, candidates)

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
