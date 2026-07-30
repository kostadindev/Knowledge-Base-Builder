"""Tests for the OutputValidator and ValidationResult classes."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from knowledge_base_builder.validator import OutputValidator, ValidationResult
from knowledge_base_builder.build_metadata import SourceResult


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_source(success: bool = True, word_count: int = 100) -> SourceResult:
    """Create a SourceResult with the given attributes."""
    sr = SourceResult(url="https://example.com/doc", source_type="web")
    sr.success = success
    sr.word_count = word_count
    return sr


# ---------------------------------------------------------------------------
# ValidationResult.to_dict
# ---------------------------------------------------------------------------

class TestValidationResultToDict:
    def test_to_dict_keys(self):
        vr = ValidationResult()
        d = vr.to_dict()
        assert set(d.keys()) == {
            "is_non_empty",
            "has_headings",
            "heading_count",
            "source_coverage_pct",
            "output_word_count",
            "quality_score",
        }


# ---------------------------------------------------------------------------
# Non-empty checks
# ---------------------------------------------------------------------------

class TestNonEmpty:
    def test_non_empty_check(self):
        validator = OutputValidator()
        result = validator.validate("# Title\nSome content here.", [])
        assert result.is_non_empty is True

    def test_empty_check(self):
        validator = OutputValidator()
        result = validator.validate("", [])
        assert result.is_non_empty is False

    def test_whitespace_only_is_empty(self):
        validator = OutputValidator()
        result = validator.validate("   \n\t  ", [])
        assert result.is_non_empty is False


# ---------------------------------------------------------------------------
# Heading detection
# ---------------------------------------------------------------------------

class TestHeadings:
    def test_headings_detected(self):
        text = "# Heading 1\nSome text\n## Heading 2\nMore text\n### Heading 3"
        validator = OutputValidator()
        result = validator.validate(text, [])
        assert result.has_headings is True
        assert result.heading_count == 3

    def test_no_headings(self):
        text = "Just plain text with no markdown headings."
        validator = OutputValidator()
        result = validator.validate(text, [])
        assert result.has_headings is False
        assert result.heading_count == 0


# ---------------------------------------------------------------------------
# Source coverage
# ---------------------------------------------------------------------------

class TestSourceCoverage:
    def test_source_coverage_full(self):
        sources = [_make_source(success=True, word_count=50) for _ in range(5)]
        validator = OutputValidator()
        result = validator.validate("some text", sources)
        assert result.source_coverage_pct == 100.0

    def test_source_coverage_partial(self):
        sources = [
            _make_source(success=True, word_count=50),
            _make_source(success=False, word_count=0),
            _make_source(success=True, word_count=0),   # success but 0 words
            _make_source(success=True, word_count=30),
        ]
        validator = OutputValidator()
        result = validator.validate("some text", sources)
        # 2 out of 4 have success=True AND word_count > 0
        assert result.source_coverage_pct == 50.0

    def test_source_coverage_empty(self):
        validator = OutputValidator()
        result = validator.validate("some text", [])
        assert result.source_coverage_pct == 0.0


# ---------------------------------------------------------------------------
# Quality score
# ---------------------------------------------------------------------------

class TestQualityScore:
    def test_quality_score_perfect(self):
        """Non-empty + headings + 100% coverage + >=100 words = 1.0."""
        words = " ".join(["word"] * 100)
        text = f"# Heading\n{words}"
        sources = [_make_source(success=True, word_count=200)]
        validator = OutputValidator()
        result = validator.validate(text, sources)
        assert result.quality_score == 1.0

    def test_quality_score_zero(self):
        """Empty output with no sources = 0.0."""
        validator = OutputValidator()
        result = validator.validate("", [])
        assert result.quality_score == 0.0

    def test_quality_score_partial(self):
        """Non-empty text, no headings, partial coverage, few words."""
        text = "hello world"
        sources = [
            _make_source(success=True, word_count=10),
            _make_source(success=False, word_count=0),
        ]
        validator = OutputValidator()
        result = validator.validate(text, sources)

        # non-empty: 0.3
        # has_headings: 0.0
        # coverage 50%: 0.3 * 0.5 = 0.15
        # word_count 2/100: 0.2 * 0.02 = 0.004
        expected = round(0.3 + 0.0 + 0.15 + 0.004, 2)
        assert result.quality_score == expected


# ---------------------------------------------------------------------------
# Integration: validate flag wired into build metadata
# ---------------------------------------------------------------------------

class TestValidateIntegrationWithBuild:
    @patch("knowledge_base_builder.kb_builder.KBBuilder._process_legacy_sources")
    @patch("knowledge_base_builder.kb_builder.KBBuilder.process_files_async")
    def test_validate_integration_with_build(
        self, mock_process_files, mock_legacy, tmp_path
    ):
        """When validate=True, the metadata sidecar contains a 'validation' key."""
        # Create a KBBuilder with a mocked LLM client
        config = {"GOOGLE_API_KEY": "fake"}
        with patch("knowledge_base_builder.kb_builder.GeminiClient"):
            from knowledge_base_builder.kb_builder import KBBuilder

            builder = KBBuilder(config)

        output_file = str(tmp_path / "kb.md")

        # _process_legacy_sources is called after _build_meta is created
        # and after text_contents is reset.  We use the side effect to
        # inject content AND a source result so the build doesn't exit
        # early at the "No content collected" guard.
        def add_source_and_content(sources):
            builder.text_contents.append("# Title\nSome content about a topic.")
            sr = SourceResult(url="https://example.com", source_type="web")
            sr.success = True
            sr.word_count = 50
            builder._build_meta.add_source(sr)

        mock_legacy.side_effect = add_source_and_content

        # Mock the LLM so it returns text untouched
        async def fake_preprocess(text):
            return "# Title\nSome content about a topic."

        builder.llm = MagicMock()
        builder.llm.preprocess_text_async = fake_preprocess

        result = builder.build(
            sources={"files": []},
            output_file=output_file,
            validate=True,
            metadata=True,
        )

        # Check that the metadata file was written with a validation key
        meta_path = output_file + ".meta.json"
        assert os.path.exists(meta_path), "Metadata sidecar file should exist"

        with open(meta_path) as f:
            meta = json.load(f)

        assert "validation" in meta, "Metadata should contain 'validation' key"
        v = meta["validation"]
        assert "quality_score" in v
        assert "is_non_empty" in v
        assert v["is_non_empty"] is True
        assert v["quality_score"] > 0
