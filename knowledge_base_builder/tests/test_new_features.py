"""Tests for the three new features: llms.txt output, metadata sidecar, incremental builds."""

import asyncio
import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

from knowledge_base_builder.kb_builder import KBBuilder
from knowledge_base_builder.build_metadata import BuildMetadata, SourceResult
from knowledge_base_builder.cache import BuildCache


# ---------------------------------------------------------------------------
# BuildMetadata
# ---------------------------------------------------------------------------
class TestBuildMetadata(unittest.TestCase):

    def test_basic_metadata(self):
        meta = BuildMetadata("OpenAIClient", "gpt-4o", 0.7)
        self.assertEqual(meta.llm_provider, "OpenAIClient")
        self.assertEqual(meta.llm_model, "gpt-4o")
        self.assertIsNotNone(meta.build_timestamp)

    def test_add_source_and_serialize(self):
        meta = BuildMetadata("OpenAIClient", "gpt-4o", 0.7)

        good = SourceResult("http://a.com/doc.pdf", "pdf")
        good.success = True
        good.word_count = 100
        good.extraction_time_seconds = 1.5
        meta.add_source(good)

        bad = SourceResult("http://b.com/fail.pdf", "pdf")
        bad.success = False
        bad.error_message = "404 Not Found"
        meta.add_source(bad)

        d = meta.to_dict()
        self.assertEqual(len(d["sources_processed"]), 1)
        self.assertEqual(len(d["sources_failed"]), 1)
        self.assertEqual(d["sources_processed"][0]["url"], "http://a.com/doc.pdf")
        self.assertEqual(d["sources_failed"][0]["error"], "404 Not Found")

    def test_compute_output_stats(self):
        meta = BuildMetadata("X", "y", 0.5)
        meta.compute_output_stats("# Title\n\n## Section\n\nSome words here.\n\n### Sub\n\nMore words.")
        self.assertEqual(meta.output_section_count, 3)
        self.assertGreater(meta.output_word_count, 0)

    def test_write_json(self):
        meta = BuildMetadata("X", "y", 0.5)
        meta.total_processing_time_seconds = 1.0
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            meta.write_json(path)
            with open(path) as f:
                data = json.load(f)
            self.assertEqual(data["llm_provider"], "X")
            self.assertIn("build_timestamp", data)
        finally:
            os.unlink(path)

    def test_cache_hit_flag(self):
        sr = SourceResult("http://x.com", "web")
        sr.success = True
        sr.cache_hit = True
        d = sr.to_dict()
        self.assertTrue(d["cache_hit"])


# ---------------------------------------------------------------------------
# BuildCache
# ---------------------------------------------------------------------------
class TestBuildCache(unittest.TestCase):

    def setUp(self):
        self.cache_dir = tempfile.mkdtemp()
        self.cache = BuildCache(self.cache_dir)

    def tearDown(self):
        shutil.rmtree(self.cache_dir, ignore_errors=True)

    def test_empty_cache(self):
        self.assertEqual(self.cache.manifest, {})

    def test_update_and_retrieve(self):
        self.cache.update_entry("http://example.com/a", "hash123", "extracted text here")
        self.cache.save_manifest()

        # Reload from disk
        cache2 = BuildCache(self.cache_dir)
        result = cache2.get_cached_text("http://example.com/a", "hash123")
        self.assertEqual(result, "extracted text here")

    def test_cache_miss_wrong_hash(self):
        self.cache.update_entry("http://example.com/a", "hash123", "text")
        result = self.cache.get_cached_text("http://example.com/a", "different_hash")
        self.assertIsNone(result)

    def test_cache_miss_no_entry(self):
        result = self.cache.get_cached_text("http://nonexistent.com", "hash")
        self.assertIsNone(result)

    def test_hash_content(self):
        h = BuildCache.hash_content(b"hello world")
        self.assertEqual(len(h), 64)  # SHA-256 hex

    def test_clear(self):
        self.cache.update_entry("http://x.com", "h", "text")
        self.cache.save_manifest()
        self.assertTrue(os.path.exists(self.cache.manifest_path))
        self.cache.clear()
        self.assertFalse(os.path.exists(self.cache_dir))

    def test_corrupt_manifest_handled(self):
        os.makedirs(self.cache_dir, exist_ok=True)
        with open(os.path.join(self.cache_dir, "manifest.json"), "w") as f:
            f.write("NOT VALID JSON")
        cache = BuildCache(self.cache_dir)
        self.assertEqual(cache.manifest, {})


# ---------------------------------------------------------------------------
# Feature 1: llms.txt output mode
# ---------------------------------------------------------------------------
class TestLlmsTxtOutput(unittest.TestCase):

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_llms_txt_build(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.llm = MagicMock()
        kbb.llm.preprocess_text_llms_txt_async = AsyncMock(
            return_value='# My Project\n\n> A cool project\n\n## Docs\n\n- [API](http://x.com): API docs\n'
        )
        kbb.website_processor = MagicMock()
        kbb.website_processor.download_and_clean_html.return_value = 'Some web content here'

        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            outpath = f.name

        try:
            kbb.build(
                {'files': ['http://example.com']},
                outpath,
                output_format='llms_txt',
                project_name='My Project',
                metadata=False,
            )
            # Main output should exist
            with open(outpath) as f:
                content = f.read()
            self.assertIn('My Project', content)

            # llms-full.txt companion should exist
            full_path = outpath.replace('.txt', '-full.txt')
            self.assertTrue(os.path.exists(full_path))
            with open(full_path) as f:
                full_content = f.read()
            self.assertIn('Some web content', full_content)

            # Verify the llms_txt prompt was used, not the regular one
            kbb.llm.preprocess_text_llms_txt_async.assert_called()
        finally:
            os.unlink(outpath)
            full_path = outpath.replace('.txt', '-full.txt')
            if os.path.exists(full_path):
                os.unlink(full_path)

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_invalid_output_format_raises(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        with self.assertRaises(ValueError):
            kbb.build({}, output_format='invalid')

    def test_llms_txt_prompt_content(self):
        """Verify the llms.txt prompt instructs the LLM to follow the spec."""
        from knowledge_base_builder.llm import LLM
        mock_client = MagicMock()
        mock_client.run_async = AsyncMock(return_value='output')
        llm = LLM(mock_client)

        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(llm.preprocess_text_llms_txt_async('test text', 'MyProject'))
        finally:
            loop.close()
        prompt = mock_client.run_async.call_args[0][0]
        self.assertIn('llmstxt.org', prompt)
        self.assertIn('MyProject', prompt)
        self.assertIn('blockquote', prompt)
        self.assertIn('H2', prompt)


# ---------------------------------------------------------------------------
# Feature 2: Metadata sidecar in build()
# ---------------------------------------------------------------------------
class TestMetadataSidecar(unittest.TestCase):

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_metadata_written(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.llm = MagicMock()
        kbb.llm.preprocess_text_async = AsyncMock(return_value='# Result')
        kbb.website_processor = MagicMock()
        kbb.website_processor.download_and_clean_html.return_value = 'page text'

        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            outpath = f.name
        meta_path = outpath + '.meta.json'

        try:
            kbb.build({'files': ['http://example.com/page']}, outpath, metadata=True)
            self.assertTrue(os.path.exists(meta_path))
            with open(meta_path) as f:
                data = json.load(f)
            self.assertIn('build_timestamp', data)
            self.assertIn('sources_processed', data)
            self.assertEqual(len(data['sources_processed']), 1)
            self.assertEqual(data['sources_processed'][0]['source_type'], 'web')
            self.assertTrue(data['sources_processed'][0]['success'])
            self.assertGreater(data['output']['word_count'], 0)
        finally:
            os.unlink(outpath)
            if os.path.exists(meta_path):
                os.unlink(meta_path)

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_metadata_suppressed(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.llm = MagicMock()
        kbb.llm.preprocess_text_async = AsyncMock(return_value='# Result')
        kbb.website_processor = MagicMock()
        kbb.website_processor.download_and_clean_html.return_value = 'text'

        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            outpath = f.name
        meta_path = outpath + '.meta.json'

        try:
            kbb.build({'files': ['http://example.com']}, outpath, metadata=False)
            self.assertFalse(os.path.exists(meta_path))
        finally:
            os.unlink(outpath)

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_metadata_tracks_failures(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.llm = MagicMock()
        kbb.llm.preprocess_text_async = AsyncMock(return_value='result')
        kbb.website_processor = MagicMock()
        kbb.website_processor.download_and_clean_html.side_effect = [
            Exception('timeout'),
            'good text',
        ]

        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            outpath = f.name
        meta_path = outpath + '.meta.json'

        try:
            kbb.build({'files': ['http://fail.com', 'http://ok.com']}, outpath)
            with open(meta_path) as f:
                data = json.load(f)
            self.assertEqual(len(data['sources_failed']), 1)
            self.assertEqual(len(data['sources_processed']), 1)
            self.assertIn('timeout', data['sources_failed'][0]['error'])
        finally:
            os.unlink(outpath)
            if os.path.exists(meta_path):
                os.unlink(meta_path)


# ---------------------------------------------------------------------------
# Feature 3: Incremental builds
# ---------------------------------------------------------------------------
class TestIncrementalBuild(unittest.TestCase):

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_incremental_caches_extraction(self, mock_gemini):
        cache_dir = tempfile.mkdtemp()
        try:
            kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
            kbb.llm = MagicMock()
            kbb.llm.preprocess_text_async = AsyncMock(return_value='# Result')

            # Mock a processor that returns file content
            kbb.web_content_processor = MagicMock()
            kbb.web_content_processor.download.return_value = '/tmp/fake.html'
            kbb.web_content_processor.extract_text.return_value = 'extracted html text'

            with tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w') as f:
                f.write('<html>test</html>')
                html_path = f.name
            kbb.web_content_processor.download.return_value = html_path

            with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
                outpath = f.name

            # First build — should extract
            kbb.build(
                {'files': ['http://example.com/page.html']},
                outpath, incremental=True, cache_dir=cache_dir, metadata=False,
            )
            self.assertEqual(kbb.web_content_processor.extract_text.call_count, 1)

            # Second build — should use cache (same file content)
            kbb2 = KBBuilder({'GOOGLE_API_KEY': 'fake'})
            kbb2.llm = MagicMock()
            kbb2.llm.preprocess_text_async = AsyncMock(return_value='# Cached Result')
            kbb2.web_content_processor = MagicMock()
            kbb2.web_content_processor.download.return_value = html_path
            kbb2.web_content_processor.extract_text.return_value = 'should not be called'

            kbb2.build(
                {'files': ['http://example.com/page.html']},
                outpath, incremental=True, cache_dir=cache_dir, metadata=False,
            )
            # extract_text should NOT have been called — cache hit
            kbb2.web_content_processor.extract_text.assert_not_called()

        finally:
            shutil.rmtree(cache_dir, ignore_errors=True)
            if os.path.exists(outpath):
                os.unlink(outpath)
            if os.path.exists(html_path):
                os.unlink(html_path)

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_non_incremental_ignores_cache(self, mock_gemini):
        """When incremental=False (default), no cache is used."""
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.llm = MagicMock()
        kbb.llm.preprocess_text_async = AsyncMock(return_value='result')
        kbb.website_processor = MagicMock()
        kbb.website_processor.download_and_clean_html.return_value = 'text'

        with tempfile.NamedTemporaryFile(suffix='.md', delete=False) as f:
            outpath = f.name
        try:
            kbb.build({'files': ['http://example.com']}, outpath, metadata=False)
            self.assertIsNone(kbb._cache)
        finally:
            os.unlink(outpath)


if __name__ == '__main__':
    unittest.main()
