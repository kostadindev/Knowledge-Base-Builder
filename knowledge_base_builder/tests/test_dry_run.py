"""Tests for Feature 7: Dry-Run Mode."""

import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from knowledge_base_builder.base_processor import BaseProcessor
from knowledge_base_builder.kb_builder import KBBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_builder():
    """Return a KBBuilder with a mocked LLM client (no real API key needed)."""
    with patch("knowledge_base_builder.gemini_client.ChatGoogleGenerativeAI"):
        builder = KBBuilder({"GOOGLE_API_KEY": "fake-key"})
    return builder


# ---------------------------------------------------------------------------
# BaseProcessor.check_accessible
# ---------------------------------------------------------------------------

class TestCheckAccessibleHTTP:
    """HTTP/HTTPS accessibility checks."""

    @patch("knowledge_base_builder.base_processor.requests.head")
    def test_check_accessible_http_success(self, mock_head):
        resp = MagicMock()
        resp.status_code = 200
        mock_head.return_value = resp

        ok, status, error = BaseProcessor.check_accessible("https://example.com/page")
        assert ok is True
        assert status == 200
        assert error is None
        mock_head.assert_called_once_with(
            "https://example.com/page", timeout=10, allow_redirects=True
        )

    @patch("knowledge_base_builder.base_processor.requests.head")
    def test_check_accessible_http_failure(self, mock_head):
        resp = MagicMock()
        resp.status_code = 404
        mock_head.return_value = resp

        ok, status, error = BaseProcessor.check_accessible("https://example.com/missing")
        assert ok is False
        assert status == 404
        assert error == "HTTP 404"

    @patch("knowledge_base_builder.base_processor.requests.head",
           side_effect=ConnectionError("refused"))
    def test_check_accessible_http_exception(self, mock_head):
        ok, status, error = BaseProcessor.check_accessible("https://example.com/down")
        assert ok is False
        assert status is None
        assert "refused" in error


class TestCheckAccessibleFile:
    """file:// accessibility checks."""

    def test_check_accessible_file_exists(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name
        try:
            url = f"file://{tmp_path}"
            ok, status, error = BaseProcessor.check_accessible(url)
            assert ok is True
            assert status is None
            assert error is None
        finally:
            os.unlink(tmp_path)

    def test_check_accessible_file_missing(self):
        url = "file:///nonexistent/path/to/file.pdf"
        ok, status, error = BaseProcessor.check_accessible(url)
        assert ok is False
        assert status is None
        assert error == "File not found"


# ---------------------------------------------------------------------------
# KBBuilder._classify_source
# ---------------------------------------------------------------------------

class TestClassifySource:
    def test_pdf(self):
        assert KBBuilder._classify_source("https://example.com/doc.pdf") == "pdf"

    def test_document_docx(self):
        assert KBBuilder._classify_source("https://example.com/notes.docx") == "document"

    def test_document_md(self):
        assert KBBuilder._classify_source("file:///tmp/readme.md") == "document"

    def test_spreadsheet(self):
        assert KBBuilder._classify_source("https://example.com/data.csv") == "spreadsheet"

    def test_web_content(self):
        assert KBBuilder._classify_source("https://example.com/page.html") == "web_content"

    def test_web_default(self):
        assert KBBuilder._classify_source("https://example.com/some-page") == "web"

    def test_query_string_ignored(self):
        assert KBBuilder._classify_source("https://example.com/doc.pdf?token=abc") == "pdf"


# ---------------------------------------------------------------------------
# KBBuilder._dry_run / build(dry_run=True)
# ---------------------------------------------------------------------------

class TestDryRun:
    """Integration-level dry-run tests."""

    @patch("knowledge_base_builder.base_processor.requests.head")
    @patch("knowledge_base_builder.gemini_client.ChatGoogleGenerativeAI")
    def test_dry_run_returns_dict(self, mock_gemini, mock_head):
        """dry_run=True must return a dict (not a file path)."""
        resp = MagicMock(); resp.status_code = 200
        mock_head.return_value = resp

        builder = _make_builder()
        builder.llm_client.run = MagicMock(return_value="OK")

        result = builder.build(
            sources={"files": ["https://example.com/doc.pdf"]},
            dry_run=True,
        )

        assert isinstance(result, dict)
        assert result["total_sources"] == 1
        assert result["accessible"] == 1
        assert result["inaccessible"] == 0
        assert "pdf" in result["sources_by_type"]
        assert result["api_key_valid"] is True
        assert "llm_provider" in result

    @patch("knowledge_base_builder.base_processor.requests.head")
    @patch("knowledge_base_builder.gemini_client.ChatGoogleGenerativeAI")
    def test_dry_run_no_file_written(self, mock_gemini, mock_head, tmp_path):
        """dry_run should never create the output file."""
        resp = MagicMock(); resp.status_code = 200
        mock_head.return_value = resp

        builder = _make_builder()
        builder.llm_client.run = MagicMock(return_value="OK")

        output_file = str(tmp_path / "should_not_exist.md")
        builder.build(
            sources={"files": ["https://example.com/page"]},
            output_file=output_file,
            dry_run=True,
        )

        assert not os.path.exists(output_file)

    @patch("knowledge_base_builder.base_processor.requests.head")
    @patch("knowledge_base_builder.gemini_client.ChatGoogleGenerativeAI")
    def test_dry_run_classifies_sources(self, mock_gemini, mock_head):
        """A mix of extensions should be classified correctly."""
        resp = MagicMock(); resp.status_code = 200
        mock_head.return_value = resp

        builder = _make_builder()
        builder.llm_client.run = MagicMock(return_value="OK")

        result = builder.build(
            sources={
                "files": [
                    "https://example.com/paper.pdf",
                    "https://example.com/notes.docx",
                    "https://example.com/about",
                ],
            },
            dry_run=True,
        )

        assert result["sources_by_type"].get("pdf") == 1
        assert result["sources_by_type"].get("document") == 1
        assert result["sources_by_type"].get("web") == 1

    @patch("knowledge_base_builder.base_processor.requests.head")
    @patch("knowledge_base_builder.gemini_client.ChatGoogleGenerativeAI")
    def test_dry_run_api_key_valid(self, mock_gemini, mock_head):
        """api_key_valid is True when the LLM call succeeds."""
        resp = MagicMock(); resp.status_code = 200
        mock_head.return_value = resp

        builder = _make_builder()
        builder.llm_client.run = MagicMock(return_value="OK")

        result = builder.build(
            sources={"files": ["https://example.com/a"]},
            dry_run=True,
        )
        assert result["api_key_valid"] is True

    @patch("knowledge_base_builder.base_processor.requests.head")
    @patch("knowledge_base_builder.gemini_client.ChatGoogleGenerativeAI")
    def test_dry_run_api_key_invalid(self, mock_gemini, mock_head):
        """api_key_valid is False when the LLM call raises."""
        resp = MagicMock(); resp.status_code = 200
        mock_head.return_value = resp

        builder = _make_builder()
        builder.llm_client.run = MagicMock(side_effect=RuntimeError("bad key"))

        result = builder.build(
            sources={"files": ["https://example.com/a"]},
            dry_run=True,
        )
        assert result["api_key_valid"] is False
