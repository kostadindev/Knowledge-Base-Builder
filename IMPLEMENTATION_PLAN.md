# Implementation Plan: Features 4-7

## Feature 4: MarkItDown Integration (Better PDF/Doc Extraction)
**Files to modify:** pdf_processor.py, document_processor.py, spreadsheet_processor.py, setup.py
**New files:** None
**Approach:**
- Try `from markitdown import MarkItDown` at module level; set `_MARKITDOWN_AVAILABLE` flag
- In extract_text methods: if available, use `MarkItDown().convert(path).text_content`
- Fall back to existing PyPDF/python-docx/pandas if not installed
- Add `extras_require={"markitdown": ["markitdown"]}` to setup.py
**Tests:** test_markitdown.py — mock MarkItDown available/unavailable, test fallback, test error handling
**Docs:** README install section, paper Software Design paragraph

## Feature 5: Chunked Output for Vector DBs
**Files to modify:** kb_builder.py, cli.py, build_metadata.py
**New files:** chunker.py
**Approach:**
- New `Chunker` class: takes list of (text, source_url) pairs, splits at paragraph/sentence boundaries
- Each chunk: `{"id": "chunk_0", "text": "...", "metadata": {"source": "url", "section": "heading", "index": 0}}`
- `output_format="chunks"` in build() — skips LLM entirely, writes JSON array
- Track `self._text_sources: List[str]` parallel to `self.text_contents` for source attribution
- Add `chunk_size` param to build() and CLI `--chunk-size`
**Tests:** test_chunker.py — chunking, section detection, source attribution, empty input
**Docs:** README section, paper mention

## Feature 6: Output Quality Validation
**Files to modify:** kb_builder.py, build_metadata.py, cli.py, __init__.py
**New files:** validator.py
**Approach:**
- `OutputValidator.validate(output_text, source_results)` returns `ValidationResult`
- Checks: non-empty, has headings, source coverage %, composite quality score (0.0-1.0)
- Score weights: non_empty=0.3, has_headings=0.2, source_coverage=0.3, word_count_adequacy=0.2
- `validate=True` on build() runs checks, adds results to metadata sidecar
- CLI: `--validate`
**Tests:** test_validator.py — each check independently, composite score, integration with build()
**Docs:** README section, paper mention

## Feature 7: Dry-Run Mode
**Files to modify:** kb_builder.py, base_processor.py, cli.py
**New files:** None
**Approach:**
- `BaseProcessor.check_accessible(url)` — HEAD request for HTTP, os.path.exists for file://
- `build(dry_run=True)` — early exit, returns dict with:
  - total_sources, accessible/inaccessible counts, sources_by_type
  - estimated_size_bytes (from Content-Length headers)
  - api_key_valid (minimal LLM call)
  - inaccessible_sources list
- Extract URL classification logic from process_files_async into `_classify_source(url)`
- CLI: `--dry-run`, pretty-prints JSON summary
**Tests:** test_dry_run.py — accessibility checks, classification, API validation, no file written
**Docs:** README section, paper mention

## Implementation Order
1. Feature 4 (MarkItDown) — self-contained, no deps on others
2. Feature 7 (Dry-run) — independent, useful cleanup of classify logic
3. Feature 5 (Chunks) — needs _text_sources tracking refactor
4. Feature 6 (Validation) — needs final output format set from Feature 5
