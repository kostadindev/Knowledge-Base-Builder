"""Targeted tests to boost coverage on low-coverage modules."""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

# ---------------------------------------------------------------------------
# BaseProcessor
# ---------------------------------------------------------------------------
class TestBaseProcessor(unittest.TestCase):

    def test_download_local_file(self):
        from knowledge_base_builder.base_processor import BaseProcessor
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b'hello')
            path = f.name
        try:
            file_url = f"file://{path}"
            result = BaseProcessor.download(file_url, ['.txt'])
            self.assertEqual(os.path.normpath(result), os.path.normpath(path))
        finally:
            os.unlink(path)

    def test_download_local_file_not_found(self):
        from knowledge_base_builder.base_processor import BaseProcessor
        with self.assertRaises(FileNotFoundError):
            BaseProcessor.download("file:///nonexistent_file_abc123.txt", ['.txt'])

    @patch('knowledge_base_builder.base_processor.requests.get')
    def test_download_from_url(self, mock_get):
        from knowledge_base_builder.base_processor import BaseProcessor
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'file content'
        mock_resp.headers = {}
        mock_get.return_value = mock_resp

        path = BaseProcessor.download("http://example.com/test.pdf", ['.pdf'])
        self.assertTrue(os.path.exists(path))
        os.unlink(path)

    @patch('knowledge_base_builder.base_processor.requests.get')
    def test_download_from_url_with_content_disposition(self, mock_get):
        from knowledge_base_builder.base_processor import BaseProcessor
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'data'
        mock_resp.headers = {'content-disposition': 'attachment; filename="report.pdf"'}
        mock_get.return_value = mock_resp

        path = BaseProcessor.download("http://example.com/download", ['.pdf'])
        self.assertTrue(os.path.exists(path))
        self.assertTrue(path.endswith('.pdf'))
        os.unlink(path)

    @patch('knowledge_base_builder.base_processor.requests.get')
    def test_download_from_url_unknown_extension(self, mock_get):
        from knowledge_base_builder.base_processor import BaseProcessor
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.content = b'data'
        mock_resp.headers = {}
        mock_get.return_value = mock_resp

        path = BaseProcessor.download("http://example.com/noext", ['.txt'])
        self.assertTrue(os.path.exists(path))
        os.unlink(path)

    @patch('knowledge_base_builder.base_processor.requests.get')
    def test_download_from_url_error(self, mock_get):
        from knowledge_base_builder.base_processor import BaseProcessor
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        with self.assertRaises(Exception):
            BaseProcessor.download("http://example.com/bad.pdf", ['.pdf'])


# ---------------------------------------------------------------------------
# GitHubProcessor
# ---------------------------------------------------------------------------
class TestGitHubProcessor(unittest.TestCase):

    def test_init_with_token(self):
        from knowledge_base_builder.github_processor import GitHubProcessor
        proc = GitHubProcessor(username='user', token='tok')
        self.assertEqual(proc.username, 'user')
        self.assertEqual(proc.headers, {'Authorization': 'token tok'})

    def test_init_without_token(self):
        from knowledge_base_builder.github_processor import GitHubProcessor
        proc = GitHubProcessor(username='user')
        self.assertEqual(proc.headers, {})

    @patch('knowledge_base_builder.github_processor.requests.get')
    def test_get_user_repos(self, mock_get):
        from knowledge_base_builder.github_processor import GitHubProcessor
        proc = GitHubProcessor(username='user', token='tok')

        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = [{'name': 'repo1'}, {'name': 'repo2'}]

        page2 = MagicMock()
        page2.status_code = 200
        page2.json.return_value = []

        mock_get.side_effect = [page1, page2]
        repos = proc.get_user_repos()
        self.assertEqual(repos, ['repo1', 'repo2'])

    @patch('knowledge_base_builder.github_processor.requests.get')
    def test_get_user_repos_error(self, mock_get):
        from knowledge_base_builder.github_processor import GitHubProcessor
        proc = GitHubProcessor(username='user')
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp
        with self.assertRaises(Exception):
            proc.get_user_repos()

    def test_get_user_repos_no_username(self):
        from knowledge_base_builder.github_processor import GitHubProcessor
        proc = GitHubProcessor()
        with self.assertRaises(ValueError):
            proc.get_user_repos()

    @patch('knowledge_base_builder.github_processor.requests.get')
    def test_get_markdown_urls_for_repo(self, mock_get):
        from knowledge_base_builder.github_processor import GitHubProcessor
        proc = GitHubProcessor()

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {'type': 'file', 'name': 'README.md', 'download_url': 'http://raw/README.md'},
            {'type': 'file', 'name': 'main.py'},
            {'type': 'dir', 'name': 'docs', 'path': 'docs'},
        ]
        mock_dir = MagicMock()
        mock_dir.status_code = 200
        mock_dir.json.return_value = [
            {'type': 'file', 'name': 'guide.md', 'download_url': 'http://raw/docs/guide.md'},
        ]
        mock_get.side_effect = [mock_resp, mock_dir]
        urls = proc.get_markdown_urls_for_repo('owner', 'repo')
        self.assertEqual(len(urls), 2)

    @patch('knowledge_base_builder.github_processor.requests.get')
    def test_get_markdown_urls_for_repo_404(self, mock_get):
        from knowledge_base_builder.github_processor import GitHubProcessor
        proc = GitHubProcessor()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        self.assertEqual(proc.get_markdown_urls_for_repo('owner', 'repo'), [])

    @patch('knowledge_base_builder.github_processor.requests.get')
    def test_get_markdown_urls(self, mock_get):
        from knowledge_base_builder.github_processor import GitHubProcessor
        proc = GitHubProcessor(username='user')

        repos_resp = MagicMock()
        repos_resp.status_code = 200
        repos_resp.json.return_value = [{'name': 'r1'}]
        empty_resp = MagicMock()
        empty_resp.status_code = 200
        empty_resp.json.return_value = []
        contents_resp = MagicMock()
        contents_resp.status_code = 200
        contents_resp.json.return_value = [
            {'type': 'file', 'name': 'README.md', 'download_url': 'http://raw/README.md'},
        ]
        mock_get.side_effect = [repos_resp, empty_resp, contents_resp]
        urls = proc.get_markdown_urls()
        self.assertEqual(urls, ['http://raw/README.md'])

    @patch('knowledge_base_builder.github_processor.requests.get')
    def test_download_markdown(self, mock_get):
        from knowledge_base_builder.github_processor import GitHubProcessor
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '# Hello'
        mock_get.return_value = mock_resp
        self.assertEqual(GitHubProcessor.download_markdown('http://raw/README.md'), '# Hello')

    @patch('knowledge_base_builder.github_processor.requests.get')
    def test_download_markdown_error(self, mock_get):
        from knowledge_base_builder.github_processor import GitHubProcessor
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        with self.assertRaises(Exception):
            GitHubProcessor.download_markdown('http://raw/bad.md')

    def test_get_markdown_urls_requires_username(self):
        from knowledge_base_builder.github_processor import GitHubProcessor
        proc = GitHubProcessor()
        with self.assertRaises(ValueError):
            proc.get_markdown_urls()


# ---------------------------------------------------------------------------
# WebsiteProcessor
# ---------------------------------------------------------------------------
class TestWebsiteProcessor(unittest.TestCase):

    @patch('knowledge_base_builder.website_processor.requests.get')
    def test_get_urls_from_sitemap(self, mock_get):
        from knowledge_base_builder.website_processor import WebsiteProcessor
        proc = WebsiteProcessor()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '''<?xml version="1.0"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>http://a.com</loc></url>
            <url><loc>http://b.com</loc></url>
        </urlset>'''
        mock_get.return_value = mock_resp
        urls = proc.get_urls_from_sitemap('http://x.com/sitemap.xml')
        self.assertEqual(urls, ['http://a.com', 'http://b.com'])

    @patch('knowledge_base_builder.website_processor.requests.get')
    def test_get_urls_from_sitemap_error(self, mock_get):
        from knowledge_base_builder.website_processor import WebsiteProcessor
        proc = WebsiteProcessor()
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp
        with self.assertRaises(Exception):
            proc.get_urls_from_sitemap('http://x.com/sitemap.xml')

    @patch('knowledge_base_builder.website_processor.requests.get')
    def test_download_and_clean_html(self, mock_get):
        from knowledge_base_builder.website_processor import WebsiteProcessor
        proc = WebsiteProcessor()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><body><h1>Title</h1><script>x</script><p>Text</p><noscript>no</noscript></body></html>'
        mock_get.return_value = mock_resp
        text = proc.download_and_clean_html('http://x.com')
        self.assertIn('Title', text)
        self.assertIn('Text', text)
        self.assertNotIn('x', text.split('Title')[0])  # script removed


# ---------------------------------------------------------------------------
# PDFProcessor
# ---------------------------------------------------------------------------
class TestPDFProcessor(unittest.TestCase):

    @patch('knowledge_base_builder.pdf_processor.RecursiveCharacterTextSplitter')
    @patch('knowledge_base_builder.pdf_processor.PyPDFLoader')
    def test_extract_text(self, mock_loader, mock_splitter):
        from knowledge_base_builder.pdf_processor import PDFProcessor
        doc1 = MagicMock()
        doc1.page_content = 'Page 1'
        doc2 = MagicMock()
        doc2.page_content = 'Page 2'
        mock_loader.return_value.load.return_value = [doc1, doc2]
        mock_splitter.return_value.split_documents.return_value = [doc1, doc2]

        result = PDFProcessor.extract_text('/tmp/fake.pdf')
        self.assertEqual(result, 'Page 1\nPage 2')

    def test_download_delegates_to_base(self):
        from knowledge_base_builder.pdf_processor import PDFProcessor
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b'pdf')
            path = f.name
        try:
            result = PDFProcessor.download(f"file://{path}")
            self.assertEqual(os.path.normpath(result), os.path.normpath(path))
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# LLM Clients — run_async with retries and backoff
# ---------------------------------------------------------------------------
class TestGeminiClientRunAsync(unittest.TestCase):

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    @patch('knowledge_base_builder.gemini_client.ChatGoogleGenerativeAI')
    def test_run_async_success(self, mock_chat):
        from knowledge_base_builder.gemini_client import GeminiClient
        mock_result = MagicMock()
        mock_result.content = 'response'
        mock_chat.return_value.ainvoke = AsyncMock(return_value=mock_result)

        client = GeminiClient(api_key='fake')
        result = self._run(client.run_async('prompt'))
        self.assertEqual(result, 'response')

    @patch('knowledge_base_builder.gemini_client.ChatGoogleGenerativeAI')
    def test_run_async_retry_then_success(self, mock_chat):
        from knowledge_base_builder.gemini_client import GeminiClient
        mock_result = MagicMock()
        mock_result.content = 'ok'
        mock_chat.return_value.ainvoke = AsyncMock(
            side_effect=[Exception('fail'), mock_result]
        )
        client = GeminiClient(api_key='fake', max_retries=2)
        with patch('knowledge_base_builder.gemini_client.asyncio.sleep', new_callable=AsyncMock):
            result = self._run(client.run_async('prompt'))
        self.assertEqual(result, 'ok')

    @patch('knowledge_base_builder.gemini_client.ChatGoogleGenerativeAI')
    def test_run_async_all_retries_fail(self, mock_chat):
        from knowledge_base_builder.gemini_client import GeminiClient
        mock_chat.return_value.ainvoke = AsyncMock(side_effect=Exception('fail'))
        client = GeminiClient(api_key='fake', max_retries=2)
        with patch('knowledge_base_builder.gemini_client.asyncio.sleep', new_callable=AsyncMock):
            with self.assertRaises(Exception):
                self._run(client.run_async('prompt'))

    @patch('knowledge_base_builder.gemini_client.ChatGoogleGenerativeAI')
    def test_sync_run(self, mock_chat):
        from knowledge_base_builder.gemini_client import GeminiClient
        mock_result = MagicMock()
        mock_result.content = 'sync result'
        mock_chat.return_value.ainvoke = AsyncMock(return_value=mock_result)
        client = GeminiClient(api_key='fake')
        result = client.run('prompt')
        self.assertEqual(result, 'sync result')


class TestOpenAIClientRunAsync(unittest.TestCase):

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    @patch('knowledge_base_builder.openai_client.ChatOpenAI')
    def test_run_async_success(self, mock_chat):
        from knowledge_base_builder.openai_client import OpenAIClient
        mock_result = MagicMock()
        mock_result.content = 'openai response'
        mock_chat.return_value.ainvoke = AsyncMock(return_value=mock_result)
        client = OpenAIClient(api_key='fake')
        result = self._run(client.run_async('prompt'))
        self.assertEqual(result, 'openai response')

    @patch('knowledge_base_builder.openai_client.ChatOpenAI')
    def test_run_async_retry_then_fail(self, mock_chat):
        from knowledge_base_builder.openai_client import OpenAIClient
        mock_chat.return_value.ainvoke = AsyncMock(side_effect=Exception('fail'))
        client = OpenAIClient(api_key='fake', max_retries=2)
        with patch('knowledge_base_builder.openai_client.asyncio.sleep', new_callable=AsyncMock):
            with self.assertRaises(Exception):
                self._run(client.run_async('prompt'))


class TestAnthropicClientRunAsync(unittest.TestCase):

    def _run(self, coro):
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()

    @patch('knowledge_base_builder.anthropic_client.ChatAnthropic')
    def test_run_async_success(self, mock_chat):
        from knowledge_base_builder.anthropic_client import AnthropicClient
        mock_result = MagicMock()
        mock_result.content = 'claude response'
        mock_chat.return_value.ainvoke = AsyncMock(return_value=mock_result)
        client = AnthropicClient(api_key='fake')
        result = self._run(client.run_async('prompt'))
        self.assertEqual(result, 'claude response')

    @patch('knowledge_base_builder.anthropic_client.ChatAnthropic')
    def test_run_async_all_retries_fail(self, mock_chat):
        from knowledge_base_builder.anthropic_client import AnthropicClient
        mock_chat.return_value.ainvoke = AsyncMock(side_effect=Exception('fail'))
        client = AnthropicClient(api_key='fake', max_retries=2)
        with patch('knowledge_base_builder.anthropic_client.asyncio.sleep', new_callable=AsyncMock):
            with self.assertRaises(Exception):
                self._run(client.run_async('prompt'))


# ---------------------------------------------------------------------------
# LLMClient base — sync run method
# ---------------------------------------------------------------------------
class TestLLMClientSyncRun(unittest.TestCase):

    def test_sync_run_delegates_to_async(self):
        from knowledge_base_builder.llm_client import LLMClient

        class FakeClient(LLMClient):
            async def run_async(self, prompt):
                return 'async_result'

        client = FakeClient(api_key='k', model='m')
        result = client.run('test')
        self.assertEqual(result, 'async_result')


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
class TestCLI(unittest.TestCase):

    @patch('knowledge_base_builder.cli.KBBuilder')
    @patch('knowledge_base_builder.cli.load_dotenv')
    def test_cli_with_google_key(self, mock_dotenv, mock_kbb):
        from knowledge_base_builder.cli import main
        mock_kbb.return_value.build.return_value = 'out.md'

        with patch('sys.argv', ['cli', '--google-api-key', 'fake', '-f', 'http://x.com/page']):
            main()

        mock_kbb.assert_called_once()
        config = mock_kbb.call_args[0][0]
        self.assertEqual(config['GOOGLE_API_KEY'], 'fake')
        mock_kbb.return_value.build.assert_called_once()

    @patch('knowledge_base_builder.cli.KBBuilder')
    @patch('knowledge_base_builder.cli.load_dotenv')
    def test_cli_with_openai_key(self, mock_dotenv, mock_kbb):
        from knowledge_base_builder.cli import main
        mock_kbb.return_value.build.return_value = 'out.md'

        with patch('sys.argv', ['cli', '--llm-provider', 'openai', '--openai-api-key', 'fake']):
            main()

        config = mock_kbb.call_args[0][0]
        self.assertEqual(config['OPENAI_API_KEY'], 'fake')

    @patch('knowledge_base_builder.cli.load_dotenv')
    def test_cli_missing_key_errors(self, mock_dotenv):
        from knowledge_base_builder.cli import main
        with patch('sys.argv', ['cli', '--llm-provider', 'gemini']):
            with self.assertRaises(SystemExit):
                main()

    @patch('knowledge_base_builder.cli.KBBuilder')
    @patch('knowledge_base_builder.cli.load_dotenv')
    def test_cli_with_all_source_types(self, mock_dotenv, mock_kbb):
        from knowledge_base_builder.cli import main
        mock_kbb.return_value.build.return_value = 'out.md'

        with patch('sys.argv', [
            'cli', '--google-api-key', 'fake',
            '-f', 'http://x.com/page',
            '-p', 'http://x.com/a.pdf',
            '-m', 'http://x.com/sitemap.xml',
            '-g', 'user/repo',
            '-o', 'custom_output.md',
        ]):
            main()

        sources = mock_kbb.return_value.build.call_args[0][0]
        self.assertEqual(sources['files'], ['http://x.com/page'])
        self.assertEqual(sources['pdf_urls'], ['http://x.com/a.pdf'])
        self.assertEqual(sources['sitemap_url'], 'http://x.com/sitemap.xml')
        self.assertEqual(sources['github_repositories'], ['user/repo'])


# ---------------------------------------------------------------------------
# DocumentProcessor — docx and rtf (mocked)
# ---------------------------------------------------------------------------
class TestDocumentProcessorExtended(unittest.TestCase):

    @patch('knowledge_base_builder.document_processor.Document')
    def test_extract_docx(self, mock_doc_cls):
        from knowledge_base_builder.document_processor import DocumentProcessor
        mock_para1 = MagicMock()
        mock_para1.text = 'Paragraph 1'
        mock_para2 = MagicMock()
        mock_para2.text = 'Paragraph 2'
        mock_doc_cls.return_value.paragraphs = [mock_para1, mock_para2]

        with tempfile.NamedTemporaryFile(suffix='.docx', delete=False) as f:
            path = f.name
        try:
            result = DocumentProcessor.extract_text(path)
            self.assertEqual(result, 'Paragraph 1\nParagraph 2')
        finally:
            os.unlink(path)

    @patch('knowledge_base_builder.document_processor.rtf_to_text')
    def test_extract_rtf(self, mock_rtf):
        from knowledge_base_builder.document_processor import DocumentProcessor
        mock_rtf.return_value = 'RTF content'

        with tempfile.NamedTemporaryFile(suffix='.rtf', mode='w', delete=False) as f:
            f.write('{\\rtf1 test}')
            path = f.name
        try:
            result = DocumentProcessor.extract_text(path)
            self.assertEqual(result, 'RTF content')
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# SpreadsheetProcessor — xlsx (mocked)
# ---------------------------------------------------------------------------
class TestSpreadsheetProcessorExtended(unittest.TestCase):

    def test_extract_xlsx(self):
        import pandas as pd
        from knowledge_base_builder.spreadsheet_processor import SpreadsheetProcessor

        # Create a real xlsx file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as f:
            path = f.name
        try:
            df = pd.DataFrame({'A': [1, 2], 'B': [3, 4]})
            df.to_excel(path, index=False)
            result = SpreadsheetProcessor.extract_text(path)
            self.assertIn('A', result)
            self.assertIn('1', result)
        finally:
            os.unlink(path)

    def test_unsupported_extension(self):
        from knowledge_base_builder.spreadsheet_processor import SpreadsheetProcessor
        with tempfile.NamedTemporaryFile(suffix='.xyz', delete=False) as f:
            path = f.name
        try:
            with self.assertRaises(ValueError):
                SpreadsheetProcessor.extract_text(path)
        finally:
            os.unlink(path)

    def test_dataframe_to_markdown_large(self):
        import pandas as pd
        from knowledge_base_builder.spreadsheet_processor import SpreadsheetProcessor

        df = pd.DataFrame({'x': range(200)})
        result = SpreadsheetProcessor._dataframe_to_markdown(df)
        self.assertIn('100 rows', result)  # 50 head + 50 tail


if __name__ == '__main__':
    unittest.main()
