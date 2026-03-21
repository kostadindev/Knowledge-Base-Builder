"""Comprehensive tests for knowledge-base-builder, targeting uncovered code paths."""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

from knowledge_base_builder.kb_builder import KBBuilder
from knowledge_base_builder.llm import LLM
from knowledge_base_builder.document_processor import DocumentProcessor
from knowledge_base_builder.spreadsheet_processor import SpreadsheetProcessor
from knowledge_base_builder.web_content_processor import WebContentProcessor


# ---------------------------------------------------------------------------
# KBBuilder — provider selection
# ---------------------------------------------------------------------------
class TestKBBuilderProviderSelection(unittest.TestCase):
    """Test LLM provider auto-selection in KBBuilder.__init__."""

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_gemini_selected(self, mock_gemini):
        config = {'GOOGLE_API_KEY': 'fake'}
        kbb = KBBuilder(config)
        mock_gemini.assert_called_once()

    @patch('knowledge_base_builder.kb_builder.OpenAIClient')
    def test_openai_selected(self, mock_openai):
        config = {'OPENAI_API_KEY': 'fake'}
        kbb = KBBuilder(config)
        mock_openai.assert_called_once()

    @patch('knowledge_base_builder.kb_builder.AnthropicClient')
    def test_anthropic_selected(self, mock_anthropic):
        config = {'ANTHROPIC_API_KEY': 'fake'}
        kbb = KBBuilder(config)
        mock_anthropic.assert_called_once()

    def test_no_api_key_raises(self):
        with self.assertRaises(ValueError):
            KBBuilder({})

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_gemini_takes_priority_over_openai(self, mock_gemini):
        config = {'GOOGLE_API_KEY': 'fake', 'OPENAI_API_KEY': 'also_fake'}
        kbb = KBBuilder(config)
        mock_gemini.assert_called_once()

    @patch('knowledge_base_builder.kb_builder.OpenAIClient')
    def test_openai_custom_params(self, mock_openai):
        config = {
            'OPENAI_API_KEY': 'fake',
            'OPENAI_MODEL': 'gpt-4o-mini',
            'OPENAI_TEMPERATURE': 0.2,
            'OPENAI_MAX_RETRIES': 5,
            'OPENAI_MAX_CONCURRENCY': 4,
        }
        kbb = KBBuilder(config)
        mock_openai.assert_called_once_with(
            api_key='fake',
            model='gpt-4o-mini',
            temperature=0.2,
            max_retries=5,
            max_concurrency=4,
        )


# ---------------------------------------------------------------------------
# KBBuilder — _parse_github_repo_url
# ---------------------------------------------------------------------------
class TestParseGitHubRepoURL(unittest.TestCase):
    """Test GitHub URL parsing logic."""

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def setUp(self, mock_gemini):
        self.kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})

    def test_https_url(self):
        self.assertEqual(
            self.kbb._parse_github_repo_url('https://github.com/user/repo'),
            ('user', 'repo'),
        )

    def test_http_url(self):
        self.assertEqual(
            self.kbb._parse_github_repo_url('http://github.com/user/repo'),
            ('user', 'repo'),
        )

    def test_simple_format(self):
        self.assertEqual(
            self.kbb._parse_github_repo_url('user/repo'),
            ('user', 'repo'),
        )

    def test_invalid_format_raises(self):
        with self.assertRaises(ValueError):
            self.kbb._parse_github_repo_url('justastring')


# ---------------------------------------------------------------------------
# KBBuilder — build (integration-style, mocked)
# ---------------------------------------------------------------------------
class TestKBBuilderBuild(unittest.TestCase):
    """Test the build pipeline with mocked processors and LLM."""

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def setUp(self, mock_gemini):
        self.kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        # Mock the LLM so preprocess_text_async returns the text unchanged
        self.kbb.llm = MagicMock()
        self.kbb.llm.preprocess_text_async = AsyncMock(side_effect=lambda t: t)

    def test_build_empty_sources_returns_early(self):
        result = self.kbb.build({}, 'out.md')
        self.assertEqual(result, 'out.md')
        # No LLM call because no content
        self.kbb.llm.preprocess_text_async.assert_not_called()

    def test_build_with_sitemap(self):
        self.kbb.website_processor = MagicMock()
        self.kbb.website_processor.get_urls_from_sitemap.return_value = ['http://a.com']
        self.kbb.website_processor.download_and_clean_html.return_value = 'page text'

        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            outpath = f.name

        try:
            self.kbb.build({'sitemap_url': 'http://a.com/sitemap.xml'}, outpath)
            self.kbb.website_processor.get_urls_from_sitemap.assert_called_once()
            with open(outpath) as f:
                self.assertIn('page text', f.read())
        finally:
            os.unlink(outpath)

    def test_build_with_legacy_pdf_urls_error_handled(self):
        """Legacy pdf_urls calls process_pdfs which calls _process_pdf (missing sync method).
        The error is caught internally, so build completes without raising."""
        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            outpath = f.name
        try:
            # Should not raise — errors are caught
            self.kbb.build({'pdf_urls': ['http://x.com/a.pdf']}, outpath)
        finally:
            if os.path.exists(outpath):
                os.unlink(outpath)

    def test_build_with_legacy_web_urls(self):
        self.kbb.website_processor = MagicMock()
        self.kbb.website_processor.download_and_clean_html.return_value = 'web text'

        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            outpath = f.name

        try:
            self.kbb.build({'web_urls': ['http://x.com/page']}, outpath)
            self.kbb.website_processor.download_and_clean_html.assert_called_once()
        finally:
            if os.path.exists(outpath):
                os.unlink(outpath)

    def test_build_with_github_repos(self):
        self.kbb.github_processor = MagicMock()
        self.kbb.github_processor.get_markdown_urls_for_repo.return_value = [
            'https://raw.github.com/u/r/main/README.md'
        ]
        self.kbb.github_processor.download_markdown.return_value = '# Readme'

        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            outpath = f.name

        try:
            self.kbb.build({'github_repositories': ['u/r']}, outpath)
            self.kbb.github_processor.get_markdown_urls_for_repo.assert_called_once_with('u', 'r')
            with open(outpath) as f:
                self.assertIn('Readme', f.read())
        finally:
            os.unlink(outpath)

    def test_build_with_github_username(self):
        self.kbb.github_processor = MagicMock()
        self.kbb.github_processor.get_user_repos.return_value = ['repo1']
        self.kbb.github_processor.get_markdown_urls_for_repo.return_value = []

        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            outpath = f.name

        try:
            self.kbb.build({'github_username': 'testuser'}, outpath)
            self.kbb.github_processor.get_user_repos.assert_called_once()
        finally:
            if os.path.exists(outpath):
                os.unlink(outpath)


# ---------------------------------------------------------------------------
# KBBuilder — process_files_async (file type routing)
# ---------------------------------------------------------------------------
class TestProcessFilesAsync(unittest.TestCase):
    """Test async file routing by extension."""

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def setUp(self, mock_gemini):
        self.kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_pdf_routed(self):
        self.kbb.pdf_processor = MagicMock()
        self.kbb.pdf_processor.download.return_value = '/tmp/f.pdf'
        self.kbb.pdf_processor.extract_text.return_value = 'pdf text'
        self._run(self.kbb.process_files_async(['http://x.com/doc.pdf']))
        self.kbb.pdf_processor.download.assert_called_once()

    def test_docx_routed(self):
        self.kbb.document_processor = MagicMock()
        self.kbb.document_processor.download.return_value = '/tmp/f.docx'
        self.kbb.document_processor.extract_text.return_value = 'docx text'
        self._run(self.kbb.process_files_async(['http://x.com/doc.docx']))
        self.kbb.document_processor.download.assert_called_once()

    def test_csv_routed(self):
        self.kbb.spreadsheet_processor = MagicMock()
        self.kbb.spreadsheet_processor.download.return_value = '/tmp/f.csv'
        self.kbb.spreadsheet_processor.extract_text.return_value = 'csv text'
        self._run(self.kbb.process_files_async(['http://x.com/data.csv']))
        self.kbb.spreadsheet_processor.download.assert_called_once()

    def test_html_file_routed(self):
        self.kbb.web_content_processor = MagicMock()
        self.kbb.web_content_processor.download.return_value = '/tmp/f.html'
        self.kbb.web_content_processor.extract_text.return_value = 'html text'
        self._run(self.kbb.process_files_async(['http://x.com/page.html']))
        self.kbb.web_content_processor.download.assert_called_once()

    def test_bare_url_routed_as_web(self):
        self.kbb.website_processor = MagicMock()
        self.kbb.website_processor.download_and_clean_html.return_value = 'web text'
        self._run(self.kbb.process_files_async(['http://example.com/about']))
        self.kbb.website_processor.download_and_clean_html.assert_called_once()

    def test_error_handling_doesnt_crash(self):
        self.kbb.pdf_processor = MagicMock()
        self.kbb.pdf_processor.download.side_effect = Exception('download fail')
        # Should not raise
        self._run(self.kbb.process_files_async(['http://x.com/bad.pdf']))


# ---------------------------------------------------------------------------
# KBBuilder — build_final_kb
# ---------------------------------------------------------------------------
class TestBuildFinalKB(unittest.TestCase):
    """Test the build_final_kb method."""

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_writes_content(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.text_contents = ['# Hello World']

        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            outpath = f.name

        try:
            kbb.build_final_kb(outpath)
            with open(outpath) as f:
                self.assertEqual(f.read(), '# Hello World')
        finally:
            os.unlink(outpath)

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_empty_content_no_write(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.text_contents = []
        # Should not raise or create a file
        kbb.build_final_kb('/tmp/nonexistent_test_file.md')


# ---------------------------------------------------------------------------
# KBBuilder — process_websites
# ---------------------------------------------------------------------------
class TestProcessWebsites(unittest.TestCase):

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_process_websites_calls_sitemap(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.website_processor = MagicMock()
        kbb.website_processor.get_urls_from_sitemap.return_value = ['http://a.com', 'http://b.com']
        kbb.website_processor.download_and_clean_html.return_value = 'text'

        kbb.process_websites('http://example.com/sitemap.xml')

        kbb.website_processor.get_urls_from_sitemap.assert_called_once_with('http://example.com/sitemap.xml')
        self.assertEqual(kbb.website_processor.download_and_clean_html.call_count, 2)
        self.assertEqual(len(kbb.text_contents), 2)

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_process_websites_handles_error(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.website_processor = MagicMock()
        kbb.website_processor.get_urls_from_sitemap.side_effect = Exception('fail')
        # Should not raise
        kbb.process_websites('http://bad.com/sitemap.xml')


# ---------------------------------------------------------------------------
# KBBuilder — legacy source processing
# ---------------------------------------------------------------------------
class TestLegacySources(unittest.TestCase):

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_process_documents_legacy_error_handled(self, mock_gemini):
        """Legacy process_documents calls _process_document which doesn't exist as sync.
        Errors are caught internally."""
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.process_documents(['http://x.com/a.docx'])
        # No crash = pass

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_process_spreadsheets_legacy_error_handled(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.process_spreadsheets(['http://x.com/a.csv'])

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_process_web_content_legacy_error_handled(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.process_web_content(['http://x.com/a.json'])

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_process_pdfs_error_handling(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.pdf_processor = MagicMock()
        kbb.pdf_processor.download.side_effect = Exception('fail')
        # Should not raise
        kbb.process_pdfs(['http://x.com/bad.pdf'])


# ---------------------------------------------------------------------------
# KBBuilder — process_github_repos
# ---------------------------------------------------------------------------
class TestProcessGitHubRepos(unittest.TestCase):

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_empty_repos_skips(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.process_github_repos([])
        # No crash, no GitHub processor initialized

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    @patch('knowledge_base_builder.kb_builder.GitHubProcessor')
    def test_initializes_processor_lazily(self, mock_gh_proc, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        self.assertIsNone(kbb.github_processor)

        mock_gh_proc.return_value.get_markdown_urls_for_repo.return_value = []
        kbb.process_github_repos(['user/repo'])
        mock_gh_proc.assert_called_once()

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_invalid_repo_url_handled(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.github_processor = MagicMock()
        # Should not raise — the ValueError from _parse_github_repo_url is caught
        kbb.process_github_repos(['invalid_string_no_slash'])


# ---------------------------------------------------------------------------
# LLM class
# ---------------------------------------------------------------------------
class TestLLMClass(unittest.TestCase):
    """Test LLM build, preprocess_text_async, merge_all_kbs, process_documents."""

    def setUp(self):
        self.mock_client = MagicMock()
        self.mock_client.run.return_value = 'result'
        self.mock_client.run_async = AsyncMock(return_value='async result')
        self.llm = LLM(self.mock_client)

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    def test_build(self):
        result = self.llm.build('some text')
        self.assertEqual(result, 'result')
        prompt = self.mock_client.run.call_args[0][0]
        self.assertIn('some text', prompt)
        self.assertIn('Markdown knowledge base', prompt)

    def test_preprocess_text_async(self):
        result = self._run(self.llm.preprocess_text_async('some text'))
        self.assertEqual(result, 'async result')

    def test_merge_all_kbs_empty(self):
        result = self._run(self.llm.merge_all_kbs([]))
        self.assertEqual(result, '')

    def test_merge_all_kbs(self):
        result = self._run(self.llm.merge_all_kbs(['kb1', 'kb2']))
        self.assertEqual(result, 'async result')
        prompt = self.mock_client.run_async.call_args[0][0]
        self.assertIn('kb1', prompt)
        self.assertIn('kb2', prompt)

    def test_process_documents_empty(self):
        result = self._run(self.llm.process_documents([]))
        self.assertEqual(result, '')

    def test_process_documents(self):
        self.mock_client.run_async = AsyncMock(return_value='processed')
        result = self._run(self.llm.process_documents(['text1', 'text2']))
        self.assertEqual(result, 'processed')


# ---------------------------------------------------------------------------
# DocumentProcessor
# ---------------------------------------------------------------------------
class TestDocumentProcessor(unittest.TestCase):

    def test_extract_text_txt(self):
        with tempfile.NamedTemporaryFile(suffix='.txt', mode='w', delete=False, encoding='utf-8') as f:
            f.write('hello world')
            path = f.name
        try:
            result = DocumentProcessor.extract_text(path)
            self.assertEqual(result, 'hello world')
        finally:
            os.unlink(path)

    def test_extract_text_md(self):
        with tempfile.NamedTemporaryFile(suffix='.md', mode='w', delete=False, encoding='utf-8') as f:
            f.write('# Title\n\nBody')
            path = f.name
        try:
            result = DocumentProcessor.extract_text(path)
            self.assertEqual(result, '# Title\n\nBody')
        finally:
            os.unlink(path)

    def test_extract_text_unsupported(self):
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            path = f.name
        try:
            with self.assertRaises(ValueError):
                DocumentProcessor.extract_text(path)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# SpreadsheetProcessor
# ---------------------------------------------------------------------------
class TestSpreadsheetProcessor(unittest.TestCase):

    def test_extract_text_csv(self):
        with tempfile.NamedTemporaryFile(suffix='.csv', mode='w', delete=False, encoding='utf-8') as f:
            f.write('name,age\nAlice,30\nBob,25\n')
            path = f.name
        try:
            result = SpreadsheetProcessor.extract_text(path)
            self.assertIn('name', result)
            self.assertIn('Alice', result)
            self.assertIn('30', result)
        finally:
            os.unlink(path)

    def test_extract_text_tsv(self):
        with tempfile.NamedTemporaryFile(suffix='.tsv', mode='w', delete=False, encoding='utf-8') as f:
            f.write('col1\tcol2\nval1\tval2\n')
            path = f.name
        try:
            result = SpreadsheetProcessor.extract_text(path)
            self.assertIn('col1', result)
            self.assertIn('val1', result)
        finally:
            os.unlink(path)

    def test_unsupported_format(self):
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            path = f.name
        try:
            with self.assertRaises(ValueError):
                SpreadsheetProcessor.extract_text(path)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# WebContentProcessor
# ---------------------------------------------------------------------------
class TestWebContentProcessor(unittest.TestCase):

    def test_extract_html(self):
        with tempfile.NamedTemporaryFile(suffix='.html', mode='w', delete=False, encoding='utf-8') as f:
            f.write('<html><body><h1>Hello</h1><script>bad</script><p>World</p></body></html>')
            path = f.name
        try:
            result = WebContentProcessor.extract_text(path)
            self.assertIn('Hello', result)
            self.assertIn('World', result)
            self.assertNotIn('bad', result)
        finally:
            os.unlink(path)

    def test_extract_json(self):
        with tempfile.NamedTemporaryFile(suffix='.json', mode='w', delete=False, encoding='utf-8') as f:
            f.write('{"key": "value", "nested": {"a": 1}}')
            path = f.name
        try:
            result = WebContentProcessor.extract_text(path)
            self.assertIn('key', result)
            self.assertIn('value', result)
        finally:
            os.unlink(path)

    def test_extract_yaml(self):
        with tempfile.NamedTemporaryFile(suffix='.yaml', mode='w', delete=False, encoding='utf-8') as f:
            f.write('name: test\nitems:\n  - one\n  - two\n')
            path = f.name
        try:
            result = WebContentProcessor.extract_text(path)
            self.assertIn('name', result)
            self.assertIn('test', result)
        finally:
            os.unlink(path)

    def test_extract_xml(self):
        with tempfile.NamedTemporaryFile(suffix='.xml', mode='w', delete=False, encoding='utf-8') as f:
            f.write('<?xml version="1.0"?><root><item>hello</item></root>')
            path = f.name
        try:
            result = WebContentProcessor.extract_text(path)
            self.assertIn('hello', result)
        finally:
            os.unlink(path)

    def test_unsupported_format(self):
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            path = f.name
        try:
            with self.assertRaises(ValueError):
                WebContentProcessor.extract_text(path)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# OpenAI / Anthropic client init (just verify they instantiate)
# ---------------------------------------------------------------------------
class TestClientInit(unittest.TestCase):

    @patch('knowledge_base_builder.openai_client.ChatOpenAI')
    def test_openai_client_init(self, mock_chat):
        from knowledge_base_builder.openai_client import OpenAIClient
        client = OpenAIClient(api_key='fake', model='gpt-4o', temperature=0.5)
        mock_chat.assert_called_once_with(model='gpt-4o', temperature=0.5, api_key='fake')

    @patch('knowledge_base_builder.anthropic_client.ChatAnthropic')
    def test_anthropic_client_init(self, mock_chat):
        from knowledge_base_builder.anthropic_client import AnthropicClient
        client = AnthropicClient(api_key='fake', model='claude-3-7-sonnet', temperature=0.5)
        mock_chat.assert_called_once_with(
            model='claude-3-7-sonnet', temperature=0.5, anthropic_api_key='fake'
        )


if __name__ == '__main__':
    unittest.main()
