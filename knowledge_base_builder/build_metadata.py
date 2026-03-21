"""Build metadata tracking for knowledge base construction."""

import json
import re
import logging
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


class SourceResult:
    """Result of processing a single source."""

    def __init__(self, url: str, source_type: str):
        self.url = url
        self.source_type = source_type
        self.extraction_time_seconds: float = 0.0
        self.word_count: int = 0
        self.success: bool = False
        self.error_message: Optional[str] = None
        self.cache_hit: bool = False

    def to_dict(self) -> dict:
        d = {
            "url": self.url,
            "source_type": self.source_type,
            "extraction_time_seconds": round(self.extraction_time_seconds, 2),
            "word_count": self.word_count,
            "success": self.success,
        }
        if self.error_message:
            d["error"] = self.error_message
        if self.cache_hit:
            d["cache_hit"] = True
        return d


class BuildMetadata:
    """Accumulates metadata during a knowledge base build."""

    def __init__(self, llm_provider: str, llm_model: str, llm_temperature: float):
        self.build_timestamp = datetime.now(timezone.utc).isoformat()
        self.llm_provider = llm_provider
        self.llm_model = llm_model
        self.llm_temperature = llm_temperature
        self.sources: List[SourceResult] = []
        self.total_processing_time_seconds: float = 0.0
        self.output_word_count: int = 0
        self.output_section_count: int = 0

    def add_source(self, result: SourceResult) -> None:
        self.sources.append(result)

    def compute_output_stats(self, output_text: str) -> None:
        self.output_word_count = len(output_text.split())
        self.output_section_count = len(
            re.findall(r"^#{1,6}\s", output_text, re.MULTILINE)
        )

    def to_dict(self) -> dict:
        processed = [s.to_dict() for s in self.sources if s.success]
        failed = [s.to_dict() for s in self.sources if not s.success]
        return {
            "build_timestamp": self.build_timestamp,
            "llm_provider": self.llm_provider,
            "llm_model": self.llm_model,
            "llm_temperature": self.llm_temperature,
            "total_processing_time_seconds": round(
                self.total_processing_time_seconds, 2
            ),
            "sources_processed": processed,
            "sources_failed": failed,
            "output": {
                "word_count": self.output_word_count,
                "section_count": self.output_section_count,
            },
        }

    def write_json(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)
        logger.info("Build metadata written to: %s", path)
