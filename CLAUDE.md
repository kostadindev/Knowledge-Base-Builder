# CLAUDE.md

Guidance for Claude Code when working in this repository.

## What this is

**Knowledge Base Builder** (`knowledge-base-builder` on PyPI) is a Python package that
ingests diverse content sources (web pages, PDFs, docs, spreadsheets, GitHub repos,
YouTube transcripts, arXiv papers, RSS feeds, Jupyter notebooks, PowerPoint) and
consolidates them into a single structured Markdown knowledge base using an LLM.

Target use cases: `/llms.txt` context files, RAG preprocessing, vector-DB ingestion,
and domain-specific chatbots.

- License: MIT. Author: Kostadin Devedzhiev.
- Version lives in **two** places that must stay in sync: `setup.py` and
  `knowledge_base_builder/__init__.py` (`__version__`).
- Python `>=3.8`.

## Repo layout — mind the nesting

The git repo root is `knowledge-base-builder/`; the importable package is the nested
`knowledge-base-builder/knowledge_base_builder/`. Run tooling (pytest, pip install,
setup.py) **from the repo root**, not from inside the package directory.

```
knowledge-base-builder/            # repo root — run commands here
├── setup.py, pyproject.toml, requirements.txt
├── pytest.ini                     # testpaths = knowledge_base_builder/tests
├── README.md, CHANGELOG.md
├── mkdocs.yml                     # MkDocs Material docs site config
├── docs/                          # docs source (index, getting-started, guides, how-it-works, api)
├── example_usage.py, comprehensive_example.py, cli_example.sh
├── experiments/                   # standalone research scripts (exp1–exp4 + run_all)
├── paper/                         # JOSS-style paper (paper.md, report.html)
└── knowledge_base_builder/        # the package
    ├── __init__.py                # public API exports + __version__
    ├── api.py                     # build() one-liner + source classification (convenience API)
    ├── async_utils.py             # run_sync() — safe coroutine runner (Jupyter-proof)
    ├── kb_builder.py              # KBBuilder — the orchestrator (largest file)
    ├── cli.py                     # `knowledge-base-builder` console entry point
    ├── llm.py                     # LLM — prompt templates + async preprocessing
    ├── llm_client.py              # LLMClient ABC (run / run_async)
    ├── gemini_client.py, openai_client.py, anthropic_client.py
    ├── base_processor.py          # BaseProcessor ABC (download / extract_text / check_accessible)
    ├── *_processor.py             # one per source type (see below)
    ├── chunker.py                 # Chunker — vector-DB chunk output
    ├── cache.py                   # BuildCache — incremental build cache (.kbb_cache/)
    ├── build_metadata.py          # BuildMetadata / SourceResult — .meta.json sidecar
    ├── validator.py               # OutputValidator — quality score
    └── tests/                     # pytest suite
```

## Architecture

Two abstract base classes anchor the design; add new capability by subclassing them.

**`LLMClient`** (`llm_client.py`) — abstract async LLM wrapper. Concrete clients:
`GeminiClient`, `OpenAIClient`, `AnthropicClient` (all LangChain-backed, with retry +
exponential backoff and a concurrency semaphore). `KBBuilder.__init__` auto-selects a
provider from available API keys in fixed order: **Gemini → OpenAI → Anthropic**.

**`BaseProcessor`** (`base_processor.py`) — abstract source handler. The common contract
is `download(url) -> local_path` then `extract_text(path) -> str`. Processors:

| Processor | Source | Routing trigger |
|-----------|--------|-----------------|
| `PDFProcessor` | PDF | `.pdf` |
| `DocumentProcessor` | DOCX/TXT/MD/RTF | those extensions |
| `SpreadsheetProcessor` | CSV/TSV/XLSX/ODS | those extensions |
| `WebContentProcessor` | HTML/XML/JSON/YAML files | those extensions |
| `WebsiteProcessor` | live URLs + sitemaps | fallback for bare http(s) URLs |
| `GitHubProcessor` | repo markdown files | `github_repositories` / `github_username` |
| `YouTubeProcessor` | video transcripts | `is_youtube_url()` |
| `ArxivProcessor` | papers (PDF + metadata) | `is_arxiv_url()` (incl. bare IDs like `2301.12345`) |
| `RSSProcessor` | RSS/Atom feeds | `is_rss_url()` or `--rss` |
| `JupyterProcessor` | `.ipynb` | `.ipynb` |
| `PresentationProcessor` | `.pptx` | `.pptx` |

**No-LLM mode:** `KBBuilder({})` still raises without a key (backward compat). Pass
`KBBuilder(config, allow_no_llm=True)` to tolerate a missing key — the builder can then
only emit `output_format="raw"` (or `"chunks"`), and `"markdown"`/`"llms_txt"` auto-fall
back to `"raw"` with a warning. The `kbb.build(...)` convenience wrapper (`api.py`) sets
this automatically when no key is found in the environment.

`LLM` (`llm.py`) holds the prompt templates. Note the whole pipeline is
**preprocess-only** in current builds: `KBBuilder.build` concatenates all extracted text,
splits into ~20K-token chunks, and runs each through `preprocess_text_async`
(or `preprocess_text_llms_txt_async`). The `merge_all_kbs` / `process_documents`
methods exist but are **not** on the main `build` path.

### The `KBBuilder.build` pipeline (`kb_builder.py`)

1. `dry_run=True` short-circuits to `_dry_run` (HEAD-checks every source concurrently,
   validates the API key with a tiny call, returns a summary dict — no processing).
2. Process `files` concurrently via `process_files_async` — routing in
   `process_files_async` is **URL-pattern first** (YouTube/arXiv/RSS), then extension,
   then bare-URL fallback. Local paths are converted to `file://` URLs.
3. Process legacy typed source keys (`pdf_urls`, `document_urls`, etc.) for backward compat.
4. Process `sitemap_url`, then GitHub (`github_username` = all repos, or `github_repositories`).
5. Emit output per `output_format`:
   - `"markdown"` (default) — LLM-structured Markdown.
   - `"llms_txt"` — llmstxt.org spec format; also writes a `-full.txt` raw companion.
   - `"chunks"` — `Chunker` emits vector-DB-ready JSON (`id`/`text`/`metadata`), **no LLM call**.
   - `"raw"` — extracted text concatenated with no LLM structuring; works with **no API key**.
6. Side artifacts (unless disabled): `<output>.meta.json` sidecar (`BuildMetadata`), and
   with `validate=True` a quality score from `OutputValidator`.

Cross-cutting: `_is_duplicate` dedupes URLs per build; `BuildCache` (`incremental=True`)
caches extracted text keyed by SHA-256 content hash in `.kbb_cache/`.

## Common commands

Run from the **repo root**.

```bash
pip install -e ".[all]"              # editable install with all optional extras
pip install -r test-requirements.txt # pytest, pytest-cov, mock

pytest                               # full suite (config in pytest.ini)
pytest knowledge_base_builder/tests/test_chunker.py   # one file
pytest -k arxiv                      # by keyword
pytest --cov=knowledge_base_builder  # with coverage

# CLI (installed as console_script)
knowledge-base-builder --openai-api-key $KEY -f https://example.com/doc.pdf -o kb.md
knowledge-base-builder --dry-run -f ... -g user/repo   # validate without processing
```

Docs (MkDocs Material, matches the skillinfer repo's setup):

```bash
pip install mkdocs-material pymdown-extensions
mkdocs serve                         # live preview at localhost:8000
mkdocs build --strict                # what CI runs; keep this clean (no broken links)
```

CI (`.github/workflows/`): `tests.yml` (pytest), `pylint.yml`, `draft-pdf.yml` (paper),
`docs.yml` (builds `mkdocs build --strict` and deploys to GitHub Pages on push to `main`).
The README is intentionally lean and links to the docs site
(`kostadindev.github.io/knowledge-base-builder`) — put detailed reference in `docs/`, not
the README (which is also the PyPI long-description). Keep both in sync with the code.

## Configuration

API keys come from a `.env` file (see `.env.example`) or CLI flags. At least one of
`GOOGLE_API_KEY` / `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` is required; `GITHUB_API_KEY`
is optional (raises GitHub rate limit 60→5000/hr). Per-provider `*_MODEL`,
`*_TEMPERATURE`, `*_MAX_RETRIES`, `*_MAX_CONCURRENCY` config keys are also honored.

## Conventions when editing

- **Adding a source type:** subclass `BaseProcessor`, implement `download` +
  `extract_text` (add an `is_*_url` static classifier if URL-pattern routed), wire it into
  `KBBuilder.__init__`, the routing in `process_files_async`, and `_classify_source`; then
  export it from `__init__.py`. Add a `test_<name>_processor.py`.
- **Adding an LLM provider:** subclass `LLMClient`, implement `run_async` with the
  retry/semaphore pattern, add the auto-selection branch in `KBBuilder.__init__` and a CLI
  flag group, and export it.
- **Install is core + extras** (`setup.py`: `CORE_REQUIRES` / `EXTRAS`). Core = import +
  Gemini + web/pdf/docs/web-content. Extras = `spreadsheets` (pandas/openpyxl/ezodf),
  `youtube`, `rss`, `pptx`, `arxiv`, `openai`, `anthropic`, `markitdown`, and `all`. Any
  dep in an extra **must** be import-guarded (`try/import` + `_AVAILABLE` flag, raise an
  informative `ImportError` naming the extra at use time — see `arxiv_processor.py`,
  `spreadsheet_processor.py`, `openai_client.py`). `__init__.py`/`kb_builder.py` import
  every module eagerly, so a bare top-level `import pandas` would break the core install —
  `tests/test_optional_deps.py` guards against exactly that (runs with extras blocked).
  Modules using an optional dep in a type annotation need `from __future__ import annotations`.
- Logging uses the stdlib `logging` module (`logger = logging.getLogger(__name__)`) — no
  `print` in library code (the CLI prints only dry-run JSON).
- **Fail transparently on bad input.** `build()` validates `sources` up front via
  `_validate_sources` (raises `TypeError` with a copy-paste fix for wrong types; warns +
  suggests the closest key for unrecognized keys — keep `_KNOWN_SOURCE_KEYS` in sync when
  adding a source key). `_log_build_summary` reports per-source success/failure and
  `_warn_no_content` explains an empty result. Prefer this pattern over silently
  swallowing an error into a log line and writing an empty file.
- Keep the two `__version__`/`version=` declarations in sync.

## Gotchas

- **Don't confuse the two `knowledge_base_builder` directory levels** — imports are
  `from knowledge_base_builder.x import Y` and only resolve from the repo root.
- `ArxivProcessor.download` / `extract_text` are `@staticmethod`; most other processors'
  `download` is inherited from `BaseProcessor` and takes a `supported_extensions` list.
- **Never** reintroduce `asyncio.get_event_loop().run_until_complete(...)` — it crashes
  inside a running loop (Jupyter/Colab). All sync→async bridging goes through
  `async_utils.run_sync()`, which runs coroutines on one persistent background-thread loop
  (keeps `asyncio.Semaphore`s bound to a single loop across calls).
- Repo contains dev leftovers not meant to ship (`.coverage`, `out.md.meta.json`,
  `test_output.md`, `.env`); don't treat them as fixtures.
