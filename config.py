import os
from dotenv import load_dotenv

load_dotenv()

GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")
AI_MODEL = os.environ.get("FINPULSE_AI_MODEL", "gpt-4o")

TELEGRAM_TARGET = os.environ.get("FINPULSE_TELEGRAM_TARGET", "")
TELEGRAM_CHANNEL = os.environ.get("FINPULSE_CHANNEL", "telegram")
TELEGRAM_ACCOUNT = os.environ.get("FINPULSE_ACCOUNT_ID", "default")

MAX_NEWS_INTERNATIONAL = 5
MAX_NEWS_TAIWAN = 5

RSS_FEEDS = {
    "international": [
        {
            "name": "Reuters Business",
            "url": "https://news.google.com/rss/search?q=finance+economy+stock+market&hl=en&gl=US&ceid=US:en",
        },
        {
            "name": "CNBC",
            "url": "https://news.google.com/rss/search?q=site:cnbc.com+market+economy&hl=en&gl=US&ceid=US:en",
        },
    ],
    "taiwan": [
        {
            "name": "CnYes",
            "url": "https://news.cnyes.com/news/cat/headline/rss",
        },
        {
            "name": "UDN Money",
            "url": "https://money.udn.com/rssfeed/news/1001/5588?ch=money",
        },
        {
            "name": "Google TW Finance",
            "url": "https://news.google.com/rss/search?q=%E5%8F%B0%E8%82%A1+OR+%E5%8F%B0%E7%81%A3%E7%B6%93%E6%BF%9F+OR+%E5%A4%AE%E8%A1%8C&hl=zh-TW&gl=TW&ceid=TW:zh-Hant",
        },
    ],
}

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "state.sqlite3")
