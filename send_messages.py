#!/usr/bin/env python3
"""Send FinPulse messages via OpenClaw Telegram integration."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone

from config import DB_PATH, TELEGRAM_ACCOUNT, TELEGRAM_CHANNEL, TELEGRAM_TARGET

TZ_TPE = timezone(timedelta(hours=8))
TELEGRAM_MAX_LENGTH = 4096


def send_message(message: str, silent: bool = False, dry_run: bool = False) -> bool:
    cmd = [
        "openclaw", "message", "send",
        "--json",
        "--channel", TELEGRAM_CHANNEL,
        "--account", TELEGRAM_ACCOUNT,
        "--target", TELEGRAM_TARGET,
        "--message", message,
    ]
    if silent:
        cmd.append("--silent")

    if dry_run:
        print(json.dumps({"dry_run": True, "message_length": len(message)}, ensure_ascii=False))
        return True

    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"[error] send failed: {e.stderr}", file=sys.stderr)
        return False


def split_message(text: str, max_len: int = TELEGRAM_MAX_LENGTH) -> list[str]:
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
    """Record delivered articles in SQLite to avoid duplicates."""
    con = sqlite3.connect(DB_PATH)
    con.execute("""
        CREATE TABLE IF NOT EXISTS pushed_news (
            url_hash TEXT PRIMARY KEY,
            url TEXT,
            title TEXT,
            pushed_at TEXT
        )
    """)
    now = datetime.now(TZ_TPE).isoformat(timespec="seconds")
    for a in articles:
        url = a.get("link", "")
        h = hashlib.sha256(url.encode()).hexdigest()[:16]
        con.execute(
            "INSERT OR IGNORE INTO pushed_news (url_hash, url, title, pushed_at) VALUES (?, ?, ?, ?)",
            (h, url, a.get("title", ""), now),
        )
    con.commit()
    con.close()


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[error] Invalid JSON input: {e}", file=sys.stderr)
        return 1

    messages = data.get("messages", [])
    articles = data.get("articles", [])
    dry_run = "--dry-run" in sys.argv

    if not TELEGRAM_TARGET:
        print("[error] FINPULSE_TELEGRAM_TARGET not set", file=sys.stderr)
        return 1

    success = True
    for item in messages:
        text = item.get("message", "")
        silent = item.get("silent", False)
        for chunk in split_message(text):
            if not send_message(chunk, silent=silent, dry_run=dry_run):
                success = False

    if success and articles and not dry_run:
        mark_pushed(articles)

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
