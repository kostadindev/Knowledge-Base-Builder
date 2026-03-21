import os
import logging
from docx import Document
import markdown
import mistune
import re
from striprtf.striprtf import rtf_to_text
from langchain.text_splitter import RecursiveCharacterTextSplitter
from knowledge_base_builder.base_processor import BaseProcessor

logger = logging.getLogger(__name__)

try:
    from markitdown import MarkItDown
    _MARKITDOWN_AVAILABLE = True
except ImportError:
    _MARKITDOWN_AVAILABLE = False

class DocumentProcessor(BaseProcessor):
    """Handle document processing for .docx, .txt, .md, and .rtf files."""

    SUPPORTED_EXTENSIONS = ['.docx', '.txt', '.md', '.rtf']

    @staticmethod
    def download(url: str) -> str:
        """Download a document from a URL or load from local file."""
        return BaseProcessor.download(url, DocumentProcessor.SUPPORTED_EXTENSIONS)

    @staticmethod
    def extract_text(file_path: str) -> str:
        """Extract text from document file based on its extension."""
        file_ext = os.path.splitext(file_path)[1].lower()

        if file_ext == '.docx':
            return DocumentProcessor._extract_from_docx(file_path)
        elif file_ext == '.txt':
            return DocumentProcessor._extract_from_txt(file_path)
        elif file_ext == '.md':
            return DocumentProcessor._extract_from_md(file_path)
        elif file_ext == '.rtf':
            return DocumentProcessor._extract_from_rtf(file_path)
        else:
            raise ValueError(f"Unsupported document format: {file_ext}")

    @staticmethod
    def _extract_from_docx(file_path: str) -> str:
        """Extract text from a .docx file."""
        if _MARKITDOWN_AVAILABLE:
            try:
                logger.info("Using MarkItDown backend for DOCX extraction: %s", file_path)
                result = MarkItDown().convert(file_path)
                return result.text_content
            except Exception as e:
                logger.warning(
                    "MarkItDown failed for %s, falling back to python-docx: %s",
                    file_path, e
                )

        logger.info("Using python-docx backend for DOCX extraction: %s", file_path)
        try:
            doc = Document(file_path)
            text = '\n'.join(paragraph.text for paragraph in doc.paragraphs)
            return text
        except Exception as e:
            raise Exception(f"Error extracting text from .docx file: {e}")

    @staticmethod
    def _extract_from_txt(file_path: str) -> str:
        """Extract text from a .txt file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                return file.read()
        except Exception as e:
            raise Exception(f"Error extracting text from .txt file: {e}")

    @staticmethod
    def _extract_from_md(file_path: str) -> str:
        """Extract text from a .md file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                md_content = file.read()

            # Option 1: Return raw markdown (often best for LLM processing)
            return md_content

            # Option 2: Convert to HTML and strip tags (uncomment if needed)
            # html = markdown.markdown(md_content)
            # text = re.sub('<[^<]+?>', '', html)
            # return text
        except Exception as e:
            raise Exception(f"Error extracting text from .md file: {e}")

    @staticmethod
    def _extract_from_rtf(file_path: str) -> str:
        """Extract text from a .rtf file."""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
                rtf_content = file.read()

            text = rtf_to_text(rtf_content)
            return text
        except Exception as e:
            raise Exception(f"Error extracting text from .rtf file: {e}")
