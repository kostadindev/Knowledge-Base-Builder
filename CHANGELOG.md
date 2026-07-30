# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-07-30

### Added
- One-line convenience API: `kbb.build(*sources, out=...)` with automatic source routing
  (URLs, local paths, `user/repo` shorthand, sitemaps) plus `config_from_env` and
  `classify_sources` helpers.
- `raw` output format and opt-in no-LLM mode (`KBBuilder(config, allow_no_llm=True)`) — a
  knowledge base can now be produced with no API key.
- Optional-dependency extras (`spreadsheets`, `youtube`, `rss`, `pptx`, `arxiv`, `openai`,
  `anthropic`, `all`): the core install is now lean, and missing extras raise an actionable
  error instead of crashing.
- Transparent input validation: mistyped `sources` keys warn with a suggestion, wrong value
  types raise a clear `TypeError`, and each build logs a per-source success/failure summary.
- MkDocs Material documentation site with GitHub Pages deployment.

### Changed
- The package version is now single-sourced from `knowledge_base_builder.__version__`.

### Fixed
- Synchronous API is now safe to call from within a running event loop (Jupyter/Colab); the
  previous `asyncio.get_event_loop().run_until_complete` pattern raised `RuntimeError` there.

## [0.1.2] - 2026-03-21

### Added
- Multi-provider LLM support: Google Gemini, OpenAI GPT-4o, and Anthropic Claude.
- Knowledge base builder (`KBBuilder`) for generating structured markdown from external sources.
- Document processors for PDF, DOCX, Markdown, and RTF files.
- Spreadsheet processors for XLSX, CSV, and ODS files.
- Web content processor with YAML support.
- Website processor for crawling and extracting site content via BeautifulSoup.
- GitHub repository processor for ingesting repo content.
- CLI entry point (`knowledge-base-builder`) for command-line usage.
- Designed for RAG pipelines, SEO-friendly LLM contexts (`/llms.txt`), and chatbots.
