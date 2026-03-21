# Knowledge Base Builder

<p align="center">
  <img src="https://kostadindev.github.io/images/kbb.svg" alt="Knowledge Base Builder" width="100%">
</p>

<p align="center">
  <a href="https://pypi.org/project/knowledge-base-builder/"><img src="https://img.shields.io/pypi/v/knowledge-base-builder" alt="PyPI"></a>
  <a href="https://github.com/kostadindev/knowledge-base-builder/actions/workflows/tests.yml"><img src="https://github.com/kostadindev/knowledge-base-builder/actions/workflows/tests.yml/badge.svg" alt="Tests"></a>
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
</p>

A Python package that transforms diverse content sources into structured Markdown knowledge bases using large language models. Ingest web pages, PDFs, spreadsheets, GitHub repositories, YouTube videos, arXiv papers, RSS feeds, Jupyter notebooks, PowerPoint presentations, and sitemaps — then consolidate them into a single organized document.

Built to power:
- Web-crawlable LLM context files (`/llms.txt`)
- Retrieval-Augmented Generation (RAG) preprocessing
- Vector database ingestion pipelines
- Domain-specific chatbots and assistants

> **[Read the full report with interactive visualizations](paper/report.html)**

---

## Installation

```bash
pip install knowledge-base-builder
```

Or install from source for development:

```bash
git clone https://github.com/kostadindev/knowledge-base-builder.git
cd knowledge-base-builder
pip install -e .
```

---

## Quickstart

### 1. Set up your API key

Create a `.env` file with at least one LLM provider key:

```env
# You need only one of the following
GOOGLE_API_KEY=your_key_here      # Free at https://aistudio.google.com/app/apikey
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Optional: increases GitHub API rate limit from 60 to 5000 requests/hour
GITHUB_API_KEY=your_token_here
```

### 2. Build a knowledge base

```python
import os
from dotenv import load_dotenv
from knowledge_base_builder import KBBuilder

load_dotenv()

config = {
    'OPENAI_API_KEY': os.getenv("OPENAI_API_KEY"),
}

sources = {
    'files': [
        "https://example.com/resume.pdf",
        "https://example.com/index.html",
        "path/to/local/document.docx",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",   # YouTube transcript
        "https://arxiv.org/abs/2301.12345",            # arXiv paper
        "path/to/notebook.ipynb",                      # Jupyter notebook
        "path/to/slides.pptx",                         # PowerPoint
    ],
    'sitemap_url': "https://example.com/sitemap.xml",
    'github_repositories': [
        "username/repo",
        "https://github.com/username/another-repo",
    ],
    'rss_urls': ["https://blog.example.com/feed"],     # RSS/Atom feeds
}

kbb = KBBuilder(config)
kbb.build(sources=sources, output_file="knowledge_base.md")
```

### 3. Or use the CLI

```bash
knowledge-base-builder \
  --openai-api-key $OPENAI_API_KEY \
  -f https://example.com/resume.pdf \
  -f https://example.com/index.html \
  -m https://example.com/sitemap.xml \
  -g username/repo \
  -o knowledge_base.md
```

---

## Supported Sources

| Source Type | Description | Formats / Detection |
|-------------|-------------|---------------------|
| Documents | Text documents | PDF, DOCX, TXT, MD, RTF |
| Spreadsheets | Tabular data | CSV, TSV, XLSX, ODS |
| Web Content | Structured web data | HTML, XML, JSON, YAML/YML |
| Websites | Live web pages | Any URL or sitemap |
| GitHub | Repository markdown files | `user/repo` or GitHub URLs |
| YouTube | Video transcripts | `youtube.com` / `youtu.be` URLs (auto-detected) |
| arXiv | Research papers (PDF + metadata) | `arxiv.org` URLs or bare IDs like `2301.12345` |
| RSS/Atom | Blog and news feeds | URLs with `/feed`, `/rss`, `.atom`; or `--rss` flag |
| Jupyter | Notebooks (code + markdown + outputs) | `.ipynb` files |
| PowerPoint | Presentation slides + speaker notes | `.pptx` files |

All source types can be mixed in a single `build()` call. YouTube, arXiv, and RSS URLs are auto-detected by URL pattern. File-based sources (Jupyter, PPTX) are auto-detected by extension. Duplicate URLs are automatically skipped.

---

## LLM Providers

| Provider | Default Model | Notes |
|----------|--------------|-------|
| Google Gemini | `gemini-2.0-flash` | Free tier available, large context window |
| OpenAI | `gpt-4o` | High-quality summaries |
| Anthropic | `claude-3-7-sonnet` | Excellent formatting |

The provider is auto-selected based on which API key is present (priority: Gemini > OpenAI > Anthropic). To override the model or temperature:

```python
config = {
    'OPENAI_API_KEY': os.getenv("OPENAI_API_KEY"),
    'OPENAI_MODEL': 'gpt-4o-mini',
    'OPENAI_TEMPERATURE': 0.3,
    'OPENAI_MAX_CONCURRENCY': 4,
}
```

---

## API Reference

### `KBBuilder(config)`

Initialize a knowledge base builder with provider configuration.

**Parameters:**
- `config` (dict): Configuration dictionary. Required keys depend on provider:
  - `GOOGLE_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` (at least one required)
  - `{PROVIDER}_MODEL` (optional, string)
  - `{PROVIDER}_TEMPERATURE` (optional, float 0.0-1.0, default 0.7)
  - `{PROVIDER}_MAX_RETRIES` (optional, int, default 3)
  - `{PROVIDER}_MAX_CONCURRENCY` (optional, int, default 8)
  - `GITHUB_API_KEY` (optional, for higher GitHub rate limits)

**Raises:** `ValueError` if no API key is provided.

### `kbb.build(sources, output_file, **kwargs)`

Build a knowledge base from the provided sources.

**Parameters:**
- `sources` (dict): Source specification with keys:
  - `files` (list[str]): URLs or local paths — auto-detected by extension or URL pattern. Supports PDF, DOCX, TXT, MD, RTF, CSV, XLSX, HTML, JSON, YAML, IPYNB, PPTX, YouTube URLs, arXiv URLs/IDs, and plain web URLs.
  - `sitemap_url` (str): URL of a sitemap.xml to crawl
  - `github_repositories` (list[str]): GitHub repos as `"user/repo"` or full URLs
  - `github_username` (str): Process all repos for a GitHub user
  - `rss_urls` (list[str]): RSS/Atom feed URLs
- `output_file` (str): Output path (default: `"final_knowledge_base.md"`)
- `output_format` (str): `"markdown"` (default), `"llms_txt"`, or `"chunks"`
- `project_name` (str, optional): Project name for the H1 heading in `llms_txt` mode
- `on_progress` (callable, optional): Callback `(stage, current, total)`
- `metadata` (bool): Write a `.meta.json` sidecar file (default `True`)
- `validate` (bool): Run output quality checks, include results in metadata (default `False`)
- `incremental` (bool): Cache extracted text, skip unchanged sources on rebuild (default `False`)
- `cache_dir` (str, optional): Cache directory (default `.kbb_cache`)
- `dry_run` (bool): Validate sources and API key without processing (default `False`)
- `chunk_size` (int): Max characters per chunk in `"chunks"` mode (default `1000`)

**Returns:** The output file path, or a summary dict when `dry_run=True`.

```python
kbb.build(
    sources=sources,
    output_file="kb.md",
    output_format="llms_txt",       # Generate llms.txt spec output
    project_name="My Project",
    incremental=True,                # Skip unchanged sources on rebuild
    on_progress=lambda s, c, t: print(f"{s}: {c}/{t}"),
)
```

---

## Architecture

The pipeline has three phases:

```
Sources (PDF, HTML, GitHub, YouTube, arXiv, RSS, Jupyter, PPTX, ...)
    |
    v
[1] Text Extraction (concurrent, async)
    - 11 specialized processors (auto-detected by URL pattern or file extension)
    - Downloads and extraction run in thread pools
    - Semaphore limits concurrency (default: 8)
    - Automatic retry with backoff on transient failures
    - Duplicate URLs skipped
    |
    v
[2] Text Merging
    - Extracted texts joined with document separators
    - Split into chunks at paragraph/sentence boundaries
    - No LLM calls in this phase
    |
    v
[3] LLM Summarization
    - Each chunk processed by the configured LLM
    - Structured prompt requests hierarchical Markdown with headings, bullets, and preserved details
    - Retry with exponential backoff on API failures
    - Sub-chunk fallback if a chunk fails
    |
    v
Output: Structured Markdown knowledge base
```

---

## `/llms.txt` Output Mode

Generate output conforming to the [llmstxt.org](https://llmstxt.org) specification — a Markdown file designed to help LLMs understand and navigate your content.

```python
kbb.build(
    sources=sources,
    output_file="llms.txt",
    output_format="llms_txt",
    project_name="My Project",
)
```

This produces two files:
- **`llms.txt`** — structured navigation file with H1 heading, blockquote summary, and H2 sections with linked resources
- **`llms-full.txt`** — complete extracted text from all sources (pre-LLM processing)

CLI: `knowledge-base-builder --output-format llms_txt --project-name "My Project" -o llms.txt`

---

## Metadata Sidecar

Every build produces a `.meta.json` companion file with build provenance:

```json
{
  "build_timestamp": "2026-03-21T16:30:00+00:00",
  "llm_provider": "OpenAIClient",
  "llm_model": "gpt-4o",
  "sources_processed": [
    {"url": "https://example.com/page", "source_type": "web", "word_count": 450, "success": true}
  ],
  "sources_failed": [],
  "output": {"word_count": 320, "section_count": 5}
}
```

This enables RAG attribution (tracking which source contributed which content) and build auditing. Suppress with `metadata=False` or `--no-metadata`.

---

## Incremental Builds

For sources that don't change often, enable incremental mode to cache extracted text and skip re-processing unchanged sources:

```python
kbb.build(sources=sources, output_file="kb.md", incremental=True)
```

The cache is stored in `.kbb_cache/` (configurable via `cache_dir`). On each build:
1. Each source is downloaded and its content hashed (SHA-256)
2. If the hash matches the cache, the cached extracted text is reused
3. The LLM summarization step always re-runs (prompts may change)

This is useful for scheduled rebuilds (e.g., keeping `/llms.txt` up to date) where most sources are unchanged between runs.

CLI: `knowledge-base-builder --incremental --cache-dir .kbb_cache`

---

## Chunked Output for Vector DBs

Produce a JSON array of text chunks ready for direct ingestion into vector databases (Pinecone, Chroma, Weaviate). This mode skips LLM processing entirely — no API key costs.

```python
kbb.build(
    sources=sources,
    output_file="chunks.json",
    output_format="chunks",
    chunk_size=500,  # characters per chunk
)
```

Output format:
```json
[
  {"id": "chunk_0", "text": "...", "metadata": {"source": "https://example.com/doc.pdf", "section": "Introduction", "index": 0}},
  {"id": "chunk_1", "text": "...", "metadata": {"source": "https://example.com/doc.pdf", "section": "Methods", "index": 1}}
]
```

CLI: `knowledge-base-builder --output-format chunks --chunk-size 500 -o chunks.json`

---

## Output Quality Validation

Run automated quality checks after building:

```python
kbb.build(sources=sources, output_file="kb.md", validate=True)
```

Checks include: non-empty output, Markdown heading structure, percentage of input sources that contributed content. Results are recorded in the `.meta.json` sidecar:

```json
{
  "validation": {
    "is_non_empty": true,
    "has_headings": true,
    "heading_count": 12,
    "source_coverage_pct": 85.0,
    "quality_score": 0.92
  }
}
```

CLI: `knowledge-base-builder --validate`

---

## Dry-Run Mode

Validate your configuration and check source accessibility without processing anything:

```python
summary = kbb.build(sources=sources, dry_run=True)
print(summary)
# {"total_sources": 8, "accessible": 7, "inaccessible": 1, "api_key_valid": true, ...}
```

CLI: `knowledge-base-builder --dry-run --google-api-key $KEY -f url1 -f url2 -g user/repo`

---

## Enhanced Document Extraction (Optional)

Install [MarkItDown](https://github.com/microsoft/markitdown) for higher-fidelity extraction of PDFs, DOCX, and XLSX files (preserves tables, code blocks, and formatting):

```bash
pip install knowledge-base-builder[markitdown]
```

When installed, MarkItDown is automatically used as the extraction backend. PyPDF/python-docx remain as fallbacks when MarkItDown is not installed.

---

## Configuration Reference

All configuration options can be passed via the `config` dictionary or as CLI arguments:

| Config Key | CLI Flag | Default | Description |
|------------|----------|---------|-------------|
| `GOOGLE_API_KEY` | `--google-api-key` | - | Google Gemini API key |
| `OPENAI_API_KEY` | `--openai-api-key` | - | OpenAI API key |
| `ANTHROPIC_API_KEY` | `--anthropic-api-key` | - | Anthropic API key |
| `{PROVIDER}_MODEL` | `--{provider}-model` | See table above | LLM model name |
| `{PROVIDER}_TEMPERATURE` | `--{provider}-temperature` | `0.7` | Sampling temperature (0.0=deterministic, 1.0=creative) |
| `{PROVIDER}_MAX_RETRIES` | - | `3` | Max retry attempts for LLM calls |
| `{PROVIDER}_MAX_CONCURRENCY` | - | `8` | Max concurrent LLM requests |
| `GITHUB_API_KEY` | `--github-api-key` | - | GitHub token for higher rate limits |

---

## Logging

The package uses Python's `logging` module instead of print statements. Configure logging in your application:

```python
import logging

# See all pipeline activity
logging.basicConfig(level=logging.INFO)

# See detailed timing and debug info
logging.basicConfig(level=logging.DEBUG)

# Suppress library output
logging.getLogger('knowledge_base_builder').setLevel(logging.WARNING)
```

The CLI configures `INFO`-level logging by default.

---

## Applications

### `/llms.txt` — Web-Crawlable LLM Context
Generate a compact Markdown file that search-powered LLMs (Perplexity, ChatGPT, Gemini) can discover and reference when answering questions about you or your organization.

### RAG Preprocessing
Produce clean, structured Markdown ready for embedding into vector stores (Pinecone, Chroma, Weaviate) or for use as direct LLM context within a single context window.

### Multi-Source Summarization
Consolidate a website (via sitemap), a PDF portfolio, and multiple GitHub repositories into one organized document.

```python
sources = {
    'sitemap_url': "https://example.com/sitemap.xml",
    'github_repositories': ["user/repo1", "user/repo2"],
    'files': ["resume.pdf", "cover_letter.docx"],
}
```

---

## Limitations

- **Output length saturation**: Because the final output is produced by a single LLM call per chunk, adding more sources beyond 4-5 increases compression rather than output length. For very large corpora, consider splitting into multiple builds.
- **GitHub rate limits**: Without a `GITHUB_API_KEY`, the GitHub API allows only 60 requests/hour. The package logs warnings when rate limits are hit but continues with available data. Always provide a token for GitHub-heavy builds.
- **Memory**: All extracted text is held in memory before LLM processing. For hundreds of large documents, monitor memory usage.
- **LLM context windows**: Chunks exceeding the model's context window will fail. The default chunk size (80K characters / ~20K tokens) is safe for all supported models.

---

## Development

### Running Tests

```bash
pip install -e .
pip install -r test-requirements.txt
pytest --cov=knowledge_base_builder --cov-report=term-missing
```

The test suite includes 260 tests with 95% code coverage. CI runs on Python 3.9, 3.10, and 3.11.

### Project Structure

```
knowledge_base_builder/
  __init__.py              # Package exports
  kb_builder.py            # Main KBBuilder class and pipeline orchestration
  llm.py                   # LLM prompt construction and KB merging
  llm_client.py            # Abstract LLM client base class
  gemini_client.py         # Google Gemini implementation
  openai_client.py         # OpenAI implementation
  anthropic_client.py      # Anthropic Claude implementation
  base_processor.py        # Base class for file processors
  pdf_processor.py         # PDF text extraction
  document_processor.py    # DOCX, TXT, MD, RTF extraction
  spreadsheet_processor.py # CSV, TSV, XLSX, ODS extraction
  web_content_processor.py # HTML, XML, JSON, YAML extraction
  website_processor.py     # Sitemap parsing and HTML crawling
  github_processor.py      # GitHub API integration
  youtube_processor.py     # YouTube transcript extraction
  rss_processor.py         # RSS/Atom feed parsing
  jupyter_processor.py     # Jupyter notebook extraction
  presentation_processor.py # PowerPoint slide extraction
  arxiv_processor.py       # arXiv paper download + metadata
  build_metadata.py        # Build metadata and source tracking
  cache.py                 # Incremental build cache
  chunker.py               # Text chunking for vector DB output
  validator.py             # Output quality validation
  cli.py                   # Command-line interface
  tests/                   # Test suite (260 tests, 95% coverage)
paper/
  paper.md                 # JOSS paper manuscript
  paper.bib                # References
  report.html              # Interactive report with experiment visualizations
experiments/               # Reproducible evaluation experiments
```

---

## Citing

If you use this package in your research, please cite:

```bibtex
@article{devedzhiev2026kbb,
  title = {Knowledge Base Builder: A Python Package for Multi-Source Knowledge Base Construction with Large Language Models},
  author = {Devedzhiev, Kostadin},
  journal = {Journal of Open Source Software},
  year = {2026}
}
```

---

## Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. This project follows the [Contributor Covenant Code of Conduct](CODE_OF_CONDUCT.md).

- **Bug reports**: [Open an issue](https://github.com/kostadindev/knowledge-base-builder/issues/new?template=bug_report.md)
- **Feature requests**: [Open an issue](https://github.com/kostadindev/knowledge-base-builder/issues/new?template=feature_request.md)
- **Questions**: [Open a discussion](https://github.com/kostadindev/knowledge-base-builder/issues)

---

## License

MIT License. See [LICENSE](LICENSE) for details.
