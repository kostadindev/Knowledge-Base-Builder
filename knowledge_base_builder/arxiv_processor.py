import os
import json
import logging
import tempfile
from knowledge_base_builder.base_processor import BaseProcessor

logger = logging.getLogger(__name__)

try:
    import arxiv
    _ARXIV_AVAILABLE = True
except ImportError:
    _ARXIV_AVAILABLE = False

class ArxivProcessor(BaseProcessor):
    SUPPORTED_EXTENSIONS = ['.pdf']

    @staticmethod
    def is_arxiv_url(url: str) -> bool:
        """Check if URL or string is an arXiv reference."""
        import re
        return bool(re.search(r'arxiv\.org/(abs|pdf)/|^\d{4}\.\d{4,5}(v\d+)?$', url))

    @staticmethod
    def extract_arxiv_id(url: str) -> str:
        """Extract arXiv ID from URL or bare ID string."""
        import re
        # Match bare ID like 2301.12345 or 2301.12345v2
        m = re.search(r'(\d{4}\.\d{4,5}(?:v\d+)?)', url)
        if m:
            return m.group(1)
        raise ValueError(f"Could not extract arXiv ID from: {url}")

    @staticmethod
    def download(url: str) -> str:
        """Download arXiv paper PDF and save metadata sidecar."""
        if not _ARXIV_AVAILABLE:
            raise ImportError("arxiv is required. Install with: pip install arxiv")

        arxiv_id = ArxivProcessor.extract_arxiv_id(url)
        logger.info("Fetching arXiv paper: %s", arxiv_id)

        client = arxiv.Client()
        search = arxiv.Search(id_list=[arxiv_id])
        paper = next(client.results(search))

        # Download PDF
        tmp_dir = tempfile.mkdtemp()
        pdf_path = paper.download_pdf(dirpath=tmp_dir)

        # Save metadata as sidecar JSON
        meta = {
            'title': paper.title,
            'authors': [str(a) for a in paper.authors],
            'abstract': paper.summary,
            'published': str(paper.published),
            'categories': paper.categories,
            'arxiv_id': arxiv_id,
        }
        meta_path = pdf_path + '.meta.json'
        with open(meta_path, 'w') as f:
            json.dump(meta, f)

        return pdf_path

    @staticmethod
    def extract_text(file_path: str) -> str:
        """Extract text from arXiv PDF, prepending paper metadata."""
        from knowledge_base_builder.pdf_processor import PDFProcessor

        # Read metadata sidecar if exists
        meta_path = file_path + '.meta.json'
        header = ''
        if os.path.exists(meta_path):
            with open(meta_path) as f:
                meta = json.load(f)
            header = (
                f"# {meta.get('title', 'Untitled')}\n\n"
                f"**Authors:** {', '.join(meta.get('authors', []))}\n\n"
                f"**Published:** {meta.get('published', 'Unknown')}\n\n"
                f"**Categories:** {', '.join(meta.get('categories', []))}\n\n"
                f"## Abstract\n\n{meta.get('abstract', '')}\n\n"
                f"## Full Text\n\n"
            )

        pdf_text = PDFProcessor.extract_text(file_path)
        return header + pdf_text
