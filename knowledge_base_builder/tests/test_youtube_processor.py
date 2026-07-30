"""Tests for YouTubeProcessor — URL detection, ID extraction, transcript fetching."""

import asyncio
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from knowledge_base_builder.youtube_processor import YouTubeProcessor


# ---------------------------------------------------------------------------
# URL detection (pure logic, no mocks)
# ---------------------------------------------------------------------------
class TestIsYouTubeUrl:
    @pytest.mark.parametrize("url", [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com/watch?v=abc123_-XYZ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "http://youtube.com/watch?v=abc&list=PLxyz",
    ])
    def test_valid_youtube_urls(self, url):
        assert YouTubeProcessor.is_youtube_url(url) is True

    @pytest.mark.parametrize("url", [
        "https://example.com/video",
        "https://vimeo.com/12345",
        "not-a-url",
        "https://youtube.com/channel/UCxyz",
        "",
    ])
    def test_non_youtube_urls(self, url):
        assert YouTubeProcessor.is_youtube_url(url) is False


# ---------------------------------------------------------------------------
# Video ID extraction (pure logic)
# ---------------------------------------------------------------------------
class TestExtractVideoId:
    def test_watch_url(self):
        assert YouTubeProcessor.extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_short_url(self):
        assert YouTubeProcessor.extract_video_id("https://youtu.be/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_embed_url(self):
        assert YouTubeProcessor.extract_video_id("https://youtube.com/embed/dQw4w9WgXcQ") == "dQw4w9WgXcQ"

    def test_watch_with_extra_params(self):
        assert YouTubeProcessor.extract_video_id("https://youtube.com/watch?v=dQw4w9WgXcQ&t=120") == "dQw4w9WgXcQ"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Could not extract video ID"):
            YouTubeProcessor.extract_video_id("https://example.com/page")


# ---------------------------------------------------------------------------
# Transcript extraction (mocked API)
# ---------------------------------------------------------------------------
class TestExtractText:
    @patch("knowledge_base_builder.youtube_processor._YT_AVAILABLE", True)
    def test_extract_text_realistic_transcript(self):
        """Mock a realistic multi-segment transcript."""
        import knowledge_base_builder.youtube_processor as yt_mod
        mock_api = MagicMock()
        mock_api.get_transcript.return_value = [
            {"text": "Welcome to the video.", "start": 0.0, "duration": 2.5},
            {"text": "Today we'll discuss Python.", "start": 2.5, "duration": 3.0},
            {"text": "Let's get started.", "start": 5.5, "duration": 1.5},
        ]
        with patch.object(yt_mod, "YouTubeTranscriptApi", mock_api, create=True):
            result = YouTubeProcessor.extract_text("https://youtube.com/watch?v=abc12345678")

        assert "# YouTube Video Transcript (abc12345678)" in result
        assert "Welcome to the video." in result
        assert "Today we'll discuss Python." in result
        assert "Let's get started." in result
        mock_api.get_transcript.assert_called_once_with("abc12345678")

    @patch("knowledge_base_builder.youtube_processor._YT_AVAILABLE", True)
    def test_extract_text_empty_transcript(self):
        """Video exists but has empty transcript."""
        import knowledge_base_builder.youtube_processor as yt_mod
        mock_api = MagicMock()
        mock_api.get_transcript.return_value = []
        with patch.object(yt_mod, "YouTubeTranscriptApi", mock_api, create=True):
            result = YouTubeProcessor.extract_text("https://youtube.com/watch?v=abc12345678")
        assert "abc12345678" in result
        # Should still have the header even with empty transcript
        assert "# YouTube Video Transcript" in result

    @patch("knowledge_base_builder.youtube_processor._YT_AVAILABLE", True)
    def test_extract_text_api_error(self):
        """Transcript API raises (e.g. captions disabled)."""
        import knowledge_base_builder.youtube_processor as yt_mod
        mock_api = MagicMock()
        mock_api.get_transcript.side_effect = Exception("Subtitles are disabled for this video")
        with patch.object(yt_mod, "YouTubeTranscriptApi", mock_api, create=True):
            with pytest.raises(Exception, match="Subtitles are disabled"):
                YouTubeProcessor.extract_text("https://youtube.com/watch?v=abc12345678")

    @patch("knowledge_base_builder.youtube_processor._YT_AVAILABLE", False)
    def test_library_not_installed(self):
        with pytest.raises(ImportError, match="youtube-transcript-api is required"):
            YouTubeProcessor.extract_text("https://youtube.com/watch?v=abc12345678")

    def test_download_returns_url_unchanged(self):
        url = "https://youtube.com/watch?v=abc12345678"
        assert YouTubeProcessor.download(url) == url


# ---------------------------------------------------------------------------
# Integration: routing in process_files_async
# ---------------------------------------------------------------------------
class TestYouTubeRouting:
    @patch("knowledge_base_builder.kb_builder.GeminiClient")
    def test_youtube_url_routed_to_youtube_processor(self, mock_gemini):
        from knowledge_base_builder.kb_builder import KBBuilder
        kbb = KBBuilder({"GOOGLE_API_KEY": "fake"})
        from knowledge_base_builder.build_metadata import BuildMetadata
        kbb._build_meta = BuildMetadata("test", "test", 0.7)
        kbb._cache = None
        kbb._text_sources = []
        kbb.youtube_processor = MagicMock()
        kbb.youtube_processor.download.return_value = "https://youtube.com/watch?v=test"
        kbb.youtube_processor.extract_text.return_value = "transcript text"

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(kbb.process_files_async([
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            ]))
        finally:
            loop.close()

        kbb.youtube_processor.download.assert_called_once()
        kbb.youtube_processor.extract_text.assert_called_once()
        assert len(kbb.text_contents) == 1
