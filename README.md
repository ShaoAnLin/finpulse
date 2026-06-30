# FinPulse

Daily financial news digest delivered to Telegram with beginner-friendly explanations in Traditional Chinese.

## How It Works

```
RSS feeds → fetch_news.py → summarize_news.py (GitHub Models AI) → send_messages.py (Telegram)
```

1. Fetch international + Taiwan financial news from RSS feeds
2. Summarize with AI (GPT-4o via GitHub Models API) including plain-language background explanations
3. Push to Telegram via OpenClaw

## Prerequisites

- Python 3.10+
- [OpenClaw](https://openclaw.ai/) installed with Telegram configured
- GitHub Personal Access Token with `models:read` permission (fine-grained token)

## Setup

```bash
cd finpulse
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your GitHub token and Telegram chat ID
```

## Usage

```bash
# Test fetching news only
python3 fetch_news.py

# Full pipeline (fetch + summarize + send)
bash run_daily.sh
```

## Schedule Daily Digest

```bash
openclaw cron add \
  --name "FinPulse Daily Digest" \
  --cron "30 7 * * *" \
  --tz "Asia/Taipei" \
  --session isolated \
  --command-argv '["./run_daily.sh"]' \
  --command-cwd "/path/to/finpulse" \
  --timeout-seconds 300 \
  --no-deliver
```

## News Sources

| Category | Sources |
|----------|---------|
| International | Reuters, CNBC (via Google News RSS) |
| Taiwan | CnYes, UDN Money, Google News TW Finance |

## Cost

- OpenClaw: Free
- RSS feeds: Free
- GitHub Models API: Free (150 requests/day)
- Telegram: Free
