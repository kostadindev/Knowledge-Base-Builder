# Sources

Every source type can be mixed in a single build. This page covers what's supported, how each is detected, and which [extra](../getting-started/installation.md#optional-extras) it needs.

## Supported types

| Source | Formats / detection | Extra required |
|--------|---------------------|----------------|
| Documents | PDF, DOCX, TXT, MD, RTF | core |
| Spreadsheets | CSV, TSV, XLSX, ODS | `spreadsheets` |
| Web content | HTML, XML, JSON, YAML/YML | core |
| Websites | any URL, or a whole `sitemap.xml` | core |
| GitHub | `user/repo` or GitHub URLs (README + Markdown files) | core |
| YouTube | `youtube.com` / `youtu.be` URLs — video transcripts | `youtube` |
| arXiv | `arxiv.org` URLs or bare IDs like `2301.12345` (PDF + metadata) | `arxiv` |
| RSS / Atom | feed URLs | `rss` |
| Jupyter | `.ipynb` — code, markdown, and outputs | core |
| PowerPoint | `.pptx` — slides + speaker notes | `pptx` |

## How routing works

With the [`build()`](../api/build.md) helper you just pass strings; classification happens for you:

- **`user/repo`** or a `github.com` URL → GitHub repository
- a `*sitemap*.xml` URL → sitemap crawl
- anything else → a file/URL, then routed by pattern or extension

```python
import knowledge_base_builder as kbb

kbb.build(
    "torvalds/linux",                       # GitHub
    "https://example.com/sitemap.xml",      # sitemap
    "https://youtu.be/dQw4w9WgXcQ",         # YouTube
    "paper.pdf",                            # local PDF
    out="kb.md",
)
```

With `KBBuilder`, group sources explicitly in the `sources` dict:

```python
sources = {
    "files": ["doc.pdf", "https://site.com", "slides.pptx"],
    "github_repositories": ["user/repo", "https://github.com/user/other"],
    "github_username": "octocat",              # process all of a user's repos
    "sitemap_url": "https://site.com/sitemap.xml",
    "rss_urls": ["https://blog.com/feed"],
}
```

### Recognized `sources` keys

`files`, `sitemap_url`, `github_repositories`, `github_username`, `rss_urls`, plus the
legacy per-type keys `pdf_urls`, `document_urls`, `spreadsheet_urls`, `web_content_urls`,
`web_urls`.

!!! tip "Typos are caught"
    An unrecognized key logs a warning that suggests the closest valid one
    (*"Ignoring unrecognized sources key 'github_repos'. Did you mean
    'github_repositories'?"*), and passing a string where a list is expected raises a
    `TypeError` with the exact fix. Bad input never silently produces an empty file.

## Local files vs. URLs

Local paths and `http(s)` URLs both work anywhere a source is accepted. Local paths are
resolved to absolute `file://` URLs internally, so relative paths are relative to your
working directory.

## Special cases

- **arXiv** — accepts full URLs (`arxiv.org/abs/...`, `/pdf/...`) or bare IDs
  (`2301.12345`, `2301.12345v2`). Paper metadata (title, authors, abstract, categories)
  is prepended to the extracted text.
- **GitHub** — pulls README and other Markdown files from a repo. Set `github_username`
  to ingest every public repo for a user. A `GITHUB_API_KEY` raises the rate limit from
  60 to 5000 requests/hour.
- **Sitemaps** — every URL in the sitemap is fetched and cleaned as a web page.
