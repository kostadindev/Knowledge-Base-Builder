"""Basic tests for the Knowledge Base Builder package."""

import unittest
from unittest.mock import patch
from knowledge_base_builder import KBBuilder


class TestKBBuilder(unittest.TestCase):
    """Test the KBBuilder class."""

    @patch('knowledge_base_builder.gemini_client.ChatGoogleGenerativeAI')
    def test_initialization(self, mock_gemini):
        """Test that KBBuilder initializes correctly."""
        config = {
            'GOOGLE_API_KEY': 'fake-api-key',
            'GEMINI_MODEL': 'gemini-2.0-flash',
            'GEMINI_TEMPERATURE': 0.7,
        }
        kb_builder = KBBuilder(config)

        self.assertIsNotNone(kb_builder)
        self.assertEqual(kb_builder.config, config)
        self.assertIsNotNone(kb_builder.llm_client)
        self.assertIsNotNone(kb_builder.llm)
        self.assertIsNotNone(kb_builder.pdf_processor)
        self.assertIsNotNone(kb_builder.website_processor)
        self.assertIsNone(kb_builder.github_processor)

    @patch('knowledge_base_builder.gemini_client.ChatGoogleGenerativeAI')
    def test_init_with_github(self, mock_gemini):
        """Test initialization with GitHub credentials."""
        config = {
            'GOOGLE_API_KEY': 'fake-api-key',
            'GITHUB_API_KEY': 'fake-github-token',
        }
        kb_builder = KBBuilder(config)
        # github_processor is lazy-initialized, so it's None at init
        self.assertIsNone(kb_builder.github_processor)


if __name__ == '__main__':
    unittest.main()
