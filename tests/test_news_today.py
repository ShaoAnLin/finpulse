import json
import tempfile
import unittest
from pathlib import Path

from send_messages import write_news_today
from summarize_news import build_candidates


class NewsTodayTest(unittest.TestCase):
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
            {"title", "snippet", "category", "source", "link"},
        )


if __name__ == "__main__":
    unittest.main()
