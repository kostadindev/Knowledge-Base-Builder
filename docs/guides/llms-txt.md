# Generate `/llms.txt`

[`/llms.txt`](https://llmstxt.org) is an emerging standard: a Markdown file at the root of
your site that gives LLMs a curated, navigable map of your content. Knowledge Base Builder
generates one from your existing pages in a single command.

## One command

```python
import knowledge_base_builder as kbb

kbb.build("https://mysite.com/sitemap.xml", out="llms.txt",
          output_format="llms_txt", project_name="My Project")
```

```bash
knowledge-base-builder \
  -m https://mysite.com/sitemap.xml \
  --output-format llms_txt \
  --project-name "My Project" \
  -o llms.txt
```

## What you get

Two files:

- **`llms.txt`** — the spec-compliant file: an H1 title, a one-line blockquote summary,
  and H2 sections listing resources as `- [Name](URL): description`.
- **`llms-full.txt`** — the full extracted text from every source, before LLM structuring,
  for tools that want the complete corpus.

```text title="llms.txt"
# My Project

> A short summary of what the project or site is about.

## Docs
- [Getting Started](https://mysite.com/start): install and first build
- [API Reference](https://mysite.com/api): full method reference

## Blog
- [Launch post](https://mysite.com/blog/launch): why we built this
```

## Tips

- Pass `project_name` to control the H1; omit it to let the model infer the name from your
  content.
- Point `sitemap_url` (CLI `-m`) at your sitemap to cover the whole site at once, or list
  individual pages in `files`.
- Serve the resulting `llms.txt` at your site root (`https://mysite.com/llms.txt`).

See [Output Formats](output-formats.md#llms_txt) for how this fits with the other formats.
