# Output Formats

Set `output_format` to control what a build produces. The extraction step is identical for
all four; they differ in whether an LLM runs and how the result is written.

| Format | LLM used? | API key needed? | Output |
|--------|-----------|-----------------|--------|
| [`markdown`](#markdown) *(default)* | yes | yes | Structured Markdown knowledge base |
| [`llms_txt`](#llms_txt) | yes | yes | `/llms.txt`-spec file + `-full.txt` companion |
| [`chunks`](#chunks) | no | no | Vector-DB-ready JSON |
| [`raw`](#raw) | no | no | Concatenated extracted text |

## markdown

The default. Each chunk of extracted text is sent to the LLM with a prompt that requests
hierarchical headings, preserved facts and code, and source attribution.

```python
kbb.build("https://example.com", out="kb.md")   # output_format="markdown" is the default
```

## llms_txt

Produces output conforming to the [llmstxt.org](https://llmstxt.org) specification — an H1
title, a blockquote summary, and H2 sections of linked resources — designed to help LLMs
navigate your content.

```python
kbb.build("https://mysite.com", out="llms.txt", output_format="llms_txt",
          project_name="My Project")
```

This writes **two** files:

- `llms.txt` — the structured navigation file
- `llms-full.txt` — the complete extracted text (pre-LLM)

See the [dedicated guide](llms-txt.md).

## chunks

Splits extracted text into chunks suitable for embedding into a vector database. **No LLM
call** — fast and free. Each chunk carries metadata.

```python
kbb.build("guide.pdf", "https://mysite.com/faq", out="chunks.json",
          output_format="chunks", chunk_size=1000)
```

```json title="chunks.json"
[
  {
    "id": "chunk_0",
    "text": "## Overview\nKnowledge Base Builder ingests...",
    "metadata": {"source": "https://example.com", "section": "Overview", "index": 0}
  }
]
```

`chunk_size` is the maximum number of characters per chunk (default `1000`); splits prefer
paragraph, then sentence boundaries.

## raw

Concatenates the cleaned extracted text with no LLM structuring. **Requires no API key** —
ideal for a first run, for debugging extraction, or when you just want the merged source
text.

```python
kbb.build("https://example.com", out="raw.md", output_format="raw")
```

```bash
knowledge-base-builder --output-format raw -f https://example.com -o raw.md
```

If no LLM key is configured, `markdown` and `llms_txt` automatically fall back to `raw`
with a warning, so a build always produces something.

## The metadata sidecar

Unless you pass `metadata=False`, every build writes `<output>.meta.json` with build
provenance:

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

Pass `validate=True` to add a quality score (non-empty, has headings, source coverage,
length) to the sidecar.
