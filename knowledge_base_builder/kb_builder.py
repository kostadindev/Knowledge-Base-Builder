import asyncio
from typing import List, Dict, Any, Tuple, Optional, Callable
import os
import hashlib
import urllib.parse
import re
import time
import logging

from knowledge_base_builder.llm_client import LLMClient
from knowledge_base_builder.build_metadata import BuildMetadata, SourceResult
from knowledge_base_builder.cache import BuildCache
from knowledge_base_builder.base_processor import BaseProcessor

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

class KBBuilder:
    """Main application class for building knowledge bases from various sources."""
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self._seen_urls: set = set()  # For deduplication

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
        else:
            raise ValueError(
                "No LLM API key found in config. Please provide at least one of: "
                "GOOGLE_API_KEY, OPENAI_API_KEY, or ANTHROPIC_API_KEY"
            )

        self.llm = LLM(self.llm_client)

        # Initialize processors
        self.pdf_processor = PDFProcessor()
        self.document_processor = DocumentProcessor()
        self.spreadsheet_processor = SpreadsheetProcessor()
        self.web_content_processor = WebContentProcessor()
        self.website_processor = WebsiteProcessor()
        self.github_processor = None
        self.text_contents: List[str] = []

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
    ) -> str:
        """Build a knowledge base from the provided sources.

        Args:
            sources: Dictionary of source URLs/paths grouped by type.
            output_file: Path to write the final knowledge base.
            on_progress: Optional callback ``(stage, current, total)``.
            output_format: ``"markdown"`` (default) or ``"llms_txt"`` for
                llmstxt.org spec-compliant output.
            project_name: Project name for the H1 heading (llms_txt mode).
            metadata: Write a ``.meta.json`` sidecar file (default True).
            incremental: Reuse cached extractions for unchanged sources.
            cache_dir: Directory for incremental build cache
                (default ``.kbb_cache``).

        Returns:
            The *output_file* path.
        """
        if output_format not in ("markdown", "llms_txt"):
            raise ValueError(f"output_format must be 'markdown' or 'llms_txt', got '{output_format}'")

        total_start_time = time.time()
        logger.info("Starting Knowledge Base Builder pipeline...")
        self.text_contents = []
        self._seen_urls = set()
        sources = sources or {}

        # Metadata tracking
        self._build_meta = BuildMetadata(
            llm_provider=self.llm_client.__class__.__name__,
            llm_model=str(getattr(self.llm_client, 'model', 'unknown')),
            llm_temperature=float(getattr(self.llm_client, 'temperature', 0.7)),
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
            asyncio.get_event_loop().run_until_complete(
                self.process_files_async(files, _progress)
            )
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

        # --- LLM processing ---
        if not self.text_contents:
            logger.warning("No content collected from any source.")
            if metadata:
                self._build_meta.total_processing_time_seconds = time.time() - total_start_time
                self._build_meta.write_json(output_file + ".meta.json")
            return output_file

        # Save raw text for llms-full.txt before LLM processing
        raw_combined_text = "\n\n---\n\n".join(self.text_contents)

        logger.info("Processing all collected content through LLM...")
        _progress("llm", 0, 1)
        llm_start = time.time()

        chunk_size = 20000 * 4  # ~20K tokens
        chunks = self._split_text(raw_combined_text, chunk_size)

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
                processed = asyncio.get_event_loop().run_until_complete(
                    _process_chunk(chunk)
                )
                processed_chunks.append(processed)
            except Exception as e:
                logger.error("Error processing chunk %d: %s", i, e)
                sub_size = chunk_size // 2
                sub_chunks = self._split_text(chunk, sub_size)
                for j, sub in enumerate(sub_chunks, 1):
                    try:
                        processed = asyncio.get_event_loop().run_until_complete(
                            _process_chunk(sub)
                        )
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

    def _process_legacy_sources(self, sources: Dict[str, Any]) -> None:
        """Process legacy source format for backward compatibility."""
        for key, label, method in [
            ('pdf_urls', 'PDF documents', self.process_pdfs),
            ('document_urls', 'documents', self.process_documents),
            ('spreadsheet_urls', 'spreadsheets', self.process_spreadsheets),
            ('web_content_urls', 'web content files', self.process_web_content),
            ('web_urls', 'web pages', self.process_web_urls),
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
                    
                # Determine if this is a web URL or file path
                if url.startswith(('http://', 'https://')) and not any(url.lower().endswith(ext) for ext in 
                                                                   ['.pdf', '.docx', '.txt', '.md', '.rtf', 
                                                                    '.csv', '.tsv', '.xlsx', '.ods',
                                                                    '.html', '.xml', '.json', '.yaml', '.yml']):
                    # Handle as a web URL
                    tasks.append(self._process_web_url_async(url))
                else:
                    # Handle based on file extension
                    file_ext = os.path.splitext(url)[1].lower()
                    
                    if file_ext == '.pdf':
                        tasks.append(self._process_pdf_async(url))
                    elif file_ext in ['.docx', '.txt', '.md', '.rtf']:
                        tasks.append(self._process_document_async(url))
                    elif file_ext in ['.csv', '.tsv', '.xlsx', '.ods']:
                        tasks.append(self._process_spreadsheet_async(url))
                    elif file_ext in ['.html', '.xml', '.json', '.yaml', '.yml']:
                        tasks.append(self._process_web_content_async(url))
                    else:
                        # Try to process as a web URL if extension is unknown
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
                    result.extraction_time_seconds = time.time() - start_time
                    self._build_meta.add_source(result)
                    return

            text = await asyncio.to_thread(processor.extract_text, path)

            if self._cache:
                self._cache.update_entry(url, content_hash, text)

            if text.strip():
                self.text_contents.append(text)

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
            result.word_count = len(text.split())
            result.success = True
        except Exception as e:
            logger.error("Error processing website %s: %s", url, e)
            result.error_message = str(e)
        finally:
            result.extraction_time_seconds = time.time() - start_time
            self._build_meta.add_source(result)

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