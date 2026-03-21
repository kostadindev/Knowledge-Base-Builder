"""
Knowledge Base Builder Package
-----------------------------

This package provides tools to build structured knowledge bases from various sources
using multiple LLM providers including Google Gemini, OpenAI GPT-4o, and Anthropic Claude.
"""

__version__ = "0.1.2"

from knowledge_base_builder.llm_client import LLMClient
from knowledge_base_builder.gemini_client import GeminiClient
from knowledge_base_builder.openai_client import OpenAIClient
from knowledge_base_builder.anthropic_client import AnthropicClient
from knowledge_base_builder.llm import LLM
from knowledge_base_builder.kb_builder import KBBuilder
from knowledge_base_builder.base_processor import BaseProcessor
from knowledge_base_builder.pdf_processor import PDFProcessor
from knowledge_base_builder.document_processor import DocumentProcessor
from knowledge_base_builder.spreadsheet_processor import SpreadsheetProcessor
from knowledge_base_builder.web_content_processor import WebContentProcessor
from knowledge_base_builder.website_processor import WebsiteProcessor
from knowledge_base_builder.github_processor import GitHubProcessor
from knowledge_base_builder.build_metadata import BuildMetadata, SourceResult
from knowledge_base_builder.cache import BuildCache

__all__ = [
    'LLMClient',
    'GeminiClient',
    'OpenAIClient',
    'AnthropicClient',
    'LLM',
    'KBBuilder',
    'BaseProcessor',
    'PDFProcessor',
    'DocumentProcessor',
    'SpreadsheetProcessor',
    'WebContentProcessor',
    'WebsiteProcessor',
    'GitHubProcessor',
    'BuildMetadata',
    'SourceResult',
    'BuildCache',
] 