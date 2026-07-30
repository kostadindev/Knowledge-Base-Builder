import re
import logging
from knowledge_base_builder.base_processor import BaseProcessor

logger = logging.getLogger(__name__)

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    _YT_AVAILABLE = True
except ImportError:
    _YT_AVAILABLE = False

class YouTubeProcessor(BaseProcessor):
    SUPPORTED_EXTENSIONS = []

    @staticmethod
    def is_youtube_url(url: str) -> bool:
        """Check if URL is a YouTube video."""
        return bool(re.search(r'(youtube\.com/watch|youtu\.be/|youtube\.com/embed/)', url))

    @staticmethod
    def extract_video_id(url: str) -> str:
        """Extract video ID from various YouTube URL formats."""
        # Handle youtu.be/ID, youtube.com/watch?v=ID, youtube.com/embed/ID
        patterns = [
            r'youtu\.be/([a-zA-Z0-9_-]{11})',
            r'youtube\.com/watch\?.*v=([a-zA-Z0-9_-]{11})',
            r'youtube\.com/embed/([a-zA-Z0-9_-]{11})',
        ]
        for p in patterns:
            m = re.search(p, url)
            if m:
                return m.group(1)
        raise ValueError(f"Could not extract video ID from: {url}")

    @staticmethod
    def download(url: str) -> str:
        # No file download needed — return URL as-is
        return url

    @staticmethod
    def extract_text(url: str) -> str:
        if not _YT_AVAILABLE:
            raise ImportError("youtube-transcript-api is required. Install with: pip install youtube-transcript-api")
        video_id = YouTubeProcessor.extract_video_id(url)
        logger.info("Fetching transcript for video: %s", video_id)
        transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        lines = [entry['text'] for entry in transcript_list]
        return f"# YouTube Video Transcript ({video_id})\n\n" + " ".join(lines)
