import asyncio
from typing import List, Dict, Any, Tuple, Optional, Callable
import os
import hashlib
import urllib.parse
import re
import time
import logging
import difflib

from knowledge_base_builder.llm_client import LLMClient
from knowledge_base_builder.build_metadata import BuildMetadata, SourceResult
from knowledge_base_builder.cache import BuildCache
from knowledge_base_builder.base_processor import BaseProcessor
from knowledge_base_builder.validator import OutputValidator
from knowledge_base_builder.async_utils import run_sync

logger = logging.getLogger(__name__)

from knowledge_base_builder.gemini_client import GeminiClient
from knowledge_base_builder.openai_client import OpenAIClient
from knowledge_base_builder.anthropic_client import AnthropicClient
from knowledge_base_builder.llm import LLM
from knowledge_base_builder.pdf_processor import PDFProcessor
from knowledge_base_builder.document_processor import DocumentProcessor
from knowledge_base_builder.spreadsheet_processor import SpreadsheetProcessor
from knowledge_base_builder.web_content_processor import WebContentProcessor
from knowledge_base_builder.website_processor import WebsiteProcessor
from knowledge_base_builder.github_processor import GitHubProcessor
from knowledge_base_builder.youtube_processor import YouTubeProcessor
from knowledge_base_builder.rss_processor import RSSProcessor
from knowledge_base_builder.jupyter_processor import JupyterProcessor
from knowledge_base_builder.presentation_processor import PresentationProcessor
from knowledge_base_builder.arxiv_processor import ArxivProcessor

class KBBuilder:
    """Main application class for building knowledge bases from various sources."""

    # Recognized ``sources`` dict keys, split by expected value type. Used to
    # give transparent feedback on mistyped keys or wrong value types.
    _LIST_SOURCE_KEYS = frozenset({
        'files', 'github_repositories', 'rss_urls',
        'pdf_urls', 'document_urls', 'spreadsheet_urls',
        'web_content_urls', 'web_urls',
    })
    _STR_SOURCE_KEYS = frozenset({'sitemap_url', 'github_username'})
    _KNOWN_SOURCE_KEYS = _LIST_SOURCE_KEYS | _STR_SOURCE_KEYS

    def __init__(self, config: Dict[str, Any], allow_no_llm: bool = False):
        """Create a builder.

        Args:
            config: Configuration dict. Must contain at least one of
                ``GOOGLE_API_KEY``, ``OPENAI_API_KEY``, or ``ANTHROPIC_API_KEY``
                unless *allow_no_llm* is True.
            allow_no_llm: When True, a missing API key is tolerated instead of
                raising; the builder can then only produce ``output_format="raw"``
                output (extracted text with no LLM structuring).
        """
        self.config = config
        self._seen_urls: set = set()  # For deduplication
        self.llm_client = None
        self.llm = None

        # Initialize the appropriate LLM client based on available API keys
        # Try providers in order: Gemini > OpenAI > Anthropic
        if 'GOOGLE_API_KEY' in config and config['GOOGLE_API_KEY']:
            self.llm_client = GeminiClient(
                api_key=config['GOOGLE_API_KEY'],
                model=config.get('GEMINI_MODEL', 'gemini-2.0-flash'),
                temperature=float(config.get('GEMINI_TEMPERATURE', 0.7)),
                max_retries=int(config.get('GEMINI_MAX_RETRIES', 3)),
                max_concurrency=int(config.get('GEMINI_MAX_CONCURRENCY', 8)),
            )
            logger.info("Using Gemini as LLM provider")
        elif 'OPENAI_API_KEY' in config and config['OPENAI_API_KEY']:
            self.llm_client = OpenAIClient(
                api_key=config['OPENAI_API_KEY'],
                model=config.get('OPENAI_MODEL', 'gpt-4o'),
                temperature=float(config.get('OPENAI_TEMPERATURE', 0.7)),
                max_retries=int(config.get('OPENAI_MAX_RETRIES', 3)),
                max_concurrency=int(config.get('OPENAI_MAX_CONCURRENCY', 8)),
            )
            logger.info("Using OpenAI as LLM provider")
        elif 'ANTHROPIC_API_KEY' in config and config['ANTHROPIC_API_KEY']:
            self.llm_client = AnthropicClient(
                api_key=config['ANTHROPIC_API_KEY'],
                model=config.get('ANTHROPIC_MODEL', 'claude-3-7-sonnet'),
                temperature=float(config.get('ANTHROPIC_TEMPERATURE', 0.7)),
                max_retries=int(config.get('ANTHROPIC_MAX_RETRIES', 3)),
                max_concurrency=int(config.get('ANTHROPIC_MAX_CONCURRENCY', 8)),
            )
            logger.info("Using Anthropic as LLM provider")
        elif allow_no_llm:
            logger.warning(
                "No LLM API key found; running in no-LLM mode. Only "
                "output_format='raw' is available."
            )
        else:
            raise ValueError(
                "No LLM API key found in config. Please provide at least one of: "
                "GOOGLE_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY"
            )

        if self.llm_client is not None:
            self.llm = LLM(self.llm_client)

        # Initialize processors
        self.pdf_processor = PDFProcessor()
        self.document_processor = DocumentProcessor()
        self.spreadsheet_processor = SpreadsheetProcessor()
        self.web_content_processor = WebContentProcessor()
        self.website_processor = WebsiteProcessor()
        self.github_processor = None
        self.youtube_processor = YouTubeProcessor()
        self.rss_processor = RSSProcessor()
        self.jupyter_processor = JupyterProcessor()
        self.presentation_processor = PresentationProcessor()
        self.arxiv_processor = ArxivProcessor()
        self.text_contents: List[str] = []
        self._text_sources: List[str] = []

    def _validate_sources(self, sources: Dict[str, Any]) -> None:
        """Validate the *sources* argument and surface likely input mistakes.

        Raises ``TypeError`` for the wrong container/value types (with a fix in
        the message) and logs a warning for unrecognized keys (usually typos),
        suggesting the closest valid key.
        """
        if not isinstance(sources, dict):
            raise TypeError(
                "sources must be a dict of source-type keys to values, e.g. "
                "{'files': ['https://example.com/doc.pdf']}. Got "
                f"{type(sources).__name__}. For a quick one-shot call, use the "
                "top-level helper: knowledge_base_builder.build('https://...', out='kb.md')."
            )

        for key, value in sources.items():
            if key not in self._KNOWN_SOURCE_KEYS:
                match = difflib.get_close_matches(key, self._KNOWN_SOURCE_KEYS, n=1)
                hint = f" Did you mean '{match[0]}'?" if match else ""
                logger.warning(
                    "Ignoring unrecognized sources key %r.%s Valid keys: %s",
                    key, hint, ", ".join(sorted(self._KNOWN_SOURCE_KEYS)),
                )
                continue

            if value is None:
                continue

            if key in self._LIST_SOURCE_KEYS:
                if isinstance(value, str):
                    raise TypeError(
                        f"sources['{key}'] must be a list of strings, but got a "
                        f"single string. Wrap it in a list: "
                        f"{{'{key}': [{value!r}]}}."
                    )
                if not isinstance(value, (list, tuple)):
                    raise TypeError(
                        f"sources['{key}'] must be a list of strings, got "
                        f"{type(value).__name__}."
                    )
                bad = next((v for v in value if not isinstance(v, str)), None)
                if bad is not None:
                    raise TypeError(
                        f"sources['{key}'] must contain only strings; found "
                        f"{type(bad).__name__}: {bad!r}."
                    )
            else:  # single-string keys
                if not isinstance(value, str):
                    raise TypeError(
                        f"sources['{key}'] must be a single string (a URL or name), "
                        f"got {type(value).__name__}."
                    )

    def _warn_no_content(self) -> None:
        """Emit an actionable warning when no source produced any text."""
        attempted = self._build_meta.sources
        if not attempted:
            logger.warning(
                "No content collected: no sources were provided (or all keys were "
                "unrecognized). Provide e.g. sources={'files': ['https://...']}, or "
                "run with dry_run=True to validate your inputs."
            )
        else:
            logger.warning(
                "No content collected: all %d source(s) failed or were empty (see the "
                "failures listed above). Check that URLs/paths are reachable and that the "
                "required extras are installed (e.g. [spreadsheets], [youtube]).",
                len(attempted),
            )

    def _log_build_summary(self) -> None:
        """Log a human-readable summary of per-source extraction results."""
        results = self._build_meta.sources
        if not results:
            return
        succeeded = [s for s in results if s.success]
        failed = [s for s in results if not s.success]
        logger.info(
            "Source summary: %d of %d succeeded, %d failed.",
            len(succeeded), len(results), len(failed),
        )
        for s in failed:
            logger.warning(
                "  Failed [%s] %s -> %s",
                s.source_type, s.url, s.error_message or "unknown error",
            )

    def _is_duplicate(self, url: str) -> bool:
        """Check if a URL has already been processed. Returns True if duplicate."""
        normalized = url.strip().rstrip('/')
        if normalized in self._seen_urls:
            logger.debug("Skipping duplicate URL: %s", url)
            return True
        self._seen_urls.add(normalized)
        return False

    def build(
        self,
        sources: Dict[str, Any] = None,
        output_file: str = "final_knowledge_base.md",
        on_progress: Optional[Callable[[str, int, int], None]] = None,
        output_format: str = "markdown",
        project_name: Optional[str] = None,
        metadata: bool = True,
        incremental: bool = False,
        cache_dir: Optional[str] = None,
        dry_run: bool = False,
        chunk_size: int = 1000,
        validate: bool = False,
    ) -> Any:
        """Build a knowledge base from the provided sources.

        Args:
            sources: Dictionary of source URLs/paths grouped by type.
            output_file: Path to write the final knowledge base.
            on_progress: Optional callback ``(stage, current, total)``.
            output_format: ``"markdown"`` (default), ``"llms_txt"`` for
                llmstxt.org spec-compliant output, ``"chunks"`` for
                vector-DB-ready JSON chunks, or ``"raw"`` for the extracted
                text with no LLM structuring (works without an API key).
            project_name: Project name for the H1 heading (llms_txt mode).
            metadata: Write a ``.meta.json`` sidecar file (default True).
            incremental: Reuse cached extractions for unchanged sources.
            cache_dir: Directory for incremental build cache
                (default ``.kbb_cache``).
            dry_run: If True, validate sources and API key without
                processing. Returns a summary dict instead of a file path.
            chunk_size: Maximum number of characters per chunk when
                *output_format* is ``"chunks"`` (default 1000).
            validate: Run output quality validation and include results
                in the metadata sidecar (default False).

        Returns:
            The *output_file* path, or a summary dict when *dry_run* is True.
        """
        if output_format not in ("markdown", "llms_txt", "chunks", "raw"):
            raise ValueError(
                "output_format must be 'markdown', 'llms_txt', 'chunks', or "
                f"'raw', got '{output_format}'"
            )

        # No LLM configured: fall back to raw extraction (no structuring).
        if self.llm_client is None and output_format in ("markdown", "llms_txt"):
            logger.warning(
                "No LLM client configured; falling back to output_format='raw'."
            )
            output_format = "raw"

        # Normalize and validate the sources argument up front so mistyped keys
        # or wrong value types fail loudly instead of silently doing nothing.
        sources = sources or {}
        self._validate_sources(sources)

        if dry_run:
            return self._dry_run(sources)

        total_start_time = time.time()
        logger.info("Starting Knowledge Base Builder pipeline...")
        self.text_contents = []
        self._text_sources = []
        self._seen_urls = set()

        # Metadata tracking
        self._build_meta = BuildMetadata(
            llm_provider=(
                self.llm_client.__class__.__name__ if self.llm_client else "none"
            ),
            llm_model=str(getattr(self.llm_client, 'model', 'none')),
            llm_temperature=float(getattr(self.llm_client, 'temperature', 0.0)),
        )

        # Incremental cache
        self._cache: Optional[BuildCache] = None
        if incremental:
            self._cache = BuildCache(cache_dir or ".kbb_cache")

        def _progress(stage: str, current: int, total: int):
            if on_progress:
                on_progress(stage, current, total)

        # --- unified file sources ---
        if files := sources.get('files', []):
            files_start = time.time()
            run_sync(self.process_files_async(files, _progress))
            logger.info("Files processing completed in %.2fs", time.time() - files_start)
        else:
            logger.info("No files provided for processing")

        # --- legacy sources ---
        legacy_start = time.time()
        self._process_legacy_sources(sources)
        logger.info("Legacy sources processing completed in %.2fs", time.time() - legacy_start)

        # --- sitemap ---
        if sitemap := sources.get('sitemap_url'):
            sitemap_start = time.time()
            self.process_websites(sitemap)
            logger.info("Sitemap processing completed in %.2fs", time.time() - sitemap_start)

        # --- GitHub ---
        github_repos = sources.get('github_repositories', [])
        github_username = sources.get('github_username')

        if github_username:
            logger.info("Processing all repositories for GitHub user: %s", github_username)
            gh_start = time.time()
            self.process_github(github_username)
            logger.info("GitHub user processing completed in %.2fs", time.time() - gh_start)
        elif github_repos:
            gh_start = time.time()
            self.process_github_repos(github_repos)
            logger.info("GitHub repositories processing completed in %.2fs", time.time() - gh_start)

        # Save cache manifest
        if self._cache:
            self._cache.save_manifest()

        # Transparent per-source outcome report
        self._log_build_summary()

        # --- Chunked output (vector DB mode) ---
        if output_format == "chunks":
            import json as _json
            from knowledge_base_builder.chunker import Chunker

            if not self.text_contents:
                self._warn_no_content()
                with open(output_file, "w", encoding="utf-8") as f:
                    _json.dump([], f, indent=2)
            else:
                chunker = Chunker(chunk_size=chunk_size)
                pairs = list(zip(self.text_contents, self._text_sources))
                result_chunks = chunker.chunk_texts(pairs)
                with open(output_file, "w", encoding="utf-8") as f:
                    _json.dump(result_chunks, f, indent=2)
                logger.info("Wrote %d chunks to: %s", len(result_chunks), output_file)

            total_elapsed = time.time() - total_start_time
            if metadata:
                self._build_meta.total_processing_time_seconds = total_elapsed
                self._build_meta.write_json(output_file + ".meta.json")
            logger.info("Total processing time: %.2fs", total_elapsed)
            return output_file

        # --- LLM processing ---
        if not self.text_contents:
            self._warn_no_content()
            if metadata:
                self._build_meta.total_processing_time_seconds = time.time() - total_start_time
                self._build_meta.write_json(output_file + ".meta.json")
            return output_file

        # Save raw text for llms-full.txt before LLM processing
        raw_combined_text = "\n\n---\n\n".join(self.text_contents)

        # --- Raw output (no LLM structuring) ---
        if output_format == "raw":
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(raw_combined_text)
            logger.info("Raw KB written to: %s", output_file)
            total_elapsed = time.time() - total_start_time
            if metadata:
                self._build_meta.total_processing_time_seconds = total_elapsed
                self._build_meta.compute_output_stats(raw_combined_text)
                self._build_meta.write_json(output_file + ".meta.json")
            logger.info("Total processing time: %.2fs", total_elapsed)
            return output_file

        logger.info("Processing all collected content through LLM...")
        _progress("llm", 0, 1)
        llm_start = time.time()

        llm_chunk_size = 20000 * 4  # ~20K tokens
        chunks = self._split_text(raw_combined_text, llm_chunk_size)

        logger.info("Processing %d chunk(s) of text...", len(chunks))
        processed_chunks = []

        # Select the appropriate LLM method based on output format
        if output_format == "llms_txt":
            async def _process_chunk(chunk_text):
                return await self.llm.preprocess_text_llms_txt_async(chunk_text, project_name)
        else:
            async def _process_chunk(chunk_text):
                return await self.llm.preprocess_text_async(chunk_text)

        for i, chunk in enumerate(chunks, 1):
            logger.info("  Processing chunk %d/%d...", i, len(chunks))
            _progress("llm", i, len(chunks))
            try:
                processed = run_sync(_process_chunk(chunk))
                processed_chunks.append(processed)
            except Exception as e:
                logger.error("Error processing chunk %d: %s", i, e)
                sub_size = llm_chunk_size // 2
                sub_chunks = self._split_text(chunk, sub_size)
                for j, sub in enumerate(sub_chunks, 1):
                    try:
                        processed = run_sync(_process_chunk(sub))
                        processed_chunks.append(processed)
                    except Exception as sub_e:
                        logger.error("Error processing sub-chunk %d of chunk %d: %s", j, i, sub_e)

        processed_content = "\n\n".join(processed_chunks)

        logger.info("LLM processing completed in %.2fs", time.time() - llm_start)

        self.text_contents = [processed_content]

        # --- Write output ---
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(processed_content)
        logger.info("Final KB written to: %s", output_file)

        # Write llms-full.txt companion (full raw text)
        if output_format == "llms_txt":
            full_path = output_file.replace(".txt", "-full.txt") if output_file.endswith(".txt") else output_file + ".full.txt"
            with open(full_path, "w", encoding="utf-8") as f:
                f.write(raw_combined_text)
            logger.info("Full text written to: %s", full_path)

        # --- Output quality validation ---
        if validate:
            validator = OutputValidator()
            validation_result = validator.validate(
                processed_content, self._build_meta.sources
            )
            logger.info(
                "Output quality score: %.2f", validation_result.quality_score
            )
            self._build_meta.validation = validation_result.to_dict()

        # --- Metadata sidecar ---
        total_elapsed = time.time() - total_start_time
        if metadata:
            self._build_meta.total_processing_time_seconds = total_elapsed
            self._build_meta.compute_output_stats(processed_content)
            self._build_meta.write_json(output_file + ".meta.json")

        logger.info("Total processing time: %.2fs", total_elapsed)
        return output_file

    @staticmethod
    def _split_text(text: str, max_chars: int) -> List[str]:
        """Split text into chunks at paragraph boundaries where possible."""
        if len(text) <= max_chars:
            return [text]

        chunks: List[str] = []
        while text:
            if len(text) <= max_chars:
                chunks.append(text)
                break
            # Try to break at a paragraph boundary
            split_at = text.rfind('\n\n', 0, max_chars)
            if split_at == -1 or split_at < max_chars // 2:
                # Fall back to sentence boundary
                split_at = text.rfind('. ', 0, max_chars)
            if split_at == -1 or split_at < max_chars // 2:
                split_at = max_chars
            else:
                split_at += 2  # include the delimiter
            chunks.append(text[:split_at])
            text = text[split_at:]
        return chunks

    # ------------------------------------------------------------------
    # Dry-run helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _classify_source(url: str) -> str:
        """Return a source-type string based on URL pattern or file extension."""
        # URL-pattern-based checks first
        if YouTubeProcessor.is_youtube_url(url):
            return "youtube"
        if ArxivProcessor.is_arxiv_url(url):
            return "arxiv"
        if RSSProcessor.is_rss_url(url):
            return "rss"

        # Extension-based checks
        clean = url.split('?')[0].split('#')[0]
        ext = os.path.splitext(clean)[1].lower()

        if ext == '.pdf':
            return "pdf"
        if ext in ('.docx', '.txt', '.md', '.rtf'):
            return "document"
        if ext in ('.csv', '.tsv', '.xlsx', '.ods'):
            return "spreadsheet"
        if ext in ('.html', '.xml', '.json', '.yaml', '.yml'):
            return "web_content"
        if ext == '.ipynb':
            return "jupyter"
        if ext == '.pptx':
            return "presentation"
        if ext in ('.rss', '.atom'):
            return "rss"
        return "web"

    def _dry_run(self, sources: Dict[str, Any]) -> Dict[str, Any]:
        """Validate sources and API key without processing anything.

        Returns a summary dict.
        """
        # Collect all URLs from every source key
        all_urls: List[str] = []
        for key in ('files', 'pdf_urls', 'document_urls', 'spreadsheet_urls',
                     'web_content_urls', 'web_urls', 'rss_urls'):
            all_urls.extend(sources.get(key) or [])

        if sitemap := sources.get('sitemap_url'):
            all_urls.append(sitemap)

        for repo in sources.get('github_repositories') or []:
            # Normalise to a browsable URL so the HEAD check is meaningful
            if not repo.startswith(('http://', 'https://')):
                all_urls.append(f"https://github.com/{repo}")
            else:
                all_urls.append(repo)

        # Check accessibility concurrently via asyncio.to_thread
        async def _check_all():
            tasks = [
                asyncio.to_thread(BaseProcessor.check_accessible, u)
                for u in all_urls
            ]
            return await asyncio.gather(*tasks)

        results = run_sync(_check_all())

        accessible = 0
        inaccessible = 0
        inaccessible_sources: List[Dict[str, Any]] = []
        sources_by_type: Dict[str, int] = {}

        for url, (ok, status_code, error) in zip(all_urls, results):
            stype = self._classify_source(url)
            sources_by_type[stype] = sources_by_type.get(stype, 0) + 1
            if ok:
                accessible += 1
            else:
                inaccessible += 1
                inaccessible_sources.append({
                    "url": url,
                    "status_code": status_code,
                    "error": error,
                })

        # Validate API key with a minimal LLM call
        api_key_valid = False
        try:
            self.llm_client.run("Respond with OK")
            api_key_valid = True
        except Exception:
            pass

        return {
            "total_sources": len(all_urls),
            "accessible": accessible,
            "inaccessible": inaccessible,
            "sources_by_type": sources_by_type,
            "inaccessible_sources": inaccessible_sources,
            "api_key_valid": api_key_valid,
            "llm_provider": self.llm_client.__class__.__name__,
        }

    def _process_legacy_sources(self, sources: Dict[str, Any]) -> None:
        """Process legacy source format for backward compatibility."""
        for key, label, method in [
            ('pdf_urls', 'PDF documents', self.process_pdfs),
            ('document_urls', 'documents', self.process_documents),
            ('spreadsheet_urls', 'spreadsheets', self.process_spreadsheets),
            ('web_content_urls', 'web content files', self.process_web_content),
            ('web_urls', 'web pages', self.process_web_urls),
            ('rss_urls', 'RSS feeds', self.process_rss_feeds),
        ]:
            urls = sources.get(key, [])
            if urls:
                logger.info("Processing %d %s (legacy format)...", len(urls), label)
                method(urls)

    async def process_files_async(self, files: List[str], progress_fn=None) -> None:
        """Process files and URLs concurrently based on their type."""
        tasks = []
        for idx, url in enumerate(files):
            if self._is_duplicate(url):
                continue
            if progress_fn:
                progress_fn("files", idx + 1, len(files))
            try:
                # Check if this is a local file path (not starting with http/https and containing a path separator)
                if not url.startswith(('http://', 'https://', 'file://')) and (os.path.sep in url or os.path.exists(url)):
                    # Convert local path to file:// URL format for internal processing
                    local_path = os.path.abspath(url)
                    
                    # Handle Windows paths differently
                    if os.name == 'nt':  # Windows
                        # For Windows, ensure path starts with / and replace backslashes with forward slashes
                        local_path = local_path.replace('\\', '/')
                        if local_path[1] == ':':  # Has drive letter like C:
                            url = f"file:///{local_path}"
                        else:
                            url = f"file:///{local_path}"
                    else:
                        # For Unix-like systems
                        url = f"file://{urllib.parse.quote(local_path)}"
                    
                # URL-pattern-based routing (before extension check)
                if YouTubeProcessor.is_youtube_url(url):
                    tasks.append(self._process_youtube_async(url))
                elif ArxivProcessor.is_arxiv_url(url):
                    tasks.append(self._process_arxiv_async(url))
                elif RSSProcessor.is_rss_url(url):
                    tasks.append(self._process_rss_async(url))
                # Extension-based routing
                elif url.startswith(('http://', 'https://')) and not any(url.lower().endswith(ext) for ext in
                                                                   ['.pdf', '.docx', '.txt', '.md', '.rtf',
                                                                    '.csv', '.tsv', '.xlsx', '.ods',
                                                                    '.html', '.xml', '.json', '.yaml', '.yml',
                                                                    '.ipynb', '.pptx', '.rss', '.atom']):
                    tasks.append(self._process_web_url_async(url))
                else:
                    file_ext = os.path.splitext(url)[1].lower()

                    if file_ext == '.pdf':
                        tasks.append(self._process_pdf_async(url))
                    elif file_ext in ['.docx', '.txt', '.md', '.rtf']:
                        tasks.append(self._process_document_async(url))
                    elif file_ext in ['.csv', '.tsv', '.xlsx', '.ods']:
                        tasks.append(self._process_spreadsheet_async(url))
                    elif file_ext in ['.html', '.xml', '.json', '.yaml', '.yml']:
                        tasks.append(self._process_web_content_async(url))
                    elif file_ext == '.ipynb':
                        tasks.append(self._process_jupyter_async(url))
                    elif file_ext == '.pptx':
                        tasks.append(self._process_presentation_async(url))
                    elif file_ext in ['.rss', '.atom']:
                        tasks.append(self._process_rss_async(url))
                    else:
                        tasks.append(self._process_web_url_async(url))
            except Exception as e:
                logger.error("Error processing file: %s - %s", url, e)
        
        # Wait for all tasks to complete
        if tasks:
            try:
                await asyncio.gather(*tasks)
            except Exception as e:
                logger.error("Error during async processing: %s", e)
                # Continue with other files even if one fails
                pass

    async def _process_with_processor_async(self, url: str, processor, source_type: str) -> None:
        """Generic async processor: download, extract, track metadata, use cache."""
        result = SourceResult(url=url, source_type=source_type)
        start_time = time.time()
        try:
            logger.info("%s: %s", source_type.capitalize(), url)
            path = await asyncio.to_thread(processor.download, url)

            # Incremental cache check
            if self._cache:
                with open(path, "rb") as fh:
                    content_hash = BuildCache.hash_content(fh.read())
                cached = self._cache.get_cached_text(url, content_hash)
                if cached is not None:
                    logger.info("  Cache hit for %s", url)
                    result.cache_hit = True
                    result.word_count = len(cached.split())
                    result.success = True
                    if cached.strip():
                        self.text_contents.append(cached)
                        self._text_sources.append(url)
                    result.extraction_time_seconds = time.time() - start_time
                    self._build_meta.add_source(result)
                    return

            text = await asyncio.to_thread(processor.extract_text, path)

            if self._cache:
                self._cache.update_entry(url, content_hash, text)

            if text.strip():
                self.text_contents.append(text)
                self._text_sources.append(url)

            result.word_count = len(text.split())
            result.success = True
        except Exception as e:
            logger.error("Error processing %s %s: %s", source_type, url, e)
            result.error_message = str(e)
        finally:
            result.extraction_time_seconds = time.time() - start_time
            self._build_meta.add_source(result)

    async def _process_pdf_async(self, url: str) -> None:
        await self._process_with_processor_async(url, self.pdf_processor, "pdf")

    async def _process_document_async(self, url: str) -> None:
        await self._process_with_processor_async(url, self.document_processor, "document")

    async def _process_spreadsheet_async(self, url: str) -> None:
        await self._process_with_processor_async(url, self.spreadsheet_processor, "spreadsheet")

    async def _process_web_content_async(self, url: str) -> None:
        await self._process_with_processor_async(url, self.web_content_processor, "web_content")

    async def _process_web_url_async(self, url: str) -> None:
        """Process a web URL asynchronously (no download/extract split)."""
        result = SourceResult(url=url, source_type="web")
        start_time = time.time()
        try:
            logger.info("Website: %s", url)
            text = await asyncio.to_thread(self.website_processor.download_and_clean_html, url)
            if text.strip():
                self.text_contents.append(text)
                self._text_sources.append(url)
            result.word_count = len(text.split())
            result.success = True
        except Exception as e:
            logger.error("Error processing website %s: %s", url, e)
            result.error_message = str(e)
        finally:
            result.extraction_time_seconds = time.time() - start_time
            self._build_meta.add_source(result)

    async def _process_youtube_async(self, url: str) -> None:
        await self._process_with_processor_async(url, self.youtube_processor, "youtube")

    async def _process_rss_async(self, url: str) -> None:
        await self._process_with_processor_async(url, self.rss_processor, "rss")

    async def _process_jupyter_async(self, url: str) -> None:
        await self._process_with_processor_async(url, self.jupyter_processor, "jupyter")

    async def _process_presentation_async(self, url: str) -> None:
        await self._process_with_processor_async(url, self.presentation_processor, "presentation")

    async def _process_arxiv_async(self, url: str) -> None:
        await self._process_with_processor_async(url, self.arxiv_processor, "arxiv")

    def process_pdfs(self, pdf_urls: List[str]) -> None:
        """Process and build knowledge bases from PDFs."""
        for url in pdf_urls:
            try:
                self._process_pdf(url)
            except Exception as e:
                logger.error("PDF error: %s", e)

    def process_documents(self, document_urls: List[str]) -> None:
        """Process and build knowledge bases from documents (.docx, .txt, .md, .rtf)."""
        for url in document_urls:
            try:
                self._process_document(url)
            except Exception as e:
                logger.error("Document error: %s", e)

    def process_spreadsheets(self, spreadsheet_urls: List[str]) -> None:
        """Process and build knowledge bases from spreadsheets (.csv, .tsv, .xlsx, .ods)."""
        for url in spreadsheet_urls:
            try:
                self._process_spreadsheet(url)
            except Exception as e:
                logger.error("Spreadsheet error: %s", e)

    def process_web_content(self, web_content_urls: List[str]) -> None:
        """Process and build knowledge bases from web content files (.html, .xml, .json, .yaml/.yml)."""
        for url in web_content_urls:
            try:
                self._process_web_content(url)
            except Exception as e:
                logger.error("Web content error: %s", e)

    def process_web_urls(self, web_urls: List[str]) -> None:
        """Process and build knowledge bases from individual web URLs."""
        for url in web_urls:
            try:
                self._process_web_url(url)
            except Exception as e:
                logger.error("Website error: %s", e)

    def process_rss_feeds(self, rss_urls: List[str]) -> None:
        """Process and extract content from RSS/Atom feeds."""
        for url in rss_urls:
            try:
                text = self.rss_processor.extract_text(url)
                if text.strip():
                    self.text_contents.append(text)
                    self._text_sources.append(url)
            except Exception as e:
                logger.error("RSS feed error: %s", e)

    def _process_web_url(self, url: str) -> None:
        """Process a web URL synchronously."""
        logger.info("Website: %s", url)
        start_time = time.time()
        
        download_start = time.time()
        text = self.website_processor.download_and_clean_html(url)
        download_end = time.time()
        logger.debug("Download and clean: %s seconds", round(download_end - download_start, 2))
        
        if text.strip():
            self.text_contents.append(text)  # Changed from kbs.append(self.llm.build(text))
        
        end_time = time.time()
        logger.debug("Total website processing: %s seconds", round(end_time - start_time, 2))

    def process_websites(self, sitemap_url: str) -> None:
        """Process and build knowledge bases from websites."""
        try:
            logger.info("Sitemap: %s", sitemap_url)
            sitemap_start = time.time()
            urls = self.website_processor.get_urls_from_sitemap(sitemap_url)
            sitemap_end = time.time()
            logger.debug("Sitemap fetching: %s seconds", round(sitemap_end - sitemap_start, 2))
            
            for url in urls:
                try:
                    self._process_web_url(url)
                except Exception as e:
                    logger.error("Site error: %s", e)
        except Exception as e:
            logger.error("Sitemap load error: %s", e)

    def _parse_github_repo_url(self, repo_url: str) -> Tuple[str, str]:
        """
        Parse a GitHub repository URL or username/repo string to extract the username and repo name.
        
        Supports formats:
        - username/repo
        - https://github.com/username/repo
        - http://github.com/username/repo
        - github.com/username/repo
        
        Returns a tuple of (username, repo_name)
        """
        # Pattern to match GitHub URLs or username/repo format
        github_pattern = r"(?:https?://)?(?:www\.)?github\.com/([^/]+)/([^/]+)"
        simple_pattern = r"^([^/]+)/([^/]+)$"
        
        # Try to match a full GitHub URL first
        url_match = re.match(github_pattern, repo_url)
        if url_match:
            return url_match.group(1), url_match.group(2)
        
        # Try to match the simpler username/repo format
        simple_match = re.match(simple_pattern, repo_url)
        if simple_match:
            return simple_match.group(1), simple_match.group(2)
            
        # If neither format matches, raise an error
        raise ValueError(f"Invalid GitHub repository format: {repo_url}. Expected format: username/repo or https://github.com/username/repo")
    
    def process_github_repos(self, github_repos: List[str]) -> None:
        """Process and build knowledge bases from GitHub repositories."""
        if not github_repos:
            logger.warning("GitHub processing skipped - no repositories provided")
            return
            
        # Initialize GitHub processor if not already done
        if not self.github_processor:
            self.github_processor = GitHubProcessor(token=self.config.get('GITHUB_API_KEY'))
        
        for repo in github_repos:
            try:
                logger.info("Processing GitHub repository: %s", repo)
                repo_start_time = time.time()
                
                try:
                    # Parse repository URL to extract username and repo name
                    username, repo_name = self._parse_github_repo_url(repo)
                    
                    # Get markdown files from the specific repo
                    md_urls_start = time.time()
                    md_urls = self.github_processor.get_markdown_urls_for_repo(username, repo_name)
                    md_urls_end = time.time()
                    logger.debug("Fetching markdown URLs: %s seconds", round(md_urls_end - md_urls_start, 2))
                    
                    if not md_urls:
                        logger.warning("No markdown files found in repository %s/%s", username, repo_name)
                        continue
                        
                    logger.info("Found %d markdown files", len(md_urls))
                    
                    for url in md_urls:
                        try:
                            logger.info("GitHub MD: %s", url)
                            url_start = time.time()
                            
                            download_start = time.time()
                            text = self.github_processor.download_markdown(url)
                            download_end = time.time()
                            logger.debug("Markdown download: %s seconds", round(download_end - download_start, 2))
                            
                            if text.strip():
                                self.text_contents.append(text)  # Changed from kbs.append(self.llm.build(text))
                            
                            url_end = time.time()
                            logger.debug("Total markdown processing: %s seconds", round(url_end - url_start, 2))
                        except Exception as e:
                            logger.error("Markdown error: %s", e)
                except ValueError as e:
                    logger.error("%s", e)
                
                repo_end_time = time.time()
                logger.debug("Total repository processing: %s seconds", round(repo_end_time - repo_start_time, 2))
            except Exception as e:
                logger.error("GitHub repository error: %s", e)
                
    # Keep the old process_github method for backward compatibility
    def process_github(self, github_username: str = None) -> None:
        """
        Process and build knowledge bases from GitHub markdown files.
        
        Note: This method is deprecated. Use process_github_repos instead.
        """
        if not github_username:
            logger.warning("GitHub processing skipped - no username provided")
            return
            
        logger.warning("process_github is deprecated. Use process_github_repos instead.")
        
        # Process the user's repositories in the new way
        repos = [f"{github_username}/{repo}" for repo in self._get_user_repos(github_username)]
        self.process_github_repos(repos)
    
    def _get_user_repos(self, username: str) -> List[str]:
        """Get a list of repository names for a user."""
        # Initialize GitHub processor if needed
        if not self.github_processor:
            self.github_processor = GitHubProcessor(
                username=username, 
                token=self.config.get('GITHUB_API_KEY')
            )
            
        try:
            return self.github_processor.get_user_repos()
        except Exception as e:
            logger.error("Error fetching user repositories: %s", e)
            return []

    def build_final_kb(self, output_path: str = "final_knowledge_base.md") -> None:
        """Write the final knowledge base to file."""
        if not self.text_contents:
            logger.warning("No content collected.")
            return

        write_start = time.time()
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(self.text_contents[0])  # Write the processed content
        write_end = time.time()
        logger.info("File writing completed in %s seconds", round(write_end - write_start, 2))

        logger.info("Final KB written to: %s", output_path) 