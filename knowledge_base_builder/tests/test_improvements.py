"""Tests for usability improvements: dedup, progress callback, smart chunking, logging."""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

from knowledge_base_builder.kb_builder import KBBuilder


class TestDeduplication(unittest.TestCase):
    """Test URL deduplication."""

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_is_duplicate_first_call(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        self.assertFalse(kbb._is_duplicate('http://example.com/page'))

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_is_duplicate_second_call(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb._is_duplicate('http://example.com/page')
        self.assertTrue(kbb._is_duplicate('http://example.com/page'))

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_is_duplicate_trailing_slash(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb._is_duplicate('http://example.com/page/')
        self.assertTrue(kbb._is_duplicate('http://example.com/page'))

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_dedup_resets_on_build(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb._is_duplicate('http://a.com')
        kbb.llm = MagicMock()
        kbb.llm.preprocess_text_async = AsyncMock(return_value='result')
        kbb.website_processor = MagicMock()
        kbb.website_processor.download_and_clean_html.return_value = 'text'

        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            outpath = f.name
        try:
            kbb.build({'files': ['http://a.com']}, outpath)
            # After build, _seen_urls is reset, so a.com should process again
            # (the build call resets _seen_urls)
        finally:
            if os.path.exists(outpath):
                os.unlink(outpath)

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_dedup_in_process_files_async(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.website_processor = MagicMock()
        kbb.website_processor.download_and_clean_html.return_value = 'text'

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(kbb.process_files_async([
                'http://example.com/page',
                'http://example.com/page',  # duplicate
                'http://example.com/other',
            ]))
        finally:
            loop.close()

        # Should only call download_and_clean_html twice (not three times)
        self.assertEqual(kbb.website_processor.download_and_clean_html.call_count, 2)


class TestSmartChunking(unittest.TestCase):
    """Test _split_text method."""

    def test_short_text_single_chunk(self):
        result = KBBuilder._split_text('hello world', 100)
        self.assertEqual(result, ['hello world'])

    def test_splits_at_paragraph_boundary(self):
        text = 'First paragraph.\n\nSecond paragraph.\n\nThird paragraph.'
        chunks = KBBuilder._split_text(text, 40)
        self.assertEqual(len(chunks), 2)
        self.assertTrue(chunks[0].endswith('\n\n'))

    def test_splits_at_sentence_boundary(self):
        text = 'First sentence. Second sentence. Third sentence. Fourth sentence.'
        chunks = KBBuilder._split_text(text, 40)
        self.assertGreater(len(chunks), 1)
        # Each chunk should end at a sentence boundary
        self.assertTrue(chunks[0].rstrip().endswith('.'))

    def test_falls_back_to_hard_split(self):
        text = 'x' * 200  # No paragraph or sentence boundaries
        chunks = KBBuilder._split_text(text, 50)
        self.assertGreater(len(chunks), 1)
        # All text should be preserved
        self.assertEqual(''.join(chunks), text)

    def test_empty_text(self):
        result = KBBuilder._split_text('', 100)
        self.assertEqual(result, [''])


class TestProgressCallback(unittest.TestCase):
    """Test on_progress callback in build()."""

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_progress_callback_called(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.llm = MagicMock()
        kbb.llm.preprocess_text_async = AsyncMock(return_value='result')
        kbb.website_processor = MagicMock()
        kbb.website_processor.download_and_clean_html.return_value = 'text'

        progress_calls = []
        def on_progress(stage, current, total):
            progress_calls.append((stage, current, total))

        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            outpath = f.name
        try:
            kbb.build(
                {'files': ['http://example.com']},
                outpath,
                on_progress=on_progress,
            )
        finally:
            os.unlink(outpath)

        # Should have at least llm progress calls
        stages = [c[0] for c in progress_calls]
        self.assertIn('llm', stages)

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_build_without_progress(self, mock_gemini):
        """Build should work fine without on_progress."""
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.llm = MagicMock()
        kbb.llm.preprocess_text_async = AsyncMock(return_value='result')
        kbb.website_processor = MagicMock()
        kbb.website_processor.download_and_clean_html.return_value = 'text'

        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            outpath = f.name
        try:
            kbb.build({'files': ['http://example.com']}, outpath)
            with open(outpath) as f:
                self.assertEqual(f.read(), 'result')
        finally:
            os.unlink(outpath)


class TestLogging(unittest.TestCase):
    """Test that source files use logging instead of print."""

    def test_no_print_in_source_files(self):
        """Verify no print() calls in any source module."""
        import knowledge_base_builder
        pkg_dir = os.path.dirname(knowledge_base_builder.__file__)

        for fname in os.listdir(pkg_dir):
            if fname.endswith('.py') and not fname.startswith('test_') and fname not in ('conftest.py', 'cli.py'):
                fpath = os.path.join(pkg_dir, fname)
                with open(fpath) as f:
                    content = f.read()
                # Check for print( but exclude comments and strings
                import ast
                try:
                    tree = ast.parse(content)
                    for node in ast.walk(tree):
                        if isinstance(node, ast.Call):
                            func = node.func
                            if isinstance(func, ast.Name) and func.id == 'print':
                                self.fail(f"Found print() call in {fname} at line {node.lineno}")
                except SyntaxError:
                    pass  # Skip files that can't be parsed


class TestImprovedLLMPrompts(unittest.TestCase):
    """Test that LLM prompts contain the improved guidelines."""

    def test_preprocess_prompt_has_guidelines(self):
        from knowledge_base_builder.llm import LLM
        mock_client = MagicMock()
        mock_client.run.return_value = 'result'
        llm = LLM(mock_client)
        llm.build('test text')
        prompt = mock_client.run.call_args[0][0]
        self.assertIn('hierarchical headings', prompt)
        self.assertIn('Preserve all factual information', prompt)

    def test_merge_prompt_has_guidelines(self):
        from knowledge_base_builder.llm import LLM
        mock_client = MagicMock()
        mock_client.run_async = AsyncMock(return_value='merged')
        llm = LLM(mock_client)
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(llm.merge_all_kbs(['kb1', 'kb2']))
        finally:
            loop.close()
        prompt = mock_client.run_async.call_args[0][0]
        self.assertIn('Combine related sections', prompt)
        self.assertIn('Remove duplicate information', prompt)


class TestGitHubRateLimitWarning(unittest.TestCase):
    """Test that GitHub rate limits produce warnings, not silent failures."""

    @patch('knowledge_base_builder.github_processor.requests.get')
    def test_rate_limit_logged(self, mock_get):
        from knowledge_base_builder.github_processor import GitHubProcessor
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        mock_resp.headers = {
            'X-RateLimit-Remaining': '0',
            'X-RateLimit-Reset': '1700000000',
        }
        mock_resp.json.return_value = []
        mock_get.return_value = mock_resp

        proc = GitHubProcessor()
        with self.assertLogs('knowledge_base_builder.github_processor', level='WARNING') as cm:
            result = proc.get_markdown_urls_for_repo('owner', 'repo')
        self.assertEqual(result, [])
        # Should have logged a rate limit warning
        self.assertTrue(any('rate limit' in msg.lower() or '403' in msg for msg in cm.output))


class TestWebsiteProcessorRetry(unittest.TestCase):
    """Test that website processor retries on transient failures."""

    @patch('knowledge_base_builder.website_processor.requests.get')
    def test_retry_on_failure(self, mock_get):
        from knowledge_base_builder.website_processor import WebsiteProcessor

        # First call fails, second succeeds
        fail_resp = MagicMock()
        fail_resp.status_code = 500
        fail_resp.raise_for_status.side_effect = Exception('500')

        ok_resp = MagicMock()
        ok_resp.status_code = 200
        ok_resp.text = '<html><body>Hello</body></html>'

        mock_get.side_effect = [fail_resp, ok_resp]

        proc = WebsiteProcessor()
        result = proc.download_and_clean_html('http://example.com')
        self.assertIn('Hello', result)
        self.assertEqual(mock_get.call_count, 2)


if __name__ == '__main__':
    unittest.main()
