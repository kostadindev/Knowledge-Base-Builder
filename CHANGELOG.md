# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
