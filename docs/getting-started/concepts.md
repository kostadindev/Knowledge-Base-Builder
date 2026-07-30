# Core Concepts

Four ideas cover everything Knowledge Base Builder does.

## Sources

A **source** is anything you want in your knowledge base: a URL, a local file path, a
`user/repo` GitHub shorthand, or a sitemap. You provide sources either positionally to
the [`build()`](../api/build.md) helper or grouped in a `sources` dict to
[`KBBuilder.build`](../api/kbbuilder.md).

Sources are routed automatically:

- **By URL pattern** — YouTube, arXiv, and RSS links are recognized on sight.
- **By file extension** — `.pdf`, `.docx`, `.csv`, `.ipynb`, `.pptx`, and so on.
- **Fallback** — any other URL is fetched and cleaned as a web page.

Duplicate URLs are skipped within a build. See [Sources](../guides/sources.md) for the full table.

## Processors

Each source type has a **processor** that knows how to download it and extract clean text.
Processors run **concurrently** with automatic retry and exponential backoff, and their
output is tracked per-source (word count, timing, success/failure) in the build metadata.

Optional processors (spreadsheets, YouTube, RSS, PowerPoint, arXiv) are installed via
[extras](installation.md#optional-extras) and guarded — if the dependency is missing you
get an actionable error naming the extra to install, not a crash.

## Providers

An **LLM provider** structures the extracted text into the final document. Three are
supported — Google Gemini (default), OpenAI, and Anthropic — auto-selected from whichever
API key you supply (priority: **Gemini → OpenAI → Anthropic**). Override the model,
temperature, retries, or concurrency through config keys:

```python
config = {
    "OPENAI_API_KEY": "...",
    "OPENAI_MODEL": "gpt-4o-mini",
    "OPENAI_TEMPERATURE": 0.3,
    "OPENAI_MAX_CONCURRENCY": 4,
}
```

No provider key? The build runs in [`raw` mode](../guides/output-formats.md#raw) and skips
the LLM entirely.

## Output formats

The same extracted content can be emitted four ways:

| Format | LLM used? | What you get |
|--------|-----------|--------------|
| `markdown` *(default)* | yes | Hierarchical Markdown knowledge base |
| `llms_txt` | yes | [llmstxt.org](https://llmstxt.org)-spec file + a `-full.txt` companion |
| `chunks` | no | Vector-DB-ready JSON (`id` / `text` / `metadata`) |
| `raw` | no | Extracted text, concatenated — works with no API key |

See [Output Formats](../guides/output-formats.md) for details and examples.

## Putting it together

```text
sources  ──►  processors  ──►  extracted text  ──►  provider (LLM)  ──►  output
(URLs,        (concurrent      (merged &            (skipped for         (kb.md,
 files,        download +       chunked)             raw / chunks)        llms.txt,
 repos)        extract)                                                   chunks.json)
```

Every build also writes a `.meta.json` sidecar with provenance: provider/model, per-source
results, timings, and output stats. See [The Pipeline](../how-it-works/pipeline.md).
