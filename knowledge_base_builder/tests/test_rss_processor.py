"""Tests for RSSProcessor — URL detection and feed parsing with real feedparser structures."""

import asyncio
import pytest
from unittest.mock import patch, MagicMock
from knowledge_base_builder.rss_processor import RSSProcessor


# ---------------------------------------------------------------------------
# URL detection (pure logic)
# ---------------------------------------------------------------------------
class TestIsRssUrl:
    @pytest.mark.parametrize("url", [
        "https://example.com/feed",
        "https://example.com/rss",
        "https://example.com/blog.rss",
        "https://example.com/atom.xml",
        "https://example.com/feed.xml",
        "https://example.com/blog.atom",
        "https://example.com/index.php/feed",
    ])
    def test_valid_rss_urls(self, url):
        assert RSSProcessor.is_rss_url(url) is True

    @pytest.mark.parametrize("url", [
        "https://example.com/page",
        "https://example.com/blog",
        "https://example.com/about",
        "",
    ])
    def test_non_rss_urls(self, url):
        assert RSSProcessor.is_rss_url(url) is False


# ---------------------------------------------------------------------------
# Feed parsing with real feedparser data structures
# ---------------------------------------------------------------------------
class TestExtractText:
    @patch("knowledge_base_builder.rss_processor._FEEDPARSER_AVAILABLE", True)
    @patch("knowledge_base_builder.rss_processor.feedparser")
    def test_realistic_rss_feed(self, mock_feedparser):
        """Use a feedparser-like FeedParserDict structure (real feedparser uses attribute access)."""
        feed = MagicMock()
        feed.feed.get = lambda k: {"title": "Tech Blog", "description": "A blog about tech"}.get(k)
        feed.feed.title = "Tech Blog"
        feed.feed.description = "A blog about tech"

        entry1 = MagicMock()
        entry1.get = lambda k, d="": {"title": "First Post", "link": "https://blog.com/1", "published": "2024-01-15", "content": None, "summary": "Summary of post one.", "description": ""}.get(k, d)
        entry1.summary = "Summary of post one."

        entry2 = MagicMock()
        entry2.get = lambda k, d="": {"title": "Second Post", "link": "https://blog.com/2", "published": "2024-01-20", "content": None, "summary": None, "description": "Description fallback."}.get(k, d)
        entry2.description = "Description fallback."

        feed.entries = [entry1, entry2]
        mock_feedparser.parse.return_value = feed

        result = RSSProcessor.extract_text("https://blog.com/feed")

        assert "# Tech Blog" in result
        assert "> A blog about tech" in result
        assert "[First Post](https://blog.com/1)" in result
        assert "*Published: 2024-01-15*" in result
        assert "Summary of post one." in result
        assert "[Second Post](https://blog.com/2)" in result

    @patch("knowledge_base_builder.rss_processor._FEEDPARSER_AVAILABLE", True)
    @patch("knowledge_base_builder.rss_processor.feedparser")
    def test_html_content_stripped(self, mock_feedparser):
        """Verify HTML tags are stripped from entry content."""
        feed = MagicMock()
        feed.feed.get = lambda k: None
        feed.entries = []

        content_obj = MagicMock()
        content_obj.get = lambda k, d="": {"value": "<p>Hello <strong>world</strong></p><br/><a href='x'>link</a>"}.get(k, d)

        entry = MagicMock()
        entry.get = lambda k, d="": {"title": "HTML Post", "link": "", "published": "", "content": [content_obj], "summary": "", "description": ""}.get(k, d)
        entry.content = [content_obj]

        feed.entries = [entry]
        mock_feedparser.parse.return_value = feed

        result = RSSProcessor.extract_text("https://blog.com/feed")
        assert "Hello world" in result
        assert "<p>" not in result
        assert "<strong>" not in result
        assert "<br" not in result

    @patch("knowledge_base_builder.rss_processor._FEEDPARSER_AVAILABLE", True)
    @patch("knowledge_base_builder.rss_processor.feedparser")
    def test_empty_feed(self, mock_feedparser):
        """Feed with no entries."""
        feed = MagicMock()
        feed.feed.get = lambda k: {"title": "Empty Blog"}.get(k)
        feed.feed.title = "Empty Blog"
        feed.entries = []
        mock_feedparser.parse.return_value = feed

        result = RSSProcessor.extract_text("https://blog.com/feed")
        assert "# Empty Blog" in result
        assert "##" not in result  # No entries

    @patch("knowledge_base_builder.rss_processor._FEEDPARSER_AVAILABLE", False)
    def test_library_not_installed(self):
        with pytest.raises(ImportError, match="feedparser is required"):
            RSSProcessor.extract_text("https://blog.com/feed")

    def test_download_returns_url_unchanged(self):
        assert RSSProcessor.download("https://blog.com/feed") == "https://blog.com/feed"


# ---------------------------------------------------------------------------
# Integration: routing
# ---------------------------------------------------------------------------
class TestRSSRouting:
    @patch("knowledge_base_builder.kb_builder.GeminiClient")
    def test_rss_url_routed_to_rss_processor(self, mock_gemini):
        from knowledge_base_builder.kb_builder import KBBuilder
        kbb = KBBuilder({"GOOGLE_API_KEY": "fake"})
        from knowledge_base_builder.build_metadata import BuildMetadata
        kbb._build_meta = BuildMetadata("test", "test", 0.7)
        kbb._cache = None
        kbb._text_sources = []
        kbb.rss_processor = MagicMock()
        kbb.rss_processor.download.return_value = "https://blog.com/feed"
        kbb.rss_processor.extract_text.return_value = "# Blog\n\n## Post 1\nContent"

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(kbb.process_files_async([
                "https://example.com/feed",
            ]))
        finally:
            loop.close()

        kbb.rss_processor.download.assert_called_once()
        kbb.rss_processor.extract_text.assert_called_once()
