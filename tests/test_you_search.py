"""Tests for the You.com web search integration; no network calls are made."""
import json
import os
import unittest
from unittest.mock import patch

from allinagent.you_search import search_web


class _FakeResponse:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class YouSearchTests(unittest.TestCase):
    def test_missing_key_is_explained(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertIn("Set YDC_API_KEY", search_web("test"))

    def test_posts_key_and_returns_citations(self):
        payload = {"results": {"web": [{
            "title": "Example page",
            "url": "https://example.com/article",
            "description": "A short description",
        }], "news": []}}
        with patch.dict(os.environ, {"YDC_API_KEY": "test-secret"}, clear=True):
            with patch("allinagent.you_search.urlopen", return_value=_FakeResponse(payload)) as mocked:
                result = search_web("example query", count=3)
        request = mocked.call_args.args[0]
        self.assertEqual(request.get_header("X-api-key"), "test-secret")
        self.assertEqual(json.loads(request.data), {"query": "example query", "count": 3})
        self.assertIn("https://example.com/article", result)
        self.assertIn("Example page", result)

    def test_you_api_key_compatibility_fallback(self):
        payload = {"results": {"web": [], "news": []}}
        with patch.dict(os.environ, {"YOU_API_KEY": "fallback-secret"}, clear=True):
            with patch("allinagent.you_search.urlopen", return_value=_FakeResponse(payload)) as mocked:
                search_web("example")
        self.assertEqual(mocked.call_args.args[0].get_header("X-api-key"), "fallback-secret")

    def test_empty_query_is_rejected(self):
        self.assertIn("Enter a search query", search_web("   "))


if __name__ == "__main__":
    unittest.main()
