import logging
import time

import requests
from typing import List, Optional

logger = logging.getLogger(__name__)

class GitHubProcessor:
    """Handle GitHub repository processing."""
    def __init__(self, username: Optional[str] = None, token: Optional[str] = None):
        self.username = username
        self.headers = {"Authorization": f"token {token}"} if token else {}

    def get_markdown_urls(self) -> List[str]:
        """Get all markdown file URLs from user's repositories."""
        if not self.username:
            raise ValueError("Username is required for this method")

        repos = self.get_user_repos()
        urls = []
        for repo in repos:
            logger.info("Scanning repo: %s", repo)
            urls.extend(self.get_markdown_urls_for_repo(self.username, repo))
        return urls

    def get_user_repos(self) -> List[str]:
        """Get all repositories for a user."""
        if not self.username:
            raise ValueError("Username is required for this method")

        repos = []
        page = 1
        while True:
            url = f"https://api.github.com/users/{self.username}/repos?per_page=100&page={page}"
            res = requests.get(url, headers=self.headers)
            if res.status_code != 200:
                if res.status_code in (403, 429):
                    remaining = res.headers.get("X-RateLimit-Remaining", "unknown")
                    reset = res.headers.get("X-RateLimit-Reset", "unknown")
                    raise Exception(
                        f"GitHub API rate limit error ({res.status_code}): "
                        f"remaining={remaining}, reset={reset}"
                    )
                raise Exception(
                    f"GitHub API error: {res.status_code} for user '{self.username}'"
                )
            data = res.json()
            if not data:
                break
            repos.extend(repo['name'] for repo in data)
            page += 1
        return repos

    def get_markdown_urls_for_repo(self, owner: str, repo: str) -> List[str]:
        """Get all markdown files from a specific repository."""
        def recurse(path=""):
            url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
            res = requests.get(url, headers=self.headers)
            if res.status_code != 200:
                if res.status_code in (403, 429):
                    remaining = res.headers.get("X-RateLimit-Remaining", "unknown")
                    reset = res.headers.get("X-RateLimit-Reset", "unknown")
                    logger.warning(
                        "Rate limited (%d) while fetching %s/%s path='%s': "
                        "remaining=%s, reset=%s",
                        res.status_code, owner, repo, path, remaining, reset,
                    )
                else:
                    logger.warning(
                        "Non-200 status %d while fetching %s/%s path='%s'",
                        res.status_code, owner, repo, path,
                    )
                return []
            contents = res.json()
            files = []
            for item in contents:
                if item['type'] == 'file' and item['name'].endswith('.md'):
                    files.append(item['download_url'])
                elif item['type'] == 'dir':
                    files.extend(recurse(item['path']))
            return files
        return recurse()

    @staticmethod
    def download_markdown(url: str) -> str:
        """Download markdown content from a URL."""
        last_exc = None
        for attempt in range(1, 4):
            try:
                res = requests.get(url)
                if res.status_code == 200:
                    return res.text
                last_exc = Exception(
                    f"Failed to fetch markdown from {url}: status {res.status_code}"
                )
            except requests.RequestException as exc:
                last_exc = exc
            if attempt < 3:
                logger.warning(
                    "Attempt %d/3 failed for %s, retrying in 1s...", attempt, url
                )
                time.sleep(1)
        raise last_exc
