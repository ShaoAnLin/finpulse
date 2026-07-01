#!/usr/bin/env bash
# FinPulse daily digest: fetch RSS -> AI summary -> push to LINE
set -u -o pipefail
export PYTHONUTF8=1

BASE_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$BASE_DIR"

PYTHON_BIN="${FINPULSE_PYTHON:-python3}"

LOG_DIR="$BASE_DIR/logs"
mkdir -p "$LOG_DIR"
stamp="$(date -u +%Y%m%dT%H%M%SZ)"

echo "[finpulse] start $(date -Is)"

# 1. Fetch news from RSS
echo "[finpulse] fetching news..."
"$PYTHON_BIN" fetch_news.py > "/tmp/finpulse-fetched-$stamp.json" 2>>"$LOG_DIR/fetch.log"
fetch_status=$?

if [ "$fetch_status" -ne 0 ]; then
    echo "[finpulse] fetch failed with status $fetch_status" >&2
    exit "$fetch_status"
fi

# 2. Summarize with AI (GitHub Models API)
echo "[finpulse] summarizing with AI..."
"$PYTHON_BIN" summarize_news.py < "/tmp/finpulse-fetched-$stamp.json" > "/tmp/finpulse-messages-$stamp.json" 2>>"$LOG_DIR/summarize.log"
summarize_status=$?

if [ "$summarize_status" -ne 0 ]; then
    echo "[finpulse] summarize failed with status $summarize_status" >&2
    exit "$summarize_status"
fi

# 3. Send via LINE
echo "[finpulse] sending to LINE..."
"$PYTHON_BIN" send_messages.py < "/tmp/finpulse-messages-$stamp.json" 2>>"$LOG_DIR/send.log"
send_status=$?

# Cleanup temp files older than 7 days
find /tmp -maxdepth 1 -name 'finpulse-*.json' -mtime +7 -delete 2>/dev/null || true

if [ "$send_status" -ne 0 ]; then
    echo "[finpulse] send failed with status $send_status" >&2
    exit "$send_status"
fi

echo "[finpulse] done"
