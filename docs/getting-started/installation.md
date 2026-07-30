# Installation

## Requirements

- Python 3.8+
- One LLM provider API key (Google Gemini, OpenAI, or Anthropic) — **optional**; without a key you can still run [`raw` mode](../guides/output-formats.md#raw).

## Install from PyPI

```bash
pip install knowledge-base-builder
```

The core install is intentionally lean. It covers the most common sources out of the box:

- Web pages and sitemaps
- PDFs and documents (DOCX, TXT, MD, RTF)
- Structured web content (HTML, XML, JSON, YAML)
- GitHub repositories
- The default **Google Gemini** provider

## Optional extras

Heavier or less-common sources are opt-in, so you only install what you use:

```bash
pip install "knowledge-base-builder[spreadsheets]"   # CSV/TSV/XLSX/ODS (pandas)
pip install "knowledge-base-builder[youtube]"        # YouTube transcripts
pip install "knowledge-base-builder[rss]"            # RSS/Atom feeds
pip install "knowledge-base-builder[pptx]"           # PowerPoint
pip install "knowledge-base-builder[arxiv]"          # arXiv papers
pip install "knowledge-base-builder[openai]"         # OpenAI provider
pip install "knowledge-base-builder[anthropic]"      # Anthropic provider
pip install "knowledge-base-builder[all]"            # everything
```

Combine extras as needed: `pip install "knowledge-base-builder[youtube,arxiv]"`.

!!! tip "Missing an extra? You get a clear message, not a crash"
    If you try to process a source whose extra isn't installed, the error tells you
    exactly what to run — e.g. *"pandas is required for spreadsheet processing.
    Install with: `pip install 'knowledge-base-builder[spreadsheets]'`"*.

## Set your API key

Create a `.env` file (or export the variables) with at least one provider key:

```env
# You need only one of these
GOOGLE_API_KEY=your_key_here      # free tier at https://aistudio.google.com/app/apikey
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Optional: raises the GitHub API rate limit from 60 to 5000 requests/hour
GITHUB_API_KEY=your_token_here
```

The provider is auto-selected from whichever key is present (priority: **Gemini → OpenAI → Anthropic**).

## Development install

```bash
git clone https://github.com/kostadindev/knowledge-base-builder.git
cd knowledge-base-builder
pip install -e ".[all]"
pip install -r test-requirements.txt   # pytest, pytest-cov, mock
pytest
```

## Verify installation

```python
import knowledge_base_builder as kbb
print(kbb.__version__)
```
