# `build()`

The one-line convenience API. Reads keys from the environment, routes each positional
source to the right bucket, and falls back to key-free `raw` extraction when no LLM key is
found.

```python
import knowledge_base_builder as kbb

kbb.build("https://arxiv.org/abs/2301.12345", "octocat/Hello-World", out="kb.md")
```

---

## `kbb.build`

```python
def build(
    *sources: str,
    out: str = "knowledge_base.md",
    config: dict | None = None,
    **build_kwargs,
) -> str | dict
```

Build a knowledge base from one or more sources in a single call.

**Parameters**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `*sources` | `str` | — | Any mix of URLs, local file paths, `user/repo` GitHub shorthand, GitHub URLs, or a `*sitemap*.xml` URL. At least one is required. |
| `out` | `str` | `"knowledge_base.md"` | Output file path. |
| `config` | `dict \| None` | `None` | Explicit config. When omitted, keys are read from the environment (`GOOGLE_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GITHUB_API_KEY`). |
| `**build_kwargs` | — | — | Forwarded to [`KBBuilder.build`](kbbuilder.md#kbbuilderbuild) — e.g. `output_format`, `incremental`, `validate`, `dry_run`. |

**Returns:** the output file path, or a summary `dict` when `dry_run=True`.

**Raises:**

- `ValueError` — no sources were passed.
- `TypeError` — a source isn't a string (with a hint to unpack a list: `kbb.build(*my_list, out=...)`).

**Source routing**

- `user/repo` shorthand or a `github.com` URL → `github_repositories`
- a `*sitemap*.xml` URL → `sitemap_url`
- everything else → `files` (then auto-detected by pattern/extension)

---

## Helpers

### `kbb.config_from_env`

```python
def config_from_env() -> dict
```

Return a config dict populated from `GOOGLE_API_KEY`, `OPENAI_API_KEY`,
`ANTHROPIC_API_KEY`, and `GITHUB_API_KEY` (only non-empty values are included).

### `kbb.classify_sources`

```python
def classify_sources(sources: list[str]) -> dict
```

Route a flat list of source strings into a `KBBuilder` sources dict — the same logic
`build()` uses internally. Useful if you want to inspect or tweak routing before building.

```python
kbb.classify_sources(["user/repo", "https://x.com/doc.pdf", "https://x.com/sitemap.xml"])
# {'files': ['https://x.com/doc.pdf'],
#  'github_repositories': ['user/repo'],
#  'sitemap_url': 'https://x.com/sitemap.xml'}
```

---

## Examples

```python
# Different output format
kbb.build("https://mysite.com", out="llms.txt", output_format="llms_txt")

# Explicit provider config
kbb.build("docs/", out="kb.md", config={"OPENAI_API_KEY": "sk-...", "OPENAI_MODEL": "gpt-4o-mini"})

# Validate inputs without processing
kbb.build("https://example.com/doc.pdf", dry_run=True)
```
