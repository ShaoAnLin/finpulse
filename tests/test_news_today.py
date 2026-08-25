import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from db import init_db
from export_news import export_recent_features
from fetch_news import clean_rss_text, select_top_news, url_hash
from send_messages import TZ_TPE, write_news_today
from summarize_news import build_candidates


class NewsTodayTest(unittest.TestCase):
    def test_clean_rss_text_decodes_entities_and_removes_html(self):
        self.assertEqual(
            clean_rss_text("<p>市場&nbsp;上漲 &amp; <strong>成交量</strong>增加</p>"),
            "市場 上漲 & 成交量增加",
        )

    def test_history_contains_only_recent_ai_features(self):
        now = datetime(2026, 8, 12, 9, 0, tzinfo=timezone(timedelta(hours=8)))
        rows = [
            ("recent-intl", "2026-08-12T08:00:00+08:00", "international", "AI feature"),
            ("boundary-tw", "2026-08-06T00:00:00+08:00", "taiwan", "Boundary feature"),
            ("utc-boundary", "2026-08-05T16:30:00Z", "international", "UTC boundary feature"),
            ("too-old", "2026-08-05T23:59:59+08:00", "international", "Old feature"),
            ("rss-only", "2026-08-11T08:00:00+08:00", "taiwan", ""),
            ("missing-ai", "2026-08-10T08:00:00+08:00", "taiwan", None),
        ]
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "state.sqlite3")
            con = init_db(db_path)
            for title, pushed_at, category, feature_text in rows:
                con.execute(
                    """
                    INSERT INTO pushed_news
                        (url_hash, url, title, pushed_at, category, source, feature_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        title,
                        f"https://example.com/{title}",
                        title,
                        pushed_at,
                        category,
                        "Source",
                        feature_text,
                    ),
                )
            con.commit()
            con.close()

            history = export_recent_features(db_path, now=now)

        self.assertEqual(
            [day["date"] for day in history["days"]],
            ["2026-08-12", "2026-08-06"],
        )
        self.assertEqual(
            [article["title"] for article in history["days"][1]["featured"]],
            ["utc-boundary", "boundary-tw"],
        )

    def test_history_keeps_latest_feature_per_category_each_day(self):
        now = datetime(2026, 8, 12, 9, 0, tzinfo=TZ_TPE)
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "state.sqlite3")
            con = init_db(db_path)
            for index, (pushed_at, category) in enumerate([
                ("2026-08-11T07:00:00+08:00", "international"),
                ("2026-08-11T09:00:00+08:00", "international"),
                ("2026-08-11T08:00:00+08:00", "taiwan"),
            ]):
                con.execute(
                    """
                    INSERT INTO pushed_news
                        (url_hash, url, title, pushed_at, category, source, feature_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        str(index),
                        f"https://example.com/{index}",
                        f"Feature {index}",
                        pushed_at,
                        category,
                        "Source",
                        f"AI feature {index}",
                    ),
                )
            con.commit()
            con.close()

            history = export_recent_features(db_path, now=now)

        self.assertEqual(len(history["days"]), 1)
        self.assertEqual(
            [article["title"] for article in history["days"][0]["featured"]],
            ["Feature 1", "Feature 2"],
        )

    def test_candidates_exclude_features_and_keep_ten_newest(self):
        articles = [
            {
                "title": f"News {index}",
                "link": f"https://example.com/{index}",
                "published": f"2026-08-{index:02d}T00:00:00+00:00",
            }
            for index in range(1, 13)
        ]

        candidates = build_candidates(articles, [articles[-1]])

        self.assertEqual(len(candidates), 10)
        self.assertNotIn(articles[-1], candidates)
        self.assertEqual(candidates[0]["title"], "News 11")
        self.assertEqual(candidates[-1]["title"], "News 2")

    def test_candidates_prioritize_international_share_when_available(self):
        international = [{
            "title": f"Intl {index}",
            "link": f"https://example.com/intl-{index}",
            "published": f"2026-08-{index:02d}T00:00:00+00:00",
            "category": "international",
        } for index in range(1, 7)]
        taiwan = [{
            "title": f"TW {index}",
            "link": f"https://example.com/tw-{index}",
            "published": f"2026-08-{index+6:02d}T00:00:00+00:00",
            "category": "taiwan",
        } for index in range(1, 7)]

        candidates = build_candidates(international + taiwan, picked=[])

        self.assertEqual(len(candidates), 10)
        self.assertEqual(
            sum(1 for item in candidates if item.get("category") == "international"),
            5,
        )

    def test_candidates_deprioritize_intraday_flash_when_limit_is_tight(self):
        articles = [
            {
                "title": "盤中速報 - 某公司大漲7%",
                "snippet": "股價快速上漲，成交量放大",
                "source": "CnYes",
                "link": "https://example.com/flash",
                "published": "2026-08-12T09:00:00+00:00",
                "category": "taiwan",
            },
            {
                "title": "央行最新政策釋出，影響台股資金面",
                "snippet": "政策背景與市場解讀",
                "source": "UDN Money",
                "link": "https://example.com/policy",
                "published": "2026-08-12T08:00:00+00:00",
                "category": "taiwan",
            },
        ]

        candidates = build_candidates(articles, picked=[], limit=1)
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["link"], "https://example.com/policy")

    def test_candidates_cap_single_source_when_alternatives_exist(self):
        cnyes = [{
            "title": f"盤中速報 - CnYes {index}",
            "snippet": "股價與成交量更新",
            "source": "CnYes",
            "link": f"https://example.com/cnyes-{index}",
            "published": f"2026-08-{index:02d}T09:00:00+00:00",
            "category": "taiwan",
        } for index in range(1, 9)]
        udn = [{
            "title": f"UDN {index}",
            "snippet": "產業新聞",
            "source": "UDN Money",
            "link": f"https://example.com/udn-{index}",
            "published": f"2026-08-{index+8:02d}T08:00:00+00:00",
            "category": "taiwan",
        } for index in range(1, 5)]
        google = [{
            "title": f"Google TW {index}",
            "snippet": "總體經濟新聞",
            "source": "Google TW Finance",
            "link": f"https://example.com/google-{index}",
            "published": f"2026-08-{index+12:02d}T07:00:00+00:00",
            "category": "taiwan",
        } for index in range(1, 5)]

        candidates = build_candidates(cnyes + udn + google, picked=[], limit=10)

        self.assertEqual(len(candidates), 10)
        self.assertLessEqual(sum(1 for item in candidates if item.get("source") == "CnYes"), 3)

    def test_candidates_backfill_to_ten_even_if_single_source(self):
        articles = [{
            "title": f"盤中速報 - CnYes {index}",
            "snippet": "股價更新",
            "source": "CnYes",
            "link": f"https://example.com/only-cnyes-{index}",
            "published": f"2026-08-{index:02d}T09:00:00+00:00",
            "category": "taiwan",
        } for index in range(1, 13)]

        candidates = build_candidates(articles, picked=[], limit=10)
        self.assertEqual(len(candidates), 10)

    def test_write_news_today_uses_public_schema_and_caps_candidates(self):
        featured = [{
            "category": "international",
            "title": "Featured",
            "feature_text": "Full feature",
            "source": "Reuters",
            "link": "https://example.com/featured",
            "published": "private pipeline field",
        }]
        candidates = [{
            "category": "taiwan",
            "title": f"Candidate {index}",
            "snippet": f"Snippet {index}",
            "source": "CnYes",
            "link": f"https://example.com/candidate-{index}",
            "published": "private pipeline field",
        } for index in range(11)]

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "docs" / "news-today.json"
            write_news_today(featured, candidates, str(output))
            data = json.loads(output.read_text(encoding="utf-8"))

        self.assertRegex(data["date"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(data["featured"], [{
            "category": "international",
            "title": "Featured",
            "feature": "Full feature",
            "source": "Reuters",
            "link": "https://example.com/featured",
        }])
        self.assertEqual(len(data["candidates"]), 10)
        self.assertEqual(
            set(data["candidates"][0]),
            {"title", "content", "category", "source", "link"},
        )

    def test_write_news_today_merges_same_day_payload(self):
        existing_payload = {
            "date": datetime.now(TZ_TPE).strftime("%Y-%m-%d"),
            "featured": [{
                "category": "taiwan",
                "title": "Old Taiwan",
                "feature": "Old feature",
                "source": "Old source",
                "link": "https://example.com/tw-old",
            }],
            "candidates": [{
                "title": "Old candidate",
                "snippet": "Old snippet",
                "category": "international",
                "source": "Old source",
                "link": "https://example.com/old-candidate",
            }],
        }
        featured = [{
            "category": "international",
            "title": "New Intl",
            "feature_text": "New feature",
            "source": "Reuters",
            "link": "https://example.com/new-intl",
        }]
        candidates = [{
            "category": "international",
            "title": "Duplicate old",
            "snippet": "Should dedup",
            "source": "Reuters",
            "link": "https://example.com/old-candidate",
        }, {
            "category": "taiwan",
            "title": "Candidate to drop",
            "snippet": "Same as featured link",
            "source": "CnYes",
            "link": "https://example.com/tw-old",
        }, {
            "category": "taiwan",
            "title": "New candidate",
            "snippet": "Keep me",
            "source": "CnYes",
            "link": "https://example.com/new-candidate",
        }]

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "docs" / "news-today.json"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(json.dumps(existing_payload, ensure_ascii=False), encoding="utf-8")
            write_news_today(featured, candidates, str(output))
            data = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual([item["category"] for item in data["featured"]], ["international", "taiwan"])
        self.assertEqual(data["featured"][1]["title"], "Old Taiwan")
        self.assertEqual(
            [item["link"] for item in data["candidates"]],
            [
                "https://example.com/old-candidate",
                "https://example.com/new-candidate",
            ],
        )
        self.assertEqual(data["candidates"][0]["content"], "Should dedup")

    def test_select_top_news_allows_same_day_rerun_but_keeps_cross_day_dedup(self):
        now = datetime.now(TZ_TPE).replace(microsecond=0)
        yesterday = now - timedelta(days=1)
        with tempfile.TemporaryDirectory() as directory:
            db_path = str(Path(directory) / "state.sqlite3")
            con = init_db(db_path)
            con.execute(
                """
                INSERT INTO pushed_news (url_hash, url, title, pushed_at)
                VALUES (?, ?, ?, ?)
                """,
                (url_hash("https://example.com/today"), "https://example.com/today", "Today", now.isoformat()),
            )
            con.execute(
                """
                INSERT INTO pushed_news (url_hash, url, title, pushed_at)
                VALUES (?, ?, ?, ?)
                """,
                (url_hash("https://example.com/yesterday"), "https://example.com/yesterday", "Yesterday", yesterday.isoformat()),
            )
            con.commit()

            selected = select_top_news(
                [
                    {"title": "Today", "link": "https://example.com/today", "published": "2026-08-12T01:00:00+00:00"},
                    {"title": "Yesterday", "link": "https://example.com/yesterday", "published": "2026-08-11T02:00:00+00:00"},
                    {"title": "New", "link": "https://example.com/new", "published": "2026-08-12T03:00:00+00:00"},
                ],
                max_count=10,
                con=con,
            )
            con.close()

        self.assertEqual(
            [item["link"] for item in selected],
            ["https://example.com/new", "https://example.com/today"],
        )


if __name__ == "__main__":
    unittest.main()
