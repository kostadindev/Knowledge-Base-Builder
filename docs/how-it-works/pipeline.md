# The Pipeline

A build runs in three phases. The first two are always executed; the third is skipped for
the `raw` and `chunks` formats.

```text
Sources (PDF, HTML, GitHub, YouTube, arXiv, RSS, Jupyter, PPTX, ...)
    |
    v
[1] Extraction  (concurrent, async)
    - Each source routed to its processor by URL pattern or file extension
    - Downloads + text extraction run in thread pools
    - A semaphore caps concurrency (default 8); retries use exponential backoff
    - Duplicate URLs skipped; per-source results recorded in metadata
    |
    v
[2] Merge & chunk
    - Extracted texts joined with document separators
    - Split at paragraph / sentence boundaries into ~20K-token chunks
    - No LLM calls in this phase
    |
    v
[3] LLM structuring   (markdown / llms_txt only)
    - Each chunk processed by the configured provider
    - Structured prompt: hierarchical headings, preserved detail, source attribution
    - Retry with backoff; a failing chunk is split and retried in halves
    |
    v
Output: kb.md  +  kb.md.meta.json
```

## Phase 1 — Extraction

Every source type has a processor implementing `download()` and `extract_text()`.
Extraction is fully concurrent: downloads and CPU-bound parsing run in threads, coordinated
by an `asyncio` semaphore. Transient network failures are retried with exponential backoff.

Each source produces a result record — URL, type, word count, timing, and success or the
error message — collected into the build metadata. After extraction, a **source summary**
is logged (how many succeeded, and every failure with its reason).

!!! note "Safe in notebooks"
    The synchronous API drives its async work on a dedicated background event loop, so
    calling `build()` from inside a running loop (Jupyter, Colab) works without the
    classic *"event loop is already running"* error.

## Phase 2 — Merge & chunk

Extracted texts are concatenated with separators and split into large chunks at natural
boundaries. For `output_format="chunks"`, this phase produces the final JSON directly (with
per-chunk `source` and `section` metadata) and the pipeline stops here. For `raw`, the
merged text is written as-is.

## Phase 3 — LLM structuring

For `markdown` and `llms_txt`, each chunk is sent to the provider with a format-specific
prompt. If a chunk fails, it is split in half and each half retried, so a single oversized
or problematic section doesn't sink the whole build. The structured chunks are concatenated
into the final document.

## Incremental builds

Pass `incremental=True` to cache extracted text keyed by a SHA-256 hash of each source's
content (in `.kbb_cache/`). On a rebuild, unchanged sources are served from cache and skip
re-download and re-extraction.

## Caveats

- The current pipeline is **preprocess-only**: chunks are structured independently and
  concatenated, not cross-merged into a single deduplicated document.
- LLM responses themselves are not cached (only extracted text is), so re-running a
  `markdown` build re-invokes the model.
