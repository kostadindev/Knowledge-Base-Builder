# Recipes

Copy-paste starting points for common jobs. Each is a complete, runnable snippet.

## A `/llms.txt` for your docs site

Crawl a whole site via its sitemap and emit a spec-compliant `/llms.txt`.

```python
import knowledge_base_builder as kbb

kbb.build(
    "https://mysite.com/sitemap.xml",
    out="llms.txt",
    output_format="llms_txt",
    project_name="My Project",
)
```

Serve the result at `https://mysite.com/llms.txt`. See [Generate /llms.txt](llms-txt.md).

## A RAG corpus (vector-DB chunks)

Turn a folder of documents into embed-ready JSON chunks — no LLM, no API key.

```python
import knowledge_base_builder as kbb

kbb.build(
    "docs/guide.pdf", "docs/faq.md", "https://mysite.com/changelog",
    out="chunks.json",
    output_format="chunks",
    chunk_size=800,
)
```

Each chunk carries `{"id", "text", "metadata": {"source", "section", "index"}}` — load it
straight into your vector store.

## Everything a GitHub user has published

```python
from knowledge_base_builder import KBBuilder

kbb = KBBuilder({"GITHUB_API_KEY": "..."})   # token raises the rate limit to 5000/hr
kbb.build(sources={"github_username": "octocat"}, output_file="octocat.md")
```

## A personal knowledge base

Fold a résumé, a GitHub repo, a talk, and a paper into one portable file.

```python
import knowledge_base_builder as kbb

kbb.build(
    "https://example.com/resume.pdf",
    "yourname/portfolio",
    "https://youtu.be/your-talk",           # needs [youtube]
    "https://arxiv.org/abs/2301.12345",     # needs [arxiv]
    out="me.md",
)
```

## Preflight before a big run

Validate that every source is reachable and your key works — without processing anything.

```python
summary = kbb.build(
    "https://example.com/a.pdf", "user/repo", "https://example.com/missing",
    dry_run=True,
)
print(summary)
# {'total_sources': 3, 'accessible': 2, 'inaccessible': 1,
#  'inaccessible_sources': [{'url': '.../missing', 'status_code': 404, ...}],
#  'api_key_valid': True, 'llm_provider': 'GeminiClient'}
```

## Fast rebuilds while iterating

Cache extracted text so unchanged sources are skipped on the next run.

```python
from knowledge_base_builder import KBBuilder

kbb = KBBuilder({"OPENAI_API_KEY": "..."})
kbb.build(
    sources={"sitemap_url": "https://mysite.com/sitemap.xml"},
    output_file="kb.md",
    incremental=True,     # writes/reads .kbb_cache/
)
```

## Try it with zero setup

No key, no config — just see extraction work.

```python
import knowledge_base_builder as kbb

kbb.build("https://example.com", out="kb.md")   # falls back to raw mode
```

## Watch progress in a long build

```python
from knowledge_base_builder import KBBuilder

kbb = KBBuilder({"GOOGLE_API_KEY": "..."})
kbb.build(
    sources={"sitemap_url": "https://bigsite.com/sitemap.xml"},
    output_file="kb.md",
    on_progress=lambda stage, i, n: print(f"[{stage}] {i}/{n}"),
)
```
