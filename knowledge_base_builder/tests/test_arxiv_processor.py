"""Tests for ArxivProcessor — URL detection, ID extraction, download + metadata, PDF extraction."""

import json
import os
import tempfile
import asyncio
import pytest
from unittest.mock import patch, MagicMock
from knowledge_base_builder.arxiv_processor import ArxivProcessor


# ---------------------------------------------------------------------------
# URL detection (pure logic)
# ---------------------------------------------------------------------------
class TestIsArxivUrl:
    @pytest.mark.parametrize("url", [
        "https://arxiv.org/abs/2301.12345",
        "https://arxiv.org/pdf/2301.12345",
        "https://arxiv.org/abs/2301.12345v2",
        "http://arxiv.org/abs/2301.12345",
        "2301.12345",
        "2301.12345v2",
        "2405.0001",
    ])
    def test_valid_arxiv_urls(self, url):
        assert ArxivProcessor.is_arxiv_url(url) is True

    @pytest.mark.parametrize("url", [
        "https://example.com/paper",
        "not-an-id",
        "https://google.com",
        "",
        "12345",  # Not enough digits
    ])
    def test_non_arxiv_urls(self, url):
        assert ArxivProcessor.is_arxiv_url(url) is False


# ---------------------------------------------------------------------------
# ID extraction (pure logic)
# ---------------------------------------------------------------------------
class TestExtractArxivId:
    def test_from_abs_url(self):
        assert ArxivProcessor.extract_arxiv_id("https://arxiv.org/abs/2301.12345") == "2301.12345"

    def test_from_pdf_url_with_version(self):
        assert ArxivProcessor.extract_arxiv_id("https://arxiv.org/pdf/2301.12345v2") == "2301.12345v2"

    def test_from_bare_id(self):
        assert ArxivProcessor.extract_arxiv_id("2301.12345") == "2301.12345"

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="Could not extract arXiv ID"):
            ArxivProcessor.extract_arxiv_id("https://example.com/page")


# ---------------------------------------------------------------------------
# Download (mocked arxiv library)
# ---------------------------------------------------------------------------
class TestDownload:
    @patch("knowledge_base_builder.arxiv_processor._ARXIV_AVAILABLE", True)
    @patch("knowledge_base_builder.arxiv_processor.arxiv")
    def test_download_fetches_pdf_and_writes_metadata(self, mock_arxiv):
        """Verify download creates PDF + sidecar metadata JSON."""
        mock_paper = MagicMock()
        mock_paper.title = "Attention Is All You Need"
        mock_paper.authors = [MagicMock(__str__=lambda s: "Author A"), MagicMock(__str__=lambda s: "Author B")]
        mock_paper.summary = "We propose the Transformer architecture."
        mock_paper.published = "2017-06-12"
        mock_paper.categories = ["cs.CL", "cs.AI"]

        # download_pdf should return a path
        tmp_dir = tempfile.mkdtemp()
        pdf_path = os.path.join(tmp_dir, "2301.12345v1.pdf")
        with open(pdf_path, "wb") as f:
            f.write(b"fake pdf")
        mock_paper.download_pdf.return_value = pdf_path

        mock_client = MagicMock()
        mock_client.results.return_value = iter([mock_paper])
        mock_arxiv.Client.return_value = mock_client
        mock_arxiv.Search.return_value = "search_obj"

        result = ArxivProcessor.download("https://arxiv.org/abs/2301.12345")

        assert result == pdf_path
        assert os.path.exists(result)

        # Verify metadata sidecar
        meta_path = result + ".meta.json"
        assert os.path.exists(meta_path)
        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["title"] == "Attention Is All You Need"
        assert "Author A" in meta["authors"]
        assert meta["arxiv_id"] == "2301.12345"
        assert "cs.CL" in meta["categories"]

        # Cleanup
        os.unlink(pdf_path)
        os.unlink(meta_path)
        os.rmdir(tmp_dir)

    @patch("knowledge_base_builder.arxiv_processor._ARXIV_AVAILABLE", False)
    def test_download_library_not_installed(self):
        with pytest.raises(ImportError, match="arxiv is required"):
            ArxivProcessor.download("https://arxiv.org/abs/2301.12345")


# ---------------------------------------------------------------------------
# Text extraction (real files + mocked PDF extraction)
# ---------------------------------------------------------------------------
class TestExtractText:
    @patch("knowledge_base_builder.pdf_processor.PDFProcessor.extract_text")
    def test_extract_with_metadata_sidecar(self, mock_pdf):
        """Verify metadata header is prepended to PDF text."""
        mock_pdf.return_value = "This is the full paper text about transformers."

        tmp_dir = tempfile.mkdtemp()
        pdf_path = os.path.join(tmp_dir, "paper.pdf")
        with open(pdf_path, "w") as f:
            f.write("fake")

        meta = {
            "title": "Attention Is All You Need",
            "authors": ["Vaswani", "Shazeer", "Parmar"],
            "abstract": "The dominant sequence transduction models are based on complex recurrent architectures.",
            "published": "2017-06-12",
            "categories": ["cs.CL", "cs.AI"],
            "arxiv_id": "1706.03762",
        }
        with open(pdf_path + ".meta.json", "w") as f:
            json.dump(meta, f)

        result = ArxivProcessor.extract_text(pdf_path)

        assert "# Attention Is All You Need" in result
        assert "**Authors:** Vaswani, Shazeer, Parmar" in result
        assert "**Published:** 2017-06-12" in result
        assert "**Categories:** cs.CL, cs.AI" in result
        assert "## Abstract" in result
        assert "dominant sequence transduction" in result
        assert "## Full Text" in result
        assert "full paper text about transformers" in result

        # Cleanup
        os.unlink(pdf_path)
        os.unlink(pdf_path + ".meta.json")
        os.rmdir(tmp_dir)

    @patch("knowledge_base_builder.pdf_processor.PDFProcessor.extract_text")
    def test_extract_without_metadata_sidecar(self, mock_pdf):
        """No sidecar — should still extract PDF text without header."""
        mock_pdf.return_value = "Raw PDF content."

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
            f.write(b"fake")
            path = f.name

        try:
            result = ArxivProcessor.extract_text(path)
            assert result == "Raw PDF content."
            assert "# " not in result  # No metadata header
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Integration: routing
# ---------------------------------------------------------------------------
class TestArxivRouting:
    @patch("knowledge_base_builder.kb_builder.GeminiClient")
    def test_arxiv_url_routed_to_arxiv_processor(self, mock_gemini):
        from knowledge_base_builder.kb_builder import KBBuilder
        kbb = KBBuilder({"GOOGLE_API_KEY": "fake"})
        from knowledge_base_builder.build_metadata import BuildMetadata
        kbb._build_meta = BuildMetadata("test", "test", 0.7)
        kbb._cache = None
        kbb._text_sources = []
        kbb.arxiv_processor = MagicMock()
        kbb.arxiv_processor.download.return_value = "/tmp/fake.pdf"
        kbb.arxiv_processor.extract_text.return_value = "# Paper\n\nContent"

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(kbb.process_files_async([
                "https://arxiv.org/abs/2301.12345",
            ]))
        finally:
            loop.close()

        kbb.arxiv_processor.download.assert_called_once()
        kbb.arxiv_processor.extract_text.assert_called_once()

    @patch("knowledge_base_builder.kb_builder.GeminiClient")
    def test_bare_arxiv_id_routed(self, mock_gemini):
        from knowledge_base_builder.kb_builder import KBBuilder
        kbb = KBBuilder({"GOOGLE_API_KEY": "fake"})
        from knowledge_base_builder.build_metadata import BuildMetadata
        kbb._build_meta = BuildMetadata("test", "test", 0.7)
        kbb._cache = None
        kbb._text_sources = []
        kbb.arxiv_processor = MagicMock()
        kbb.arxiv_processor.download.return_value = "/tmp/fake.pdf"
        kbb.arxiv_processor.extract_text.return_value = "text"

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(kbb.process_files_async(["2301.12345"]))
        finally:
            loop.close()

        kbb.arxiv_processor.download.assert_called_once()
