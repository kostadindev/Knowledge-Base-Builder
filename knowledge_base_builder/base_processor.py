import os
import logging
import requests
import tempfile
import time
import urllib.parse
import re
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class BaseProcessor(ABC):
    """Base class for all document processors."""

    @staticmethod
    def check_accessible(url: str):
        """Check whether *url* is reachable.

        Returns:
            Tuple of ``(accessible, status_code, error)``.
            *status_code* is ``None`` for ``file://`` URLs and on exceptions.
        """
        try:
            if url.startswith("file://"):
                parsed = urllib.parse.urlparse(url)
                local_path = urllib.parse.unquote(parsed.path)
                if os.path.exists(local_path):
                    return (True, None, None)
                else:
                    return (False, None, "File not found")
            elif url.startswith(("http://", "https://")):
                resp = requests.head(url, timeout=10, allow_redirects=True)
                if 200 <= resp.status_code < 300:
                    return (True, resp.status_code, None)
                else:
                    return (False, resp.status_code, f"HTTP {resp.status_code}")
            else:
                # Treat as a local path
                if os.path.exists(url):
                    return (True, None, None)
                else:
                    return (False, None, "File not found")
        except Exception as exc:
            return (False, None, str(exc))

    @staticmethod
    def download(url: str, supported_extensions: list) -> str:
        """Download a file from a URL or load from local file."""
        if url.startswith("file://"):
            parsed = urllib.parse.urlparse(url)
            local_path = urllib.parse.unquote(parsed.path)

            # Handle path differences between Windows and Mac/Linux
            if os.name == 'nt':  # Windows
                # For Windows paths with drive letters (like C:/)
                if local_path.startswith('/') and len(local_path) > 1:
                    # Windows paths might have multiple leading slashes - remove them all before the drive letter
                    while local_path.startswith('/') and len(local_path) > 2 and local_path[1:3] != ':/':
                        local_path = local_path[1:]

                    # Now handle the format /C:/path/to/file.pdf -> C:/path/to/file.pdf
                    if len(local_path) > 2 and local_path[1].isalpha() and local_path[2] == ':':
                        local_path = local_path[1:]

                # Ensure proper slash direction for Windows
                local_path = local_path.replace('/', '\\')
            else:  # Mac/Linux - ensure path starts with /
                if not local_path.startswith('/'):
                    local_path = '/' + local_path

            # Replace any remaining URL encodings (like %20 for spaces)
            local_path = urllib.parse.unquote(local_path)

            if not os.path.exists(local_path):
                raise FileNotFoundError(f"Local file not found: {local_path}")
            return local_path
        else:
            max_retries = 3
            for attempt in range(1, max_retries + 1):
                response = requests.get(url)
                if response.status_code == 200:
                    break
                logger.warning(
                    "Attempt %d/%d failed to download %s (status %d)",
                    attempt, max_retries, url, response.status_code
                )
                if attempt < max_retries:
                    time.sleep(2)
            else:
                raise Exception(
                    f"Failed to download file from {url}: "
                    f"server returned status code {response.status_code}"
                )

            # Parse the filename from URL or headers
            filename = url.split('/')[-1].split('?')[0]
            content_disposition = response.headers.get('content-disposition')
            if content_disposition:
                cd_match = re.findall('filename="(.+?)"', content_disposition)
                if cd_match:
                    filename = cd_match[0]

            # Ensure we have the correct file extension
            if not any(filename.lower().endswith(ext) for ext in supported_extensions):
                # Try to guess from content-type
                content_type = response.headers.get('content-type', '')
                # Default to first supported extension if we can't determine
                filename = filename + supported_extensions[0]

            # Create temporary file with the correct extension
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(filename)[1])
            temp_file.write(response.content)
            temp_file.close()
            return temp_file.name

    @abstractmethod
    def extract_text(self, file_path: str) -> str:
        """Extract text from a file. Must be implemented by subclasses."""
        pass
