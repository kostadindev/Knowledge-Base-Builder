"""Tests for no-LLM / raw output mode."""

import os

import pytest
from unittest.mock import MagicMock, patch

from knowledge_base_builder.kb_builder import KBBuilder


def test_no_key_still_raises_by_default():
    """Backward-compat: KBBuilder({}) must raise without opt-in."""
    with pytest.raises(ValueError):
        KBBuilder({})


def test_allow_no_llm_constructs_without_client():
    builder = KBBuilder({}, allow_no_llm=True)
    assert builder.llm_client is None
    assert builder.llm is None


def test_invalid_output_format_rejected():
    builder = KBBuilder({}, allow_no_llm=True)
    with pytest.raises(ValueError, match="output_format"):
        builder.build(sources={"files": []}, output_format="bogus")


def _write_txt(tmp_path, name, content):
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_raw_output_without_key(tmp_path):
    src = _write_txt(tmp_path, "doc.txt", "Hello world. Structured content here.")
    builder = KBBuilder({}, allow_no_llm=True)
    out = str(tmp_path / "kb.md")

    result = builder.build(
        sources={"files": [src]}, output_file=out, output_format="raw"
    )

    assert result == out
    assert os.path.exists(out)
    with open(out, encoding="utf-8") as f:
        text = f.read()
    assert "Hello world" in text


def test_markdown_falls_back_to_raw_without_key(tmp_path):
    """Default output_format='markdown' with no key must not crash; falls back."""
    src = _write_txt(tmp_path, "doc.txt", "Fallback content preserved.")
    builder = KBBuilder({}, allow_no_llm=True)
    out = str(tmp_path / "kb.md")

    builder.build(sources={"files": [src]}, output_file=out)  # default markdown

    with open(out, encoding="utf-8") as f:
        assert "Fallback content preserved." in f.read()


def test_raw_output_with_key_does_not_call_llm(tmp_path):
    """output_format='raw' must skip the LLM even when a client exists."""
    src = _write_txt(tmp_path, "doc.txt", "Raw only, no LLM.")
    with patch("knowledge_base_builder.gemini_client.ChatGoogleGenerativeAI"):
        builder = KBBuilder({"GOOGLE_API_KEY": "fake"})

    builder.llm = MagicMock()
    out = str(tmp_path / "kb.md")

    builder.build(sources={"files": [src]}, output_file=out, output_format="raw")

    with open(out, encoding="utf-8") as f:
        assert "Raw only, no LLM." in f.read()
    builder.llm.preprocess_text_async.assert_not_called()


def test_raw_output_writes_metadata(tmp_path):
    src = _write_txt(tmp_path, "doc.txt", "Some words for the counter.")
    builder = KBBuilder({}, allow_no_llm=True)
    out = str(tmp_path / "kb.md")

    builder.build(sources={"files": [src]}, output_file=out, output_format="raw")

    assert os.path.exists(out + ".meta.json")
