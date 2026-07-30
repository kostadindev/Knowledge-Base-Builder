# `KBBuilder`

The main class. Use it directly when you want explicit control over configuration and
source grouping; for a quick call, prefer [`build()`](build.md).

```python
from knowledge_base_builder import KBBuilder

kbb = KBBuilder({"OPENAI_API_KEY": "sk-..."})
kbb.build(sources={"files": ["https://example.com"]}, output_file="kb.md")
```

---

## `KBBuilder(config, allow_no_llm=False)`

Initialize a builder with provider configuration.

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `config` | `dict` | — | Configuration (see keys below). At least one provider key is required unless `allow_no_llm=True`. |
| `allow_no_llm` | `bool` | `False` | Tolerate a missing API key. The builder can then only produce `output_format="raw"`; `markdown`/`llms_txt` fall back to `raw`. |

**Config keys**

| Key | Description |
|-----|-------------|
| `GOOGLE_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | Provider key (at least one, unless `allow_no_llm`). Auto-selected in that priority. |
| `{PROVIDER}_MODEL` | Override the model, e.g. `OPENAI_MODEL="gpt-4o-mini"`. |
| `{PROVIDER}_TEMPERATURE` | Sampling temperature (default `0.7`). |
| `{PROVIDER}_MAX_RETRIES` | Retry attempts on API errors (default `3`). |
| `{PROVIDER}_MAX_CONCURRENCY` | Max concurrent LLM requests (default `8`). |
| `GITHUB_API_KEY` | Optional; raises the GitHub rate limit to 5000 req/hour. |

**Raises:** `ValueError` if no API key is provided and `allow_no_llm` is `False`.

Defaults: Gemini `gemini-2.0-flash`, OpenAI `gpt-4o`, Anthropic `claude-3-7-sonnet`.

---

## `KBBuilder.build`

```python
def build(
    sources: dict = None,
    output_file: str = "final_knowledge_base.md",
    on_progress: Callable[[str, int, int], None] | None = None,
    output_format: str = "markdown",
    project_name: str | None = None,
    metadata: bool = True,
    incremental: bool = False,
    cache_dir: str | None = None,
    dry_run: bool = False,
    chunk_size: int = 1000,
    validate: bool = False,
) -> str | dict
```

Build a knowledge base from the provided sources.

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `sources` | `dict` | `None` | Sources grouped by key (see below). |
| `output_file` | `str` | `"final_knowledge_base.md"` | Output path. |
| `on_progress` | `callable` | `None` | Callback `(stage, current, total)`. |
| `output_format` | `str` | `"markdown"` | `"markdown"`, `"llms_txt"`, `"chunks"`, or `"raw"`. See [Output Formats](../guides/output-formats.md). |
| `project_name` | `str` | `None` | H1 heading for `llms_txt` mode. |
| `metadata` | `bool` | `True` | Write a `.meta.json` sidecar. |
| `incremental` | `bool` | `False` | Cache extracted text; skip unchanged sources on rebuild. |
| `cache_dir` | `str` | `None` | Cache directory (default `.kbb_cache`). |
| `dry_run` | `bool` | `False` | Validate sources + API key without processing; returns a summary dict. |
| `chunk_size` | `int` | `1000` | Max characters per chunk in `chunks` mode. |
| `validate` | `bool` | `False` | Run output quality checks; include results in metadata. |

**Returns:** the output file path, or a summary `dict` when `dry_run=True`.

**Raises:**

- `ValueError` — invalid `output_format`.
- `TypeError` — `sources` isn't a dict, or a key has the wrong value type (the message shows the fix). Unrecognized keys warn and are ignored.

### `sources` keys

| Key | Type | Description |
|-----|------|-------------|
| `files` | `list[str]` | URLs or paths — auto-detected by extension/pattern. |
| `sitemap_url` | `str` | A `sitemap.xml` to crawl. |
| `github_repositories` | `list[str]` | Repos as `"user/repo"` or URLs. |
| `github_username` | `str` | Process all repos for a user. |
| `rss_urls` | `list[str]` | RSS/Atom feed URLs. |
| *legacy* | `list[str]` | `pdf_urls`, `document_urls`, `spreadsheet_urls`, `web_content_urls`, `web_urls`. |

---

## Example

```python
kbb.build(
    sources={
        "files": ["https://example.com/doc.pdf", "notes.ipynb"],
        "github_repositories": ["user/repo"],
        "sitemap_url": "https://example.com/sitemap.xml",
    },
    output_file="kb.md",
    output_format="llms_txt",
    project_name="My Project",
    incremental=True,
    validate=True,
    on_progress=lambda stage, i, n: print(f"{stage}: {i}/{n}"),
)
```
