import logging
from knowledge_base_builder.base_processor import BaseProcessor

logger = logging.getLogger(__name__)

try:
    import feedparser
    _FEEDPARSER_AVAILABLE = True
except ImportError:
    _FEEDPARSER_AVAILABLE = False

class RSSProcessor(BaseProcessor):
    SUPPORTED_EXTENSIONS = ['.rss', '.atom']

    @staticmethod
    def is_rss_url(url: str) -> bool:
        """Heuristic: URL likely points to an RSS/Atom feed."""
        lower = url.lower()
        return any(indicator in lower for indicator in ['/feed', '/rss', '.rss', '.atom', '/atom.xml', 'feed.xml'])

    @staticmethod
    def download(url: str) -> str:
        # feedparser can handle URLs directly, return URL as-is
        return url

    @staticmethod
    def extract_text(url_or_path: str) -> str:
        if not _FEEDPARSER_AVAILABLE:
            raise ImportError("feedparser is required. Install with: pip install feedparser")
        logger.info("Parsing RSS feed: %s", url_or_path)
        feed = feedparser.parse(url_or_path)

        parts = []
        if feed.feed.get('title'):
            parts.append(f"# {feed.feed.title}")
        if feed.feed.get('description'):
            parts.append(f"> {feed.feed.description}")

        for entry in feed.entries:
            title = entry.get('title', 'Untitled')
            link = entry.get('link', '')
            published = entry.get('published', '')

            header = f"## {title}"
            if link:
                header = f"## [{title}]({link})"
            parts.append(header)

            if published:
                parts.append(f"*Published: {published}*")

            # Get content: try content[0].value, then summary, then description
            content = ''
            if entry.get('content'):
                content = entry.content[0].get('value', '')
            elif entry.get('summary'):
                content = entry.summary
            elif entry.get('description'):
                content = entry.description

            if content:
                # Strip HTML tags simply
                import re
                clean = re.sub(r'<[^>]+>', '', content)
                parts.append(clean.strip())

        return '\n\n'.join(parts)
