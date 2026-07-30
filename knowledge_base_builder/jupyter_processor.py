import json
import logging
from knowledge_base_builder.base_processor import BaseProcessor

logger = logging.getLogger(__name__)

class JupyterProcessor(BaseProcessor):
    SUPPORTED_EXTENSIONS = ['.ipynb']

    @staticmethod
    def download(url: str) -> str:
        return BaseProcessor.download(url, JupyterProcessor.SUPPORTED_EXTENSIONS)

    @staticmethod
    def extract_text(file_path: str) -> str:
        logger.info("Extracting cells from notebook: %s", file_path)
        with open(file_path, 'r', encoding='utf-8') as f:
            nb = json.load(f)

        # Detect kernel language
        kernel = nb.get('metadata', {}).get('kernelspec', {}).get('language', 'python')
        cells = nb.get('cells', [])

        parts = []
        for i, cell in enumerate(cells):
            cell_type = cell.get('cell_type', '')
            source = ''.join(cell.get('source', []))

            if not source.strip():
                continue

            if cell_type == 'markdown':
                parts.append(source)
            elif cell_type == 'code':
                parts.append(f"```{kernel}\n{source}\n```")
                # Include text outputs
                for output in cell.get('outputs', []):
                    if output.get('output_type') == 'stream':
                        text = ''.join(output.get('text', []))
                        if text.strip():
                            parts.append(f"**Output:**\n```\n{text.strip()}\n```")
                    elif 'text/plain' in output.get('data', {}):
                        text = ''.join(output['data']['text/plain'])
                        if text.strip():
                            parts.append(f"**Output:**\n```\n{text.strip()}\n```")
            elif cell_type == 'raw':
                parts.append(source)

        return '\n\n'.join(parts)
