"""Chunked output for vector database ingestion."""

import re
from typing import List, Tuple


class Chunker:
    """Splits extracted texts into chunks suitable for vector DB ingestion.

    Each chunk is a dictionary with ``id``, ``text``, and ``metadata`` keys.
    Metadata includes ``source`` (URL), ``section`` (nearest Markdown heading),
    and ``index`` (position within the source document).
    """

    def __init__(self, chunk_size: int = 1000):
        if chunk_size <= 0:
            raise ValueError("chunk_size must be a positive integer")
        self.chunk_size = chunk_size

    def chunk_texts(self, texts_with_sources: List[Tuple[str, str]]) -> List[dict]:
        """Split a list of ``(text, source_url)`` pairs into chunk dicts.

        Returns a flat list of chunk dictionaries with sequential IDs across
        all sources.
        """
        chunks: List[dict] = []
        global_index = 0

        for text, source_url in texts_with_sources:
            if not text or not text.strip():
                continue

            parts = self._split_at_boundaries(text, self.chunk_size)
            position = 0
            for local_index, part in enumerate(parts):
                section = self._detect_section(text, position)
                chunks.append({
                    "id": f"chunk_{global_index}",
                    "text": part,
                    "metadata": {
                        "source": source_url,
                        "section": section,
                        "index": local_index,
                    },
                })
                global_index += 1
                position += len(part)

        return chunks

    @staticmethod
    def _detect_section(text: str, position: int) -> str:
        """Return the nearest Markdown heading that appears before *position*.

        Searches backwards from *position* for a line starting with one or more
        ``#`` characters.  Returns an empty string when no heading is found.
        """
        preceding = text[:position]
        # Find all markdown headings in the text before the position
        matches = list(re.finditer(r"^(#{1,6})\s+(.+)$", preceding, re.MULTILINE))
        if matches:
            return matches[-1].group(2).strip()
        return ""

    @staticmethod
    def _split_at_boundaries(text: str, max_chars: int) -> List[str]:
        """Split *text* into pieces of at most *max_chars* characters.

        Tries to break at paragraph boundaries (``\\n\\n``), then sentence
        boundaries (``. ``), falling back to a hard cut when neither is
        available within the allowed window.
        """
        if len(text) <= max_chars:
            return [text]

        parts: List[str] = []
        remaining = text
        while remaining:
            if len(remaining) <= max_chars:
                parts.append(remaining)
                break

            # Try paragraph boundary
            split_at = remaining.rfind("\n\n", 0, max_chars)
            if split_at != -1 and split_at >= max_chars // 2:
                split_at += 2  # include the delimiter
            else:
                # Try sentence boundary
                split_at = remaining.rfind(". ", 0, max_chars)
                if split_at != -1 and split_at >= max_chars // 2:
                    split_at += 2  # include the period and space
                else:
                    # Hard cut
                    split_at = max_chars

            parts.append(remaining[:split_at])
            remaining = remaining[split_at:]

        return parts
