import logging
import time
import requests
from typing import List
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

class WebsiteProcessor:
    """Handle website content processing."""
    @staticmethod
    def get_urls_from_sitemap(sitemap_url: str) -> List[str]:
        """Extract URLs from a sitemap XML file."""
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            logger.debug("Downloading sitemap from %s (attempt %d)", sitemap_url, attempt)
            response = requests.get(sitemap_url)
            if response.status_code == 200:
                break
            logger.warning(
                "Attempt %d/%d failed to load sitemap from %s (status %d)",
                attempt, max_retries, sitemap_url, response.status_code
            )
            if attempt < max_retries:
                time.sleep(2)
        else:
            raise Exception(
                f"Failed to load sitemap from {sitemap_url}: "
                f"server returned status code {response.status_code}"
            )
        soup = BeautifulSoup(response.text, "xml")
        return [loc.text for loc in soup.find_all("loc")]

    @staticmethod
    def download_and_clean_html(url: str) -> str:
        """Download HTML from a URL and clean it for processing."""
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            logger.debug("Downloading HTML from %s (attempt %d)", url, attempt)
            response = requests.get(url)
            if response.status_code == 200:
                break
            logger.warning(
                "Attempt %d/%d failed to download HTML from %s (status %d)",
                attempt, max_retries, url, response.status_code
            )
            if attempt < max_retries:
                time.sleep(2)
        else:
            raise Exception(
                f"Failed to download HTML from {url}: "
                f"server returned status code {response.status_code}"
            )
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)
