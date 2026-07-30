# Quickstart

## The one-liner

The fastest way in. Pass any mix of sources as positional arguments — each is auto-routed to the right extractor.

```python
import knowledge_base_builder as kbb

kbb.build(
    "https://arxiv.org/abs/2301.12345",   # arXiv paper
    "octocat/Hello-World",                # GitHub repo (user/repo)
    "notes.pdf",                          # local file
    out="kb.md",
)
```

API keys are read from the environment (`GOOGLE_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`). The result is written to `out` and its path is returned.

## Try it with no API key

No key yet? `build()` falls back to **raw mode** — it extracts and concatenates the source text without any LLM call, so you always get a result on the very first run.

```python
import knowledge_base_builder as kbb

kbb.build("https://example.com", out="kb.md")   # zero configuration
```

Add a key when you want LLM-structured Markdown (the default). A free Gemini key is available at [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey).

## Choose an output format

```python
kbb.build("https://mysite.com", out="llms.txt", output_format="llms_txt")            # /llms.txt spec
kbb.build("guide.pdf", "https://mysite.com/faq", out="chunks.json", output_format="chunks")  # vector-DB JSON
kbb.build("https://mysite.com", out="raw.md", output_format="raw")                   # no LLM
```

See [Output Formats](../guides/output-formats.md) for all four.

## Full control with `KBBuilder`

For advanced pipelines, use the `KBBuilder` class with an explicit config and grouped sources.

```python
import os
from dotenv import load_dotenv
from knowledge_base_builder import KBBuilder

load_dotenv()

config = {"OPENAI_API_KEY": os.getenv("OPENAI_API_KEY")}

sources = {
    "files": [
        "https://example.com/resume.pdf",
        "https://example.com/index.html",
        "path/to/local/document.docx",
        "https://youtube.com/watch?v=dQw4w9WgXcQ",   # YouTube transcript
        "https://arxiv.org/abs/2301.12345",            # arXiv paper
        "path/to/notebook.ipynb",                      # Jupyter notebook
        "path/to/slides.pptx",                         # PowerPoint
    ],
    "sitemap_url": "https://example.com/sitemap.xml",
    "github_repositories": ["username/repo"],
    "rss_urls": ["https://blog.example.com/feed"],
}

kbb = KBBuilder(config)
kbb.build(
    sources=sources,
    output_file="knowledge_base.md",
    incremental=True,                          # skip unchanged sources on rebuild
    on_progress=lambda stage, i, n: print(f"{stage}: {i}/{n}"),
)
```

See the [`KBBuilder` reference](../api/kbbuilder.md) for every parameter.

## From the command line

```bash
knowledge-base-builder \
  -f https://example.com/resume.pdf \
  -f https://example.com/index.html \
  -m https://example.com/sitemap.xml \
  -g username/repo \
  -o knowledge_base.md
```

No API key needed for raw output:

```bash
knowledge-base-builder --output-format raw -f https://example.com -o kb.md
```

See the [CLI reference](../api/cli.md) for all flags.

## Preview before you build

Use `dry_run=True` to validate that your sources are reachable and your API key works — without processing anything.

```python
summary = kbb.build(sources={"files": ["https://example.com/doc.pdf"]}, dry_run=True)
print(summary)
# {'total_sources': 1, 'accessible': 1, 'inaccessible': 0,
#  'sources_by_type': {'pdf': 1}, 'api_key_valid': True, 'llm_provider': 'GeminiClient'}
```

!!! note "Runs in notebooks too"
    The synchronous API is safe to call from inside Jupyter or Colab — an already-running
    event loop no longer breaks it.
