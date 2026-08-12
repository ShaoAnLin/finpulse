# FinPulse

Daily financial news digest delivered to LINE in Traditional Chinese. Each day it
publishes two in-depth features — one international, one Taiwan — with background
and context pulled from live web search (Tavily), not just RSS snippets.

## Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                       FinPulse Pipeline                      │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  RSS Feeds ──► fetch_news.py ──► summarize_news.py           │
│  (Free)        (feedparser)      │  1. AI picks top story    │
│                     │            │  2. Tavily live search    │
│                     ▼            │  3. Groq LLM writes it up │
│              state.sqlite3       └──────────┬────────────────┘
│              (dedup store)                  ▼                │
│                                    send_messages.py          │
│                                    (LINE + web cache)        │
│                                      │           │           │
│                                      ▼           ▼           │
│                               LINE Bot       GitHub Pages    │
└──────────────────────────────────────────────────────────────┘
```

## Tools & Services Used

| Component | Tool / Service | Cost |
|-----------|---------------|------|
| News source | Google News RSS, CnYes RSS, UDN Money RSS | Free |
| Live web research | Tavily Search API (multi-source context for features) | Free tier (~4 credits/day) |
| AI summarization | Groq API (Llama 3.3 70B) | Free tier |
| Message delivery | LINE Messaging API (Push) | Free (200 msg/month; ~2/day = ~60/month) |
| Deduplication | SQLite (local file) | Free |
| Scheduling | cron / Task Scheduler / OpenClaw | Free |
| Hosting | Azure DevBox (or any always-on machine) | Existing |

## Project Structure

```
finpulse/
├── config.py             # Environment variables and RSS feed definitions
├── db.py                 # Shared pushed_news schema/migration helpers
├── fetch_news.py         # Fetches RSS feeds, filters last 24h, deduplicates via SQLite
├── summarize_news.py     # Calls Groq API (Llama 3.3 70B) to generate summaries
├── send_messages.py      # Pushes formatted messages to LINE via Messaging API
├── export_news.py        # Exports historical pushed_news rows to JSON for the webpage
├── run_daily.sh          # Shell script that orchestrates the full pipeline
├── web/                  # React + Vite + Tailwind source
├── docs/                 # Built GitHub Pages site and today's JSON cache
├── state.sqlite3         # SQLite DB tracking previously pushed articles (with full detail)
├── requirements.txt      # Python dependencies
├── .env                  # API keys and config (not committed)
├── .env.example          # Template for .env
├── .gitignore
├── logs/                 # Runtime logs (not committed)
└── ops/cron/
    └── finpulse-daily.json   # OpenClaw cron config (optional)
```

## How It Works

1. **fetch_news.py** — Pulls articles from RSS feeds (international + Taiwan), filters to last 24 hours, removes already-pushed articles using SQLite. Candidate volume is controlled by `MAX_NEWS_INTERNATIONAL` / `MAX_NEWS_TAIWAN` in `config.py`
2. **summarize_news.py** — For each category (international + Taiwan), runs a three-step feature flow:
   1. The Groq model picks the single most important story from the candidates
   2. **Tavily Search API** runs a live web search on that story's headline (`topic=news`, last 7 days) and returns multi-source page content
   3. The Groq model writes a ~500-word Traditional Chinese feature — headline, what happened, background/context, impact — grounded in the live research rather than just the RSS snippet. If Tavily is unavailable it degrades gracefully to RSS-only
3. **send_messages.py** — Pushes the two features to LINE, records their full details in `state.sqlite3`, then replaces `docs/news-today.json` with those features and the 10 newest unselected candidates
4. **finpulse-web** — Reads only `docs/news-today.json`: the two LINE features are shown in full, while candidate cards expand to reveal their complete RSS snippet and original link

## Historical Data Export

`state.sqlite3`'s `pushed_news` table doubles as both the dedup ledger (used to
avoid re-sending an article) and a historical archive of everything ever pushed
to LINE. Each row stores:

| Column | Description |
|--------|-------------|
| `url_hash` | SHA-256 hash of the article URL (primary key) |
| `url` | Original article link |
| `title` | Article title |
| `pushed_at` | ISO-8601 timestamp (Asia/Taipei) when it was sent |
| `category` | `international` or `taiwan` |
| `source` | Feed name (e.g. CnYes, Reuters Business) |
| `snippet` | RSS summary snippet |
| `published` | Article's original published timestamp |
| `feature_text` | The full AI-written Traditional Chinese feature sent to LINE |

To export this history as JSON (e.g. for a webpage that displays past digests):

```bash
python export_news.py [output_path]   # defaults to news_export.json
```

Databases created before this schema was introduced are migrated in place
(missing columns are added via `ALTER TABLE`) the next time `fetch_news.py` or
`send_messages.py` runs, so no manual migration step is required. Rows written
before the migration will have `NULL` values for the newer columns since that
detail was not previously captured.

## Prerequisites

- Python 3.10+
- Groq API key (`gsk_…`) — free from https://console.groq.com/keys
- Tavily API key (`tvly-…`) — free tier from https://app.tavily.com
- LINE Messaging API channel with a long-lived channel access token
- LINE target ID — a user ID (starts with `U`) or a group ID (starts with `C`)

## Setup

```bash
cd finpulse
pip install -r requirements.txt
cp .env.example .env
# Fill in .env with your tokens
```

### Getting the tokens

**Groq API Key** (for AI):
1. Sign up at https://console.groq.com (Google/GitHub login)
2. Create an API key under https://console.groq.com/keys
3. Copy the `gsk_…` key into `GROQ_API_KEY`

**Tavily API Key** (for live web search):
1. Sign up at https://app.tavily.com (Google/email, no credit card)
2. Copy the `tvly-…` key from the dashboard into `TAVILY_API_KEY`

**LINE Channel Access Token**:
1. Go to https://developers.line.biz/ and log in with your LINE account
2. Create a provider and a Messaging API channel (via LINE Official Account Manager)
3. In the channel's Messaging API tab, issue a long-lived channel access token

**LINE Target (delivery destination)**:

Set `FINPULSE_LINE_TARGET` to either a **user ID** (`U…`, delivers to one person) or a **group ID** (`C…`, delivers to a group chat). The same push endpoint handles both, so no code change is needed to switch.

To get a *user ID*:
1. Set a webhook URL (e.g. webhook.site) in the Messaging API tab
2. Send a message to your bot on LINE
3. Copy the `userId` from the webhook payload

To get a *group ID*:
1. In the LINE Developers Console, enable **"Allow bot to join group chats"** (Messaging API settings)
2. Invite the bot (your LINE Official Account) into the group
3. With a webhook URL configured, send any message in the group
4. Copy `source.groupId` (starts with `C`) from the webhook payload

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

**GitHub Actions:**
`.env` is intentionally not committed. Store production values in GitHub instead:

Repository Settings -> Secrets and variables -> Actions -> Secrets:
- `GROQ_API_KEY`: Groq API key (`gsk_…`)
- `TAVILY_API_KEY`: Tavily Search API key (`tvly-…`)
- `LINE_CHANNEL_ACCESS_TOKEN`: LINE Messaging API channel access token
- `FINPULSE_LINE_TARGET`: LINE user ID or group ID

Optional repository variable:
- `FINPULSE_AI_MODEL`: defaults to `llama-3.3-70b-versatile` when unset

The workflow in `.github/workflows/finpulse-daily.yml` runs daily at 07:30 Asia/Taipei and can also be started manually from the Actions tab.
After a successful LINE broadcast, it commits the refreshed `docs/news-today.json`. If you rerun on the same day, new results are merged into today's cache (instead of fully replacing it), so manual reruns can progressively improve the same-day digest.

## finpulse-web

The mobile-first frontend source lives in `web/`; Vite builds the static site directly
into `docs/` without deleting `docs/news-today.json`.

```bash
cd web
npm install
npm run dev       # local development
npm run lint
npm run build     # refresh the committed static files in ../docs
```

To deploy, open **Settings → Pages**, choose **Deploy from a branch**, select the
default branch and the `/docs` folder, then save. The site shows only today's cache;
each successful daily workflow replaces the prior day's data rather than creating an archive.

**Linux/macOS (cron):**
```cron
30 7 * * * cd /path/to/finpulse && bash run_daily.sh
```

**Windows Task Scheduler:**
Create a daily task at 07:30 that runs:
```
"C:\Program Files\Git\bin\bash.exe" -lc "cd '/c/path/to/finpulse' && FINPULSE_PYTHON='/c/path/to/python.exe' ./run_daily.sh"
```

`FINPULSE_PYTHON` is optional on machines where `python3` already resolves to the Python environment with the packages from `requirements.txt` installed.

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

Each day sends two features (🌍 international + 🇹🇼 Taiwan), each grounded in live web search:

```
🌍 FinPulse 國際焦點 2026-07-20
━━━━━━━━━━━━━━━━━━━━
### 聯準會不加息，因應通膨降溫之勢

📰 發生什麼事
美國聯準會宣布維持基準利率不變。6 月消費者物價指數（CPI）年增率
降至 3.5%（5 月為 4.2%），核心 CPI 為 2.6%，顯示通膨壓力緩解。

🔍 背景與來龍去脈
去年以來 Fed 多輪激進升息以壓抑通膨。近期能源價格回落（年減 5.7%）、
供應鏈緩解，減輕物價壓力。市場依 CME FedWatch 預測進一步升息機率下降。

🌐 影響
暫停升息對全球股市偏多。但房貸利率仍維持約 6.5% 高位。對台灣而言，
可望舒緩國際資金波動、支撐新台幣匯率。

🔗 原文連結
Fed holds rates steady as inflation cools
https://tinyurl.com/...
```

(The CPI figures, energy price change, and mortgage rate above come from Tavily's
live search — none of them are in the original RSS snippet.)
