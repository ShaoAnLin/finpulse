# FinPulse

Daily financial news digest delivered to LINE with beginner-friendly explanations in Traditional Chinese.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    FinPulse Pipeline                     │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  RSS Feeds ──► fetch_news.py ──► summarize_news.py      │
│  (Free)        (feedparser)      (GitHub Models API)    │
│                     │                    │              │
│                     ▼                    ▼              │
│              state.sqlite3        send_messages.py      │
│              (dedup store)        (LINE Push API)       │
│                                         │              │
│                                         ▼              │
│                                    LINE Bot ──► User   │
└─────────────────────────────────────────────────────────┘
```

## Tools & Services Used

| Component | Tool / Service | Cost |
|-----------|---------------|------|
| News source | Google News RSS, CnYes RSS, UDN Money RSS | Free |
| AI summarization | GitHub Models API (GPT-4o) | Free (150 req/day) |
| Message delivery | LINE Messaging API (Push) | Free (200 msg/month) |
| Deduplication | SQLite (local file) | Free |
| Scheduling | cron / Task Scheduler / OpenClaw | Free |
| Hosting | Azure DevBox (or any always-on machine) | Existing |

## Project Structure

```
finpulse/
├── config.py             # Environment variables and RSS feed definitions
├── fetch_news.py         # Fetches RSS feeds, filters last 24h, deduplicates via SQLite
├── summarize_news.py     # Calls GitHub Models API (GPT-4o) to generate summaries
├── send_messages.py      # Pushes formatted messages to LINE via Messaging API
├── run_daily.sh          # Shell script that orchestrates the full pipeline
├── state.sqlite3         # SQLite DB tracking previously pushed articles
├── requirements.txt      # Python dependencies
├── .env                  # API keys and config (not committed)
├── .env.example          # Template for .env
├── .gitignore
├── logs/                 # Runtime logs (not committed)
└── ops/cron/
    └── finpulse-daily.json   # OpenClaw cron config (optional)
```

## How It Works

1. **fetch_news.py** — Pulls articles from RSS feeds (international + Taiwan), filters to last 24 hours, removes already-pushed articles using SQLite
2. **summarize_news.py** — Sends article titles/snippets to GPT-4o via GitHub Models API, receives beginner-friendly summaries with background explanations in Traditional Chinese
3. **send_messages.py** — Pushes the formatted digest to LINE using the Messaging API push endpoint

## Prerequisites

- Python 3.10+
- GitHub Personal Access Token (fine-grained) with `Models: Read` permission
- LINE Messaging API channel with a long-lived channel access token
- LINE target user ID (starts with `U`)

## Setup

```bash
cd finpulse
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with your tokens
```

### Getting the tokens

**GitHub Token** (for AI):
1. Go to https://github.com/settings/personal-access-tokens/new
2. Create a fine-grained token
3. Under Account permissions → set **Models** to **Read**

**LINE Channel Access Token**:
1. Go to https://developers.line.biz/ and log in with your LINE account
2. Create a provider and a Messaging API channel (via LINE Official Account Manager)
3. In the channel's Messaging API tab, issue a long-lived channel access token

**LINE Target (your user ID)**:
1. Set a webhook URL (e.g. webhook.site) in the Messaging API tab
2. Send a message to your bot on LINE
3. Copy the `userId` from the webhook payload

## Usage

```bash
# Test fetching news only
python fetch_news.py

# Full pipeline (fetch + summarize + send to LINE)
# On Windows, run as a single process to avoid pipe encoding issues:
python -c "
from fetch_news import *
from summarize_news import *
from send_messages import *
# ... or use run_daily.sh on Linux/macOS
"

# On Linux/macOS:
bash run_daily.sh
```

### Known issue: Windows pipe encoding

On Windows, piping between Python processes (`fetch | summarize | send`) can corrupt CJK characters due to codepage issues. The recommended approach on Windows is to run the pipeline within a single Python process or use the temp-file approach in `run_daily.sh` with `PYTHONUTF8=1`:

```bash
export PYTHONUTF8=1
bash run_daily.sh
```

## Scheduling

**Linux/macOS (cron):**
```cron
30 7 * * * cd /path/to/finpulse && bash run_daily.sh
```

**Windows Task Scheduler:**
Create a daily task at 07:30 that runs:
```
python C:\path\to\finpulse\run_daily.sh
```

**OpenClaw:**
```bash
openclaw cron add --name "FinPulse" --cron "30 7 * * *" --tz "Asia/Taipei" \
  --session isolated --command-argv '["./run_daily.sh"]' --command-cwd "/path/to/finpulse"
```

## News Sources

| Category | Source | Feed |
|----------|--------|------|
| International | Reuters/CNBC via Google News | Google News RSS (finance keywords) |
| Taiwan | CnYes (鉅亨網) | cnyes.com RSS |
| Taiwan | UDN Money (經濟日報) | money.udn.com RSS |
| Taiwan | Google News TW | Google News RSS (台股/經濟 keywords) |

## Output Example

```
🇹🇼 FinPulse 台灣財經早報 2026-06-30
━━━━━━━━━━━━━━━━━━━━

📌 台股暴跌逾千點，台積電尾盤遭大量賣壓

📰 台股今日重挫 1,126 點，盤中一度跌超過 1,637 點，
創下史上第三大單日跌幅。台積電尾盤出現近兩萬張賣單。

💡 想像股市是高樓，台積電是其中的柱子，柱子搖晃時
整座樓就跟著晃動。這次台股跌了一層樓那麼多。

📊 投資股票的上班族可能感受到帳戶價值縮水，
投資氣氛變得更謹慎。
```
