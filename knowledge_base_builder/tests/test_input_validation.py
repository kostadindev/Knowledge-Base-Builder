"""Tests for transparent handling of misentered input."""

import logging

import pytest

import knowledge_base_builder as kbb
from knowledge_base_builder.kb_builder import KBBuilder


def _builder():
    return KBBuilder({}, allow_no_llm=True)


# ---------------------------------------------------------------------------
# KBBuilder.build source-argument validation
# ---------------------------------------------------------------------------

class TestSourcesValidation:
    def test_non_dict_sources_raises(self):
        with pytest.raises(TypeError, match="sources must be a dict"):
            _builder().build(sources="https://example.com")

    def test_list_key_given_string_raises_with_wrap_hint(self):
        with pytest.raises(TypeError, match=r"must be a list of strings.*Wrap it in a list"):
            _builder().build(sources={"files": "https://example.com/doc.pdf"})

    def test_list_key_with_non_string_item_raises(self):
        with pytest.raises(TypeError, match="must contain only strings"):
            _builder().build(sources={"files": ["ok.pdf", 123]})

    def test_str_key_given_list_raises(self):
        with pytest.raises(TypeError, match="must be a single string"):
            _builder().build(sources={"sitemap_url": ["https://example.com/sitemap.xml"]})

    def test_unknown_key_warns_with_suggestion(self, caplog, tmp_path):
        src = tmp_path / "a.txt"
        src.write_text("content", encoding="utf-8")
        out = str(tmp_path / "kb.md")
        with caplog.at_level(logging.WARNING):
            # 'file' is a typo for 'files' -> should warn and be ignored, not crash
            _builder().build(sources={"file": [str(src)]}, output_file=out)
        msgs = " ".join(r.message for r in caplog.records)
        assert "unrecognized sources key 'file'" in msgs
        assert "Did you mean 'files'?" in msgs

    def test_valid_legacy_keys_do_not_warn(self, caplog):
        with caplog.at_level(logging.WARNING):
            _builder().build(sources={"pdf_urls": [], "web_urls": []},
                             output_file="/dev/null", metadata=False)
        assert "unrecognized sources key" not in " ".join(r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Build summary and empty-content messaging
# ---------------------------------------------------------------------------

class TestBuildTransparency:
    def test_failed_source_is_reported(self, caplog, tmp_path):
        out = str(tmp_path / "kb.md")
        with caplog.at_level(logging.WARNING):
            _builder().build(
                sources={"files": ["/definitely/not/here.pdf"]},
                output_file=out,
                metadata=False,
            )
        text = " ".join(r.message for r in caplog.records)
        assert "Failed [pdf]" in text
        assert "all 1 source(s) failed" in text

    def test_no_sources_message(self, caplog, tmp_path):
        out = str(tmp_path / "kb.md")
        with caplog.at_level(logging.WARNING):
            _builder().build(sources={}, output_file=out, metadata=False)
        assert "no sources were provided" in " ".join(r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# Convenience build() argument validation
# ---------------------------------------------------------------------------

class TestConvenienceValidation:
    def test_no_sources_raises(self):
        with pytest.raises(ValueError, match="requires at least one source"):
            kbb.build(out="kb.md")

    def test_list_argument_raises_with_unpack_hint(self, tmp_path):
        with pytest.raises(TypeError, match="unpack it"):
            kbb.build(["a.pdf", "b.pdf"], out=str(tmp_path / "kb.md"))

    def test_non_string_argument_raises(self, tmp_path):
        with pytest.raises(TypeError, match="must be a string"):
            kbb.build(123, out=str(tmp_path / "kb.md"))
