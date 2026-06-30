#!/usr/bin/env python3
"""Summarize news articles using GitHub Models API with beginner-friendly explanations."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone

from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

from config import GITHUB_TOKEN, AI_MODEL

# Windows defaults stdout to cp1252, which cannot encode the CJK/emoji payload.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

TZ_TPE = timezone(timedelta(hours=8))

SYSTEM_PROMPT = """你是「FinPulse 財經脈動」的編輯，讀者是剛接觸財經新聞的台灣上班族。
你的任務是把財經新聞轉化為任何人都能看懂的內容。

規則：
- 使用繁體中文
- 用生活化的比喻解釋專業概念
- 不要假設讀者知道任何財經術語
- 保持客觀，不做投資建議
- 每則新聞的解說控制在 150 字以內"""

NEWS_PROMPT_TEMPLATE = """請針對以下{count}則{category_label}財經新聞，每一則提供：

1. 📌 一句話摘要（15-20字）
2. 📰 發生什麼事（2-3句）
3. 💡 白話解說（用生活化比喻，讓不懂財經的人也能理解）
4. 📊 可能的影響（對一般人的影響，1-2句）

用 --- 分隔每則新聞。

新聞列表：
{news_list}"""


def safe_json(payload: dict) -> str:
    """Serialize to JSON, dropping lone surrogates that RSS/AI text can contain
    and that would otherwise break UTF-8 encoding on output."""
    text = json.dumps(payload, ensure_ascii=False)
    return text.encode("utf-8", "ignore").decode("utf-8")


def build_news_list(articles: list[dict]) -> str:
    parts = []
    for i, a in enumerate(articles, 1):
        parts.append(f"[{i}] 標題：{a['title']}\n    來源：{a['source']}\n    摘要：{a.get('snippet', '無')}")
    return "\n\n".join(parts)


def call_ai(prompt: str) -> str:
    client = ChatCompletionsClient(
        endpoint="https://models.inference.ai.azure.com",
        credential=AzureKeyCredential(GITHUB_TOKEN),
    )
    response = client.complete(
        messages=[
            SystemMessage(content=SYSTEM_PROMPT),
            UserMessage(content=prompt),
        ],
        model=AI_MODEL,
    )
    return response.choices[0].message.content


def summarize_batch(articles: list[dict], category_label: str) -> str | None:
    if not articles:
        return None

    prompt = NEWS_PROMPT_TEMPLATE.format(
        count=len(articles),
        category_label=category_label,
        news_list=build_news_list(articles),
    )

    try:
        return call_ai(prompt)
    except Exception as e:
        print(f"[error] AI summarization failed for {category_label}: {e}", file=sys.stderr)
        return None


def format_fallback(articles: list[dict], category_label: str) -> str:
    """Fallback to raw headlines when AI summarization is unavailable."""
    lines = [f"📋 {category_label}新聞標題（AI 摘要暫時無法使用）\n"]
    for a in articles:
        lines.append(f"• {a['title']}\n  {a['link']}")
    return "\n".join(lines)


def format_telegram_message(international_summary: str | None, taiwan_summary: str | None,
                            international_articles: list[dict], taiwan_articles: list[dict]) -> list[dict]:
    """Build message payloads for Telegram delivery."""
    today = datetime.now(TZ_TPE).strftime("%Y-%m-%d")
    messages = []

    if international_articles:
        header = f"🌍 FinPulse 國際財經早報 {today}\n{'━' * 20}\n"
        body = international_summary or format_fallback(international_articles, "國際")
        messages.append({"message": header + body, "silent": False})

    if taiwan_articles:
        header = f"🇹🇼 FinPulse 台灣財經早報 {today}\n{'━' * 20}\n"
        body = taiwan_summary or format_fallback(taiwan_articles, "台灣")
        messages.append({"message": header + body, "silent": False})

    if not messages:
        messages.append({"message": f"📭 FinPulse {today}：今日無新的重大財經新聞。", "silent": True})

    return messages


def main() -> int:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print(f"[error] Invalid JSON input: {e}", file=sys.stderr)
        return 1

    articles = data.get("articles", [])
    if not articles:
        messages = format_telegram_message(None, None, [], [])
        print(safe_json({"messages": messages}))
        return 0

    international = [a for a in articles if a.get("category") == "international"]
    taiwan = [a for a in articles if a.get("category") == "taiwan"]

    international_summary = summarize_batch(international, "國際")
    taiwan_summary = summarize_batch(taiwan, "台灣")

    messages = format_telegram_message(international_summary, taiwan_summary, international, taiwan)

    print(safe_json({
        "messages": messages,
        "articles": articles,
    }))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
