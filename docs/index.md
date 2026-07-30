---
hide:
  - navigation
---

<div class="hero" markdown>

# Knowledge Base Builder

**Turn any source into one structured knowledge base.**
{ .hero-tagline }

Point it at web pages, PDFs, GitHub repos, YouTube videos, arXiv papers, RSS feeds, notebooks, and slides — it extracts everything and consolidates it into a single, LLM-structured Markdown file.

[Get Started](getting-started/quickstart.md){ .md-button .md-button--primary }
[API Reference](api/build.md){ .md-button }

</div>

```python
import knowledge_base_builder as kbb

kbb.build("https://arxiv.org/abs/1706.03762", "octocat/Hello-World", "notes.pdf", out="kb.md")
```

```text title="Output — kb.md"
# Attention Is All You Need
> The Transformer, a model architecture relying entirely on attention...

## Hello-World (GitHub)
- **Purpose**: octocat's introductory repository...

## Meeting notes
- Q3 roadmap: ship the ingestion pipeline...
```

---

<div class="grid" markdown>

<div class="card" markdown>
### :page_facing_up: One call, many sources
Mix URLs, local files, GitHub repos, and sitemaps in a single `build()`. Each source is auto-routed to the right extractor — no per-type wiring.
</div>

<div class="card" markdown>
### :robot: Built for LLMs
Emit structured Markdown, an [llmstxt.org](https://llmstxt.org)-spec `/llms.txt`, or vector-DB-ready JSON chunks. Drop it straight into a RAG pipeline or a chatbot.
</div>

<div class="card" markdown>
### :zap: Fast and concurrent
Downloads and extraction run in parallel with retry/backoff. Incremental caching skips unchanged sources on rebuild.
</div>

<div class="card" markdown>
### :battery: Works out of the box
No API key? Run in `raw` mode and still get a result. Runs in scripts, notebooks, and Colab alike. Clear errors when input is off.
</div>

</div>

```bash
pip install knowledge-base-builder
```

---

## Supported sources

| Source | Formats / detection |
|--------|---------------------|
| Documents | PDF, DOCX, TXT, MD, RTF |
| Spreadsheets | CSV, TSV, XLSX, ODS |
| Web content | HTML, XML, JSON, YAML/YML |
| Websites | any URL, or a whole `sitemap.xml` |
| GitHub | `user/repo` shorthand or GitHub URLs (README + Markdown) |
| YouTube | `youtube.com` / `youtu.be` URLs — transcripts |
| arXiv | `arxiv.org` URLs or bare IDs like `2301.12345` (PDF + metadata) |
| RSS / Atom | feed URLs |
| Jupyter | `.ipynb` (code + markdown + outputs) |
| PowerPoint | `.pptx` (slides + speaker notes) |

Mix any of these in one call. URL-based types (YouTube, arXiv, RSS) are detected by pattern; file types by extension. Duplicate URLs are skipped automatically. See [Sources](guides/sources.md).

---

## What you can build

<div class="grid" markdown>

<div class="card" markdown>
### RAG preprocessing
Consolidate scattered docs into clean Markdown or JSON chunks ready for embedding and retrieval.
</div>

<div class="card" markdown>
### `/llms.txt` for your site
Generate a spec-compliant `/llms.txt` so LLMs can navigate your content. See the [guide](guides/llms-txt.md).
</div>

<div class="card" markdown>
### Domain chatbots
Assemble a single source of truth from repos, blogs, and papers, then hand it to an assistant.
</div>

<div class="card" markdown>
### Personal knowledge base
Fold a résumé, a GitHub profile, talks, and papers into one portable Markdown file.
</div>

</div>

---

## Next steps

- **[Installation](getting-started/installation.md)** — core install and optional extras
- **[Quickstart](getting-started/quickstart.md)** — the one-liner, raw mode, and full control
- **[Core Concepts](getting-started/concepts.md)** — sources, processors, providers, output formats
- **[The Pipeline](how-it-works/pipeline.md)** — how extraction and structuring actually work
