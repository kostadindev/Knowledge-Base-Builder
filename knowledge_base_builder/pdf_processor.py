import os
import logging
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from knowledge_base_builder.base_processor import BaseProcessor

logger = logging.getLogger(__name__)

try:
    from markitdown import MarkItDown
    _MARKITDOWN_AVAILABLE = True
except ImportError:
    _MARKITDOWN_AVAILABLE = False

class PDFProcessor(BaseProcessor):
    """Handle PDF document processing."""

    SUPPORTED_EXTENSIONS = ['.pdf']

    @staticmethod
    def download(url: str) -> str:
        """Download a PDF from a URL or load from local file."""
        return BaseProcessor.download(url, PDFProcessor.SUPPORTED_EXTENSIONS)

    @staticmethod
    def extract_text(pdf_path: str) -> str:
        """Extract text from a PDF file."""
        if _MARKITDOWN_AVAILABLE:
            try:
                logger.info("Using MarkItDown backend for PDF extraction: %s", pdf_path)
                result = MarkItDown().convert(pdf_path)
                return result.text_content
            except Exception as e:
                logger.warning(
                    "MarkItDown failed for %s, falling back to PyPDFLoader: %s",
                    pdf_path, e
                )

        logger.info("Using PyPDFLoader backend for PDF extraction: %s", pdf_path)
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
        splitter = RecursiveCharacterTextSplitter(chunk_size=20000, chunk_overlap=100)
        chunks = splitter.split_documents(documents)
        return "\n".join(chunk.page_content for chunk in chunks)
