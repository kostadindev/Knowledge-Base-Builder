"""Output quality validation for knowledge base builds."""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ValidationResult:
    """Result of validating a knowledge base output."""

    def __init__(self):
        self.is_non_empty: bool = False
        self.has_headings: bool = False
        self.heading_count: int = 0
        self.source_coverage_pct: float = 0.0
        self.output_word_count: int = 0
        self.quality_score: float = 0.0

    def to_dict(self) -> dict:
        return {
            "is_non_empty": self.is_non_empty,
            "has_headings": self.has_headings,
            "heading_count": self.heading_count,
            "source_coverage_pct": round(self.source_coverage_pct, 2),
            "output_word_count": self.output_word_count,
            "quality_score": self.quality_score,
        }


class OutputValidator:
    """Validates the quality of knowledge base output."""

    def validate(self, output_text: str, source_results: list) -> ValidationResult:
        """Validate output text quality against source results.

        Args:
            output_text: The generated knowledge base text.
            source_results: List of ``SourceResult`` objects from the build.

        Returns:
            A ``ValidationResult`` with quality metrics.
        """
        result = ValidationResult()
        result.is_non_empty = bool(output_text.strip())
        result.output_word_count = len(output_text.split())

        headings = re.findall(r'^#{1,6}\s', output_text, re.MULTILINE)
        result.has_headings = len(headings) > 0
        result.heading_count = len(headings)

        total = len(source_results)
        successful = sum(1 for s in source_results if s.success and s.word_count > 0)
        result.source_coverage_pct = (successful / total * 100) if total else 0.0

        # Quality score (0.0 - 1.0)
        score = 0.0
        score += 0.3 if result.is_non_empty else 0.0
        score += 0.2 if result.has_headings else 0.0
        score += 0.3 * (result.source_coverage_pct / 100.0)
        score += 0.2 * min(result.output_word_count / 100, 1.0)
        result.quality_score = round(score, 2)

        return result
