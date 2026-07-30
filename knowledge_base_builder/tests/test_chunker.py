"""Tests for Feature 5: Chunked Output for Vector DBs."""

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch, AsyncMock

from knowledge_base_builder.chunker import Chunker
from knowledge_base_builder.kb_builder import KBBuilder


class TestBasicChunking(unittest.TestCase):
    """test_basic_chunking: short text, verify structure."""

    def test_basic_chunking(self):
        chunker = Chunker(chunk_size=500)
        texts = [("Hello world. This is a test.", "http://example.com/page")]
        chunks = chunker.chunk_texts(texts)

        self.assertEqual(len(chunks), 1)
        chunk = chunks[0]
        self.assertIn("id", chunk)
        self.assertIn("text", chunk)
        self.assertIn("metadata", chunk)
        self.assertEqual(chunk["id"], "chunk_0")
        self.assertEqual(chunk["text"], "Hello world. This is a test.")
        self.assertEqual(chunk["metadata"]["source"], "http://example.com/page")
        self.assertEqual(chunk["metadata"]["index"], 0)
        self.assertIn("section", chunk["metadata"])


class TestChunkSizeRespected(unittest.TestCase):
    """test_chunk_size_respected: long text, verify max size."""

    def test_chunk_size_respected(self):
        # Create text longer than chunk_size
        long_text = "Word " * 500  # 2500 chars
        chunker = Chunker(chunk_size=200)
        chunks = chunker.chunk_texts([(long_text, "http://example.com")])

        self.assertGreater(len(chunks), 1)
        for chunk in chunks:
            self.assertLessEqual(len(chunk["text"]), 200)


class TestSectionDetection(unittest.TestCase):
    """test_section_detection: text with ## headings."""

    def test_section_detection(self):
        text = (
            "# Introduction\n\n"
            "Some intro text.\n\n"
            "## Getting Started\n\n"
            "Instructions here.\n\n"
            "## API Reference\n\n"
            "Details about the API."
        )
        chunker = Chunker(chunk_size=50)
        chunks = chunker.chunk_texts([(text, "http://docs.example.com")])

        # There should be multiple chunks
        self.assertGreater(len(chunks), 1)

        # At least one chunk should reference a detected section heading
        sections_found = [c["metadata"]["section"] for c in chunks if c["metadata"]["section"]]
        self.assertGreater(len(sections_found), 0)

    def test_detect_section_static(self):
        text = "# Title\n\nSome text.\n\n## Section A\n\nMore text."
        # Position after "## Section A\n\n"
        pos = text.index("More text.")
        section = Chunker._detect_section(text, pos)
        self.assertEqual(section, "Section A")

    def test_detect_section_no_heading(self):
        text = "No headings here at all."
        section = Chunker._detect_section(text, 10)
        self.assertEqual(section, "")


class TestSourceAttribution(unittest.TestCase):
    """test_source_attribution: two sources, verify metadata.source."""

    def test_source_attribution(self):
        chunker = Chunker(chunk_size=500)
        texts = [
            ("Content from source A.", "http://a.com"),
            ("Content from source B.", "http://b.com"),
        ]
        chunks = chunker.chunk_texts(texts)

        self.assertEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["metadata"]["source"], "http://a.com")
        self.assertEqual(chunks[1]["metadata"]["source"], "http://b.com")


class TestEmptyInput(unittest.TestCase):
    """test_empty_input."""

    def test_empty_list(self):
        chunker = Chunker()
        chunks = chunker.chunk_texts([])
        self.assertEqual(chunks, [])

    def test_empty_text(self):
        chunker = Chunker()
        chunks = chunker.chunk_texts([("", "http://empty.com")])
        self.assertEqual(chunks, [])

    def test_whitespace_only(self):
        chunker = Chunker()
        chunks = chunker.chunk_texts([("   \n\n  ", "http://blank.com")])
        self.assertEqual(chunks, [])


class TestChunkIdsSequential(unittest.TestCase):
    """test_chunk_ids_sequential."""

    def test_chunk_ids_sequential(self):
        chunker = Chunker(chunk_size=30)
        texts = [
            ("First document text here.", "http://a.com"),
            ("Second document text here too.", "http://b.com"),
        ]
        chunks = chunker.chunk_texts(texts)

        for i, chunk in enumerate(chunks):
            self.assertEqual(chunk["id"], f"chunk_{i}")


class TestChunksBuildIntegration(unittest.TestCase):
    """test_chunks_build_integration: mock processors, build with output_format='chunks', verify JSON output."""

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_chunks_build_integration(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.llm = MagicMock()
        kbb.website_processor = MagicMock()
        kbb.website_processor.download_and_clean_html.side_effect = [
            "## Overview\n\nFirst page content here.",
            "## Details\n\nSecond page content here.",
        ]

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            outpath = f.name

        try:
            kbb.build(
                {'files': ['http://example.com/a', 'http://example.com/b']},
                outpath,
                output_format='chunks',
                chunk_size=500,
                metadata=False,
            )

            self.assertTrue(os.path.exists(outpath))
            with open(outpath) as f:
                data = json.load(f)

            self.assertIsInstance(data, list)
            self.assertGreater(len(data), 0)

            # Verify structure of each chunk
            for chunk in data:
                self.assertIn("id", chunk)
                self.assertIn("text", chunk)
                self.assertIn("metadata", chunk)
                self.assertIn("source", chunk["metadata"])
                self.assertIn("section", chunk["metadata"])
                self.assertIn("index", chunk["metadata"])

            # Verify both sources appear
            sources = {c["metadata"]["source"] for c in data}
            self.assertIn("http://example.com/a", sources)
            self.assertIn("http://example.com/b", sources)
        finally:
            if os.path.exists(outpath):
                os.unlink(outpath)


class TestChunksSkipsLLM(unittest.TestCase):
    """test_chunks_skips_llm: verify llm.preprocess_text_async not called."""

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_chunks_skips_llm(self, mock_gemini):
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.llm = MagicMock()
        kbb.llm.preprocess_text_async = AsyncMock(return_value='should not be called')
        kbb.llm.preprocess_text_llms_txt_async = AsyncMock(return_value='should not be called')
        kbb.website_processor = MagicMock()
        kbb.website_processor.download_and_clean_html.return_value = 'Some text content.'

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            outpath = f.name

        try:
            kbb.build(
                {'files': ['http://example.com/page']},
                outpath,
                output_format='chunks',
                metadata=False,
            )

            # LLM should never have been called
            kbb.llm.preprocess_text_async.assert_not_called()
            kbb.llm.preprocess_text_llms_txt_async.assert_not_called()

            # Output should still be valid JSON chunks
            with open(outpath) as f:
                data = json.load(f)
            self.assertGreater(len(data), 0)
        finally:
            if os.path.exists(outpath):
                os.unlink(outpath)


class TestSplitAtBoundaries(unittest.TestCase):
    """Tests for the static _split_at_boundaries helper."""

    def test_short_text_not_split(self):
        result = Chunker._split_at_boundaries("Hello world.", 100)
        self.assertEqual(result, ["Hello world."])

    def test_paragraph_boundary(self):
        text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
        result = Chunker._split_at_boundaries(text, 30)
        self.assertGreater(len(result), 1)
        # Reassembled text should match original
        self.assertEqual("".join(result), text)

    def test_sentence_boundary(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        result = Chunker._split_at_boundaries(text, 40)
        self.assertGreater(len(result), 1)

    def test_hard_cut(self):
        text = "a" * 200
        result = Chunker._split_at_boundaries(text, 50)
        for part in result:
            self.assertLessEqual(len(part), 50)
        self.assertEqual("".join(result), text)


class TestChunkerEdgeCases(unittest.TestCase):
    """Additional edge case tests."""

    def test_invalid_chunk_size(self):
        with self.assertRaises(ValueError):
            Chunker(chunk_size=0)
        with self.assertRaises(ValueError):
            Chunker(chunk_size=-1)

    @patch('knowledge_base_builder.kb_builder.GeminiClient')
    def test_chunks_with_metadata_sidecar(self, mock_gemini):
        """Verify metadata sidecar is written for chunks mode."""
        kbb = KBBuilder({'GOOGLE_API_KEY': 'fake'})
        kbb.llm = MagicMock()
        kbb.website_processor = MagicMock()
        kbb.website_processor.download_and_clean_html.return_value = 'Some content.'

        with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as f:
            outpath = f.name
        meta_path = outpath + '.meta.json'

        try:
            kbb.build(
                {'files': ['http://example.com']},
                outpath,
                output_format='chunks',
                metadata=True,
            )
            self.assertTrue(os.path.exists(meta_path))
            with open(meta_path) as f:
                meta = json.load(f)
            self.assertIn('build_timestamp', meta)
        finally:
            if os.path.exists(outpath):
                os.unlink(outpath)
            if os.path.exists(meta_path):
                os.unlink(meta_path)


if __name__ == '__main__':
    unittest.main()
