# FinPulse

Daily financial news digest delivered to LINE with beginner-friendly explanations in Traditional Chinese.

## How It Works

```
RSS feeds → fetch_news.py → summarize_news.py (GitHub Models AI) → send_messages.py (LINE)
```

1. Fetch international + Taiwan financial news from RSS feeds
2. Summarize with AI (GPT-4o via GitHub Models API) including plain-language background explanations
3. Push to LINE via the Messaging API

## Prerequisites

- Python 3.10+
- A LINE Messaging API channel (create one in the [LINE Developers Console](https://developers.line.biz/)) with a long-lived channel access token
- GitHub Personal Access Token with `models:read` permission (fine-grained token)

## Setup

```bash
cd finpulse
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your GitHub token, LINE channel access token, and LINE target ID
```

## Usage

```bash
# Test fetching news only
python3 fetch_news.py

# Full pipeline (fetch + summarize + send)
bash run_daily.sh
```

## Schedule Daily Digest

Run `run_daily.sh` on a schedule with whatever scheduler your platform provides.

**cron (Linux/macOS)** — daily at 07:30 Taipei time:

```cron
30 7 * * * cd /path/to/finpulse && ./run_daily.sh
```

(Set the host timezone to `Asia/Taipei`, or adjust the cron hour accordingly.)

**Windows Task Scheduler** — create a daily task that runs:

```
bash /path/to/finpulse/run_daily.sh
```

## News Sources

| Category | Sources |
|----------|---------|
| International | Reuters, CNBC (via Google News RSS) |
| Taiwan | CnYes, UDN Money, Google News TW Finance |

## Cost

- RSS feeds: Free
- GitHub Models API: Free (150 requests/day)
- LINE Messaging API: Free tier (~200 push messages/month)
