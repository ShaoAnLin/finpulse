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

from config import GITHUB_TOKEN, AI_MODEL, TAVILY_API_KEY

# Windows defaults stdout to cp1252, which cannot encode the CJK/emoji payload.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

TZ_TPE = timezone(timedelta(hours=8))

SYSTEM_PROMPT = """你是「FinPulse 財經脈動」的主編，讀者是有基本常識、想快速掌握財經大事來龍去脈的台灣上班族。
你的任務是把財經新聞整理成清楚、有脈絡的專題。

規則：
- 使用繁體中文
- 把背景、前因後果、影響講清楚，重點是「來龍去脈」而非逐字翻譯新聞
- 遇到專業術語可簡短帶過，不需假設讀者完全不懂，也不用刻意寫給小學生看
- 保持客觀，不做投資建議"""

SELECT_PROMPT_TEMPLATE = """以下是 {count} 則{category_label}財經新聞候選。請以「FinPulse 主編」的角度，
挑出**當天最重要的一則**（判斷依據：對台灣一般讀者的重要性、影響範圍、時效性）。

只回傳 JSON，格式如下（不要有任何多餘文字或 markdown 圍欄）：
{{"index": <候選編號，整數>}}

候選新聞列表：
{news_list}"""

FEATURE_PROMPT_TEMPLATE = """以下是一則{category_label}財經新聞，請你以「FinPulse 主編」的角度，
把它寫成一篇「專題報導」——不只是摘要這則新聞，而是把背景、來龍去脈、影響都講清楚，
讓讀者掌握這件事的全貌。

只回傳 JSON，格式如下（不要有任何多餘文字或 markdown 圍欄）：
{{"feature": "<專題內文>"}}

feature 內文請包含以下幾段，段落之間用換行分隔，**全文控制在 500 字以內**：
（標題行）用一句話點出焦點
📰 發生什麼事（把這則新聞說清楚）
🔍 背景與來龍去脈（相關的前因後果、為什麼會發生、和過去哪些事有關）
🌐 影響（對市場、對台灣一般人可能造成的多方面影響）

新聞：
標題：{title}
來源：{source}
摘要：{snippet}
{research}"""

RESEARCH_BLOCK_TEMPLATE = """
以下是針對候選新聞，透過即時網路搜尋取得的多來源延伸資料（可能包含比 RSS 摘要更完整的內容與最新進展）。
撰寫專題時請善用這些資料補充背景與來龍去脈，但仍以繁體中文改寫、不要照抄：

{research_body}"""


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


def tavily_research(query: str, max_results: int = 4) -> str:
    """Run a live web search via Tavily and return concatenated multi-source
    content for the given query. Returns "" on any failure or when no key is
    configured, so the feature write-up degrades to RSS-only rather than
    breaking the daily run."""
    if not TAVILY_API_KEY:
        return ""
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            headers={"Authorization": f"Bearer {TAVILY_API_KEY}"},
            json={
                "query": query,
                "topic": "news",
                "search_depth": "advanced",
                "max_results": max_results,
                "days": 7,
                "include_raw_content": "text",
            },
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as e:
        print(f"[warn] Tavily search failed for {query!r}: {e}", file=sys.stderr)
        return ""

    blocks = []
    for r in data.get("results", []):
        title = (r.get("title") or "").strip()
        url = (r.get("url") or "").strip()
        content = (r.get("raw_content") or r.get("content") or "").strip()
        if not content:
            continue
        blocks.append(f"【{title}】（{url}）\n{content[:2000]}")
    return "\n\n".join(blocks)


def _strip_fences(raw: str) -> str:
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    return text


def parse_index(raw: str, candidate_count: int) -> int | None:
    """Parse the AI's selection reply into a 1-based candidate index.
    Returns None if unparseable/out-of-range so the caller can fall back to the
    top recency-sorted candidate."""
    try:
        data = json.loads(_strip_fences(raw))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    idx = data.get("index")
    if not isinstance(idx, int) or idx < 1 or idx > candidate_count:
        return None
    return idx


def parse_feature(raw: str) -> str | None:
    """Parse the AI's feature reply into the feature text.
    Tolerates ```json fences. Returns None if unparseable/empty so the caller
    drops the feature for that category rather than emitting an empty shell."""
    try:
        data = json.loads(_strip_fences(raw))
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    feature = data.get("feature")
    if not isinstance(feature, str) or not feature.strip():
        return None
    return feature.strip()


def select_feature(articles: list[dict], category_label: str) -> dict | None:
    """Pick the single most important article for a category, enrich it with a
    live Tavily web search, and write it up as a feature (background + context +
    impact). Returns the selected article dict with a `feature_text` field, or
    None when there are no candidates or the write-up fails."""
    if not articles:
        return None

    # Step 1: cheap selection — pick the winning candidate by index only.
    select_prompt = SELECT_PROMPT_TEMPLATE.format(
        count=len(articles),
        category_label=category_label,
        news_list=build_news_list(articles),
    )
    idx = None
    try:
        idx = parse_index(call_ai(select_prompt), len(articles))
    except Exception as e:
        print(f"[error] AI selection failed for {category_label}: {e}", file=sys.stderr)
    article = dict(articles[(idx - 1) if idx else 0])

    # Step 2: live web research on the winner via Tavily (best-effort).
    research_text = tavily_research(article["title"])
    research = RESEARCH_BLOCK_TEMPLATE.format(research_body=research_text) if research_text else ""

    # Step 3: write the feature, grounded in the multi-source research.
    feature_prompt = FEATURE_PROMPT_TEMPLATE.format(
        category_label=category_label,
        title=article["title"],
        source=article["source"],
        snippet=article.get("snippet", "無"),
        research=research,
    )
    feature = None
    try:
        feature = parse_feature(call_ai(feature_prompt))
    except Exception as e:
        print(f"[error] AI feature write-up failed for {category_label}: {e}", file=sys.stderr)

    if not feature:
        return None

    article["feature_text"] = feature
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


def format_messages(international_feature: dict | None,
                    taiwan_feature: dict | None) -> list[dict]:
    """Build message payloads for LINE delivery from the two AI-selected
    features: one international, one Taiwan."""
    today = datetime.now(TZ_TPE).strftime("%Y-%m-%d")
    messages = []

    if international_feature:
        header = f"🌍 FinPulse 國際焦點 {today}\n{'━' * 20}\n"
        body = international_feature["feature_text"].strip() + format_source_links([international_feature])
        messages.append({"message": header + body, "silent": False})

    if taiwan_feature:
        header = f"🇹🇼 FinPulse 台灣焦點 {today}\n{'━' * 20}\n"
        body = taiwan_feature["feature_text"].strip() + format_source_links([taiwan_feature])
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
        messages = format_messages(None, None)
        print(safe_json({"messages": messages}))
        return 0

    international = [a for a in articles if a.get("category") == "international"]
    taiwan = [a for a in articles if a.get("category") == "taiwan"]

    international_feature = select_feature(international, "國際")
    taiwan_feature = select_feature(taiwan, "台灣")

    messages = format_messages(international_feature, taiwan_feature)

    # Only the AI-selected features go downstream, so send_messages.py dedup marks
    # exactly what was pushed — unpicked candidates stay eligible for future days.
    picked = [f for f in (international_feature, taiwan_feature) if f]
    print(safe_json({
        "messages": messages,
        "articles": picked,
    }))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
