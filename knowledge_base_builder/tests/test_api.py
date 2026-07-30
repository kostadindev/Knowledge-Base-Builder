"""Tests for the one-line convenience API (knowledge_base_builder.api)."""

import os

from unittest.mock import patch

import knowledge_base_builder as kbb
from knowledge_base_builder.api import build, classify_sources, config_from_env


# ---------------------------------------------------------------------------
# classify_sources
# ---------------------------------------------------------------------------

class TestClassifySources:
    def test_github_shorthand(self):
        result = classify_sources(["torvalds/linux"])
        assert result["github_repositories"] == ["torvalds/linux"]
        assert result["files"] == []

    def test_github_url(self):
        result = classify_sources(["https://github.com/psf/requests"])
        assert result["github_repositories"] == ["https://github.com/psf/requests"]

    def test_sitemap(self):
        result = classify_sources(["https://example.com/sitemap.xml"])
        assert result["sitemap_url"] == "https://example.com/sitemap.xml"
        assert result["files"] == []

    def test_plain_url_is_a_file(self):
        result = classify_sources(["https://example.com/page"])
        assert result["files"] == ["https://example.com/page"]
        assert "github_repositories" not in result

    def test_local_path_is_a_file_not_github(self, tmp_path):
        p = tmp_path / "notes.md"
        p.write_text("hi")
        result = classify_sources([str(p)])
        assert str(p) in result["files"]
        assert "github_repositories" not in result

    def test_dotted_host_path_not_github(self):
        # example.com/page has a dot in the first segment -> not a repo
        result = classify_sources(["example.com/page"])
        assert result["files"] == ["example.com/page"]
        assert "github_repositories" not in result

    def test_mixed_bag(self):
        result = classify_sources([
            "user/repo",
            "https://example.com/doc.pdf",
            "https://site.com/sitemap.xml",
            "  ",  # blank ignored
        ])
        assert result["github_repositories"] == ["user/repo"]
        assert result["files"] == ["https://example.com/doc.pdf"]
        assert result["sitemap_url"] == "https://site.com/sitemap.xml"


# ---------------------------------------------------------------------------
# config_from_env
# ---------------------------------------------------------------------------

class TestConfigFromEnv:
    def test_reads_known_keys(self):
        env = {"OPENAI_API_KEY": "sk-x", "GITHUB_API_KEY": "gh-y"}
        with patch.dict(os.environ, env, clear=True):
            cfg = config_from_env()
        assert cfg == {"OPENAI_API_KEY": "sk-x", "GITHUB_API_KEY": "gh-y"}

    def test_ignores_empty(self):
        with patch.dict(os.environ, {"OPENAI_API_KEY": ""}, clear=True):
            cfg = config_from_env()
        assert "OPENAI_API_KEY" not in cfg


# ---------------------------------------------------------------------------
# build() convenience wrapper
# ---------------------------------------------------------------------------

class TestBuild:
    def test_exported_from_package(self):
        assert kbb.build is build

    def test_build_no_key_uses_raw_mode(self, tmp_path):
        """With no env keys, build() runs key-free and still produces output."""
        src = tmp_path / "doc.txt"
        src.write_text("End-to-end content via the one-liner.", encoding="utf-8")
        out = str(tmp_path / "kb.md")

        with patch.dict(os.environ, {}, clear=True):
            result = build(str(src), out=out)

        assert result == out
        with open(out, encoding="utf-8") as f:
            assert "End-to-end content" in f.read()

    def test_build_forwards_kwargs_and_routes_github(self, tmp_path):
        """build() should classify sources and forward kwargs to KBBuilder.build."""
        out = str(tmp_path / "kb.md")
        with patch("knowledge_base_builder.api.KBBuilder") as MockBuilder:
            instance = MockBuilder.return_value
            instance.build.return_value = out

            result = build(
                "user/repo",
                "https://example.com/a.pdf",
                out=out,
                config={"OPENAI_API_KEY": "sk-x"},
                output_format="markdown",
            )

        assert result == out
        # allow_no_llm should be False when a key is present
        _, kwargs = MockBuilder.call_args
        assert kwargs.get("allow_no_llm") is False
        # sources routed correctly
        _, build_kwargs = instance.build.call_args
        assert build_kwargs["sources"]["github_repositories"] == ["user/repo"]
        assert build_kwargs["sources"]["files"] == ["https://example.com/a.pdf"]
        assert build_kwargs["output_file"] == out
        assert build_kwargs["output_format"] == "markdown"
