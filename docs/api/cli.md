# CLI

Installing the package adds a `knowledge-base-builder` console command.

```bash
knowledge-base-builder \
  -f https://example.com/resume.pdf \
  -m https://example.com/sitemap.xml \
  -g username/repo \
  -o knowledge_base.md
```

Environment variables from a `.env` file in the working directory are loaded automatically.

## Sources

| Flag | Description |
|------|-------------|
| `-f`, `--file` | A URL or local path of any supported type. Repeatable. |
| `-m`, `--sitemap` | Crawl an entire site via its `sitemap.xml`. |
| `-g`, `--github-repo` | GitHub repo as `user/repo` or a full URL. Repeatable. |
| `--rss` | RSS/Atom feed URL. Repeatable. |
| `--github-username` | Process all public repos for a user. |

Legacy per-type flags also exist: `-p/--pdf`, `-d/--document`, `-s/--spreadsheet`,
`-w/--web-content`, `-u/--web-url`.

## Output

| Flag | Default | Description |
|------|---------|-------------|
| `-o`, `--output` | `final_knowledge_base.md` | Output file path. |
| `--output-format` | `markdown` | `markdown`, `llms_txt`, `chunks`, or `raw`. |
| `--project-name` | — | H1 heading for `llms_txt` mode. |
| `--chunk-size` | `1000` | Max characters per chunk in `chunks` mode. |
| `--no-metadata` | — | Suppress the `.meta.json` sidecar. |
| `--validate` | — | Run output quality checks; include in metadata. |

## Providers

| Flag | Description |
|------|-------------|
| `--llm-provider` | `gemini` (default), `openai`, or `anthropic`. |
| `--google-api-key` / `--openai-api-key` / `--anthropic-api-key` | Provider key (or use the env var). |
| `--gemini-model` / `--openai-model` / `--anthropic-model` | Override the model. |
| `--gemini-temperature` / `--openai-temperature` / `--anthropic-temperature` | Sampling temperature. |
| `--github-api-key` | GitHub token for higher rate limits. |

!!! tip "No key needed for `raw`"
    `--output-format raw` (and `chunks`) require no provider key:
    ```bash
    knowledge-base-builder --output-format raw -f https://example.com -o kb.md
    ```

## Caching & preview

| Flag | Description |
|------|-------------|
| `--incremental` | Cache extracted text; skip unchanged sources on rebuild. |
| `--cache-dir` | Cache directory (default `.kbb_cache`). |
| `--dry-run` | Validate sources and API key without processing; prints a JSON summary. |

```bash
# Dry-run prints an accessibility + key summary as JSON
knowledge-base-builder --dry-run -f https://example.com/doc.pdf -g user/repo
```
