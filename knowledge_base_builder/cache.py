"""Incremental build cache for knowledge base construction."""

import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import Optional, Dict

logger = logging.getLogger(__name__)


class BuildCache:
    """Manages a .kbb_cache/ directory for incremental builds.

    Stores a manifest mapping URL -> content hash + path to cached extracted text.
    On rebuild, sources whose content hash matches the cache are skipped.
    """

    MANIFEST_FILE = "manifest.json"
    TEXTS_DIR = "texts"

    def __init__(self, cache_dir: str = ".kbb_cache"):
        self.cache_dir = cache_dir
        self.texts_dir = os.path.join(cache_dir, self.TEXTS_DIR)
        self.manifest_path = os.path.join(cache_dir, self.MANIFEST_FILE)
        self.manifest: Dict[str, dict] = {}
        self._load_manifest()

    def _load_manifest(self) -> None:
        if os.path.exists(self.manifest_path):
            try:
                with open(self.manifest_path, "r", encoding="utf-8") as f:
                    self.manifest = json.load(f)
                logger.info("Loaded cache manifest with %d entries", len(self.manifest))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Cache manifest corrupt, starting fresh: %s", e)
                self.manifest = {}
        else:
            self.manifest = {}

    def save_manifest(self) -> None:
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(self.manifest_path, "w", encoding="utf-8") as f:
            json.dump(self.manifest, f, indent=2)

    @staticmethod
    def hash_content(content: bytes) -> str:
        return hashlib.sha256(content).hexdigest()

    @staticmethod
    def _url_key(url: str) -> str:
        return url.strip().rstrip("/")

    def _text_path(self, url: str) -> str:
        url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
        return os.path.join(self.texts_dir, f"{url_hash}.txt")

    def get_cached_text(self, url: str, content_hash: str) -> Optional[str]:
        """Return cached extracted text if content hash matches, else None."""
        key = self._url_key(url)
        entry = self.manifest.get(key)
        if not entry or entry.get("content_hash") != content_hash:
            return None
        text_path = entry.get("text_path")
        if not text_path or not os.path.exists(text_path):
            return None
        try:
            with open(text_path, "r", encoding="utf-8") as f:
                return f.read()
        except OSError:
            return None

    def update_entry(self, url: str, content_hash: str, extracted_text: str) -> None:
        """Store or update a cache entry."""
        os.makedirs(self.texts_dir, exist_ok=True)
        text_path = self._text_path(url)
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(extracted_text)
        key = self._url_key(url)
        self.manifest[key] = {
            "content_hash": content_hash,
            "text_path": text_path,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def clear(self) -> None:
        """Remove the entire cache directory."""
        import shutil
        if os.path.exists(self.cache_dir):
            shutil.rmtree(self.cache_dir)
            logger.info("Cache cleared: %s", self.cache_dir)
        self.manifest = {}
