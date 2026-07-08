#!/usr/bin/env python3
"""Summarize news articles using GitHub Models API with beginner-friendly explanations."""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timedelta, timezone

import requests
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

from config import GITHUB_TOKEN, AI_MODEL, PICK_PER_CATEGORY

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

SELECT_PROMPT_TEMPLATE = """以下是 {count} 則{category_label}財經新聞候選。請你以「FinPulse 編輯」的角度，
從中挑出**最重要的 {pick} 則**（判斷依據：對台灣一般讀者的重要性、影響範圍、時效性），
並針對選中的每一則撰寫白話摘要。

只回傳 JSON，格式如下（不要有任何多餘文字或 markdown 圍欄）：
{{"picks": [{{"index": <候選編號，整數>, "summary": "<四段式摘要>"}}]}}

每則的 summary 需包含以下四段，段落之間用換行分隔：
📌 一句話摘要（15-20字）
📰 發生什麼事（2-3句）
💡 白話解說（用生活化比喻，讓不懂財經的人也能理解）
📊 可能的影響（對一般人的影響，1-2句）

候選新聞列表：
{news_list}"""

FEATURE_PROMPT_TEMPLATE = """以下是 {count} 則財經新聞候選（含國際與台灣）。請你以「FinPulse 主編」的角度，
從中挑出**當天最重要的一則**（判斷依據：對台灣一般讀者的重要性、影響範圍、時效性），
把它寫成一篇「簡化版專題報導」——不只是摘要這則新聞，而是把背景、來龍去脈、影響都講清楚，
讓完全不懂財經的人也能讀懂這件事的全貌。

只回傳 JSON，格式如下（不要有任何多餘文字或 markdown 圍欄）：
{{"index": <候選編號，整數>, "feature": "<專題內文>"}}

feature 內文請包含以下幾段，段落之間用換行分隔，**全文控制在 500 字以內**：
（標題行）用一句話點出今日焦點
📰 發生什麼事（把這則新聞說清楚）
🔍 背景與來龍去脈（相關的前因後果、為什麼會發生、和過去哪些事有關）
🌐 影響（對市場、對台灣一般人可能造成的多方面影響）

候選新聞列表：
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


def parse_picks(raw: str, candidate_count: int) -> list[dict] | None:
    """Parse the AI's JSON reply into a list of {index, summary}.
    Tolerates ```json fences. Returns None if unparseable so callers fall back."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    picks = data.get("picks") if isinstance(data, dict) else None
    if not isinstance(picks, list):
        return None

    cleaned = []
    seen = set()
    for p in picks:
        if not isinstance(p, dict):
            continue
        idx = p.get("index")
        summary = p.get("summary")
        if not isinstance(idx, int) or not isinstance(summary, str):
            continue
        if idx < 1 or idx > candidate_count or idx in seen:
            continue
        seen.add(idx)
        cleaned.append({"index": idx, "summary": summary})
    return cleaned or None


def parse_feature(raw: str, candidate_count: int) -> dict | None:
    """Parse the AI's feature reply into {index, feature}.
    Tolerates ```json fences. Returns None if unparseable/out-of-range so the
    caller drops the feature for the day rather than emitting an empty shell."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None

    if not isinstance(data, dict):
        return None
    idx = data.get("index")
    feature = data.get("feature")
    if not isinstance(idx, int) or not isinstance(feature, str) or not feature.strip():
        return None
    if idx < 1 or idx > candidate_count:
        return None
    return {"index": idx, "feature": feature.strip()}


def select_and_summarize(articles: list[dict], category_label: str,
                         pick: int = PICK_PER_CATEGORY) -> list[dict]:
    """Ask the AI to pick the most important `pick` articles from the candidates
    and summarize them. Returns a list of selected article dicts, each with a
    `summary` field. Falls back to the top candidates (already recency-sorted by
    fetch) when the AI call fails or returns unusable output — so we always emit
    exactly `pick` items and dedup stays correct."""
    if not articles:
        return []

    prompt = SELECT_PROMPT_TEMPLATE.format(
        count=len(articles),
        category_label=category_label,
        pick=pick,
        news_list=build_news_list(articles),
    )

    picks = None
    try:
        picks = parse_picks(call_ai(prompt), len(articles))
    except Exception as e:
        print(f"[error] AI selection failed for {category_label}: {e}", file=sys.stderr)

    if not picks:
        return [dict(a, summary_text=None) for a in articles[:pick]]

    selected = []
    for p in picks[:pick]:
        article = dict(articles[p["index"] - 1])
        article["summary_text"] = p["summary"]
        selected.append(article)
    return selected


def select_feature(articles: list[dict]) -> dict | None:
    """Ask the AI to pick the single most important article across all candidates
    and write it up as a simplified feature (background + context + impact).
    Returns the selected article dict with a `feature_text` field, or None when
    there are no candidates or the AI fails — the feature is optional, so on
    failure we simply skip it for the day instead of emitting an empty shell."""
    if not articles:
        return None

    prompt = FEATURE_PROMPT_TEMPLATE.format(
        count=len(articles),
        news_list=build_news_list(articles),
    )

    parsed = None
    try:
        parsed = parse_feature(call_ai(prompt), len(articles))
    except Exception as e:
        print(f"[error] AI feature selection failed: {e}", file=sys.stderr)

    if not parsed:
        return None

    article = dict(articles[parsed["index"] - 1])
    article["feature_text"] = parsed["feature"]
    return article


def shorten_url(url: str) -> str:
    """Shorten a URL via TinyURL's keyless endpoint. Returns the original URL
    on any failure so message delivery never depends on the shortener."""
    try:
        resp = requests.get(
            "https://tinyurl.com/api-create.php",
            params={"url": url},
            timeout=8,
        )
        short = resp.text.strip()
        if resp.status_code == 200 and short.startswith("http"):
            return short
    except requests.RequestException as e:
        print(f"[warn] URL shorten failed: {e}", file=sys.stderr)
    return url


def format_source_links(articles: list[dict]) -> str:
    lines = ["\n🔗 原文連結"]
    for article in articles:
        lines.append(f"{article['title']}\n{shorten_url(article['link'])}")
    return "\n".join(lines)


def build_category_body(selected: list[dict], category_label: str) -> str:
    """Join per-article AI summaries; fall back to the raw headline for any
    article whose summary is missing (AI failure path)."""
    blocks = []
    for a in selected:
        summary = a.get("summary_text")
        if summary:
            blocks.append(summary.strip())
        else:
            blocks.append(f"📌 {a['title']}\n（AI 摘要暫時無法使用）")
    return f"\n{'─' * 12}\n".join(blocks)


def format_messages(feature_article: dict | None,
                    international_selected: list[dict],
                    taiwan_selected: list[dict]) -> list[dict]:
    """Build message payloads for LINE delivery from the AI-selected articles.
    The feature (if any) leads, followed by the international and Taiwan digests."""
    today = datetime.now(TZ_TPE).strftime("%Y-%m-%d")
    messages = []

    if feature_article:
        header = f"🔥 FinPulse 今日焦點 {today}\n{'━' * 20}\n"
        body = feature_article["feature_text"].strip() + format_source_links([feature_article])
        messages.append({"message": header + body, "silent": False})

    if international_selected:
        header = f"🌍 FinPulse 國際財經早報 {today}\n{'━' * 20}\n"
        body = build_category_body(international_selected, "國際") + format_source_links(international_selected)
        messages.append({"message": header + body, "silent": False})

    if taiwan_selected:
        header = f"🇹🇼 FinPulse 台灣財經早報 {today}\n{'━' * 20}\n"
        body = build_category_body(taiwan_selected, "台灣") + format_source_links(taiwan_selected)
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
        messages = format_messages(None, [], [])
        print(safe_json({"messages": messages}))
        return 0

    international = [a for a in articles if a.get("category") == "international"]
    taiwan = [a for a in articles if a.get("category") == "taiwan"]

    # Pick the day's feature across all candidates first, then drop it from the
    # digest candidates so the feature and the short summaries never cover the
    # exact same article.
    feature_article = select_feature(international + taiwan)
    if feature_article:
        feature_link = feature_article.get("link")
        international = [a for a in international if a.get("link") != feature_link]
        taiwan = [a for a in taiwan if a.get("link") != feature_link]

    international_selected = select_and_summarize(international, "國際")
    taiwan_selected = select_and_summarize(taiwan, "台灣")

    messages = format_messages(feature_article, international_selected, taiwan_selected)

    # Only the AI-selected articles go downstream, so send_messages.py dedup marks
    # exactly what was pushed — unpicked candidates stay eligible for future days.
    # The feature is included so it also gets recorded and won't repeat tomorrow.
    picked = ([feature_article] if feature_article else []) + international_selected + taiwan_selected
    print(safe_json({
        "messages": messages,
        "articles": picked,
    }))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
