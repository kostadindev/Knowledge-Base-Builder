import asyncio
import logging
from typing import List, Tuple
import time

from knowledge_base_builder.llm_client import LLMClient

logger = logging.getLogger(__name__)

class LLM:
    """Build and merge KBs via LLM, with async I/O for preprocessing."""
    def __init__(self, llm_client: LLMClient, max_concurrency: int = 8):
        self.llm_client = llm_client
        # A simple semaphore to cap concurrent in-flight requests
        self._sem = asyncio.Semaphore(max_concurrency)

    def build(self, text: str) -> str:
        """Build a single KB chunk synchronously."""
        start_time = time.time()
        prompt = (
            "You are a knowledge base builder. Convert the following document into a well-structured "
            "Markdown knowledge base.\n\n"
            "Guidelines:\n"
            "- Use hierarchical headings (##, ###) to organize content by topic\n"
            "- Preserve all factual information, names, dates, and technical details\n"
            "- Use bullet points for lists and key facts\n"
            "- Keep code blocks, URLs, and structured data intact\n"
            "- Attribute information to its source when the source is identifiable\n"
            "- Prioritize completeness over brevity\n\n"
            f"---DOCUMENT START---\n{text}\n---DOCUMENT END---\n\n"
            "Return only the Markdown."
        )
        result = self.llm_client.run(prompt)
        end_time = time.time()
        client_name = self.llm_client.__class__.__name__
        logger.info(f"KB building with {client_name}: {end_time - start_time:.2f} seconds")
        return result

    async def preprocess_text_async(self, text: str) -> str:
        """Preprocess a single text document into a structured KB asynchronously."""
        start_time = time.time()
        prompt = (
            "You are a knowledge base builder. Convert the following document into a well-structured "
            "Markdown knowledge base.\n\n"
            "Guidelines:\n"
            "- Use hierarchical headings (##, ###) to organize content by topic\n"
            "- Preserve all factual information, names, dates, and technical details\n"
            "- Use bullet points for lists and key facts\n"
            "- Keep code blocks, URLs, and structured data intact\n"
            "- Attribute information to its source when the source is identifiable\n"
            "- Prioritize completeness over brevity\n\n"
            f"---DOCUMENT START---\n{text}\n---DOCUMENT END---\n\n"
            "Return only the Markdown."
        )
        async with self._sem:
            result = await self.llm_client.run_async(prompt)
        end_time = time.time()
        logger.debug(f"Document preprocessing: {end_time - start_time:.2f} seconds")
        return result

    async def preprocess_text_llms_txt_async(self, text: str, project_name: str = None) -> str:
        """Preprocess text into llms.txt spec format asynchronously."""
        start_time = time.time()
        name_instruction = (
            f'Use "{project_name}" as the H1 heading.'
            if project_name
            else "Infer the project or site name from the content for the H1 heading."
        )
        prompt = (
            "You are a knowledge base builder producing output in the llms.txt specification format "
            "(see llmstxt.org).\n\n"
            "Format requirements:\n"
            f"- {name_instruction}\n"
            "- Follow the H1 with a blockquote (> ) containing a one-sentence summary\n"
            "- Organize content under H2 (##) sections by topic\n"
            "- Within each section, list items as: - [Name](URL): Brief description\n"
            "- If no URL exists for a piece of information, omit the link: - **Name**: Description\n"
            "- Keep descriptions concise (one sentence each)\n"
            "- Preserve all source URLs found in the document\n\n"
            f"---DOCUMENT START---\n{text}\n---DOCUMENT END---\n\n"
            "Return only the llms.txt formatted output."
        )
        async with self._sem:
            result = await self.llm_client.run_async(prompt)
        end_time = time.time()
        logger.debug("llms.txt preprocessing: %.2f seconds", end_time - start_time)
        return result

    async def merge_all_kbs(self, kbs: List[str]) -> str:
        """Merge all preprocessed KBs into one final document."""
        if not kbs:
            return ""
            
        start_time = time.time()
        prompt = (
            "Merge the following knowledge bases into a single, well-organized Markdown document.\n\n"
            "Guidelines:\n"
            "- Combine related sections under common headings\n"
            "- Remove duplicate information but preserve all unique facts\n"
            "- Maintain a logical flow: overview first, then detailed sections\n"
            "- Preserve all source attributions\n"
            "- Do not add information that is not in the source documents\n\n" +
            "\n\n".join(f"---KB{i+1}---\n{kb}" for i, kb in enumerate(kbs)) +
            "\n\nReturn only the final Markdown."
        )
        async with self._sem:
            result = await self.llm_client.run_async(prompt)
        end_time = time.time()
        logger.info(f"Final KB merge ({len(kbs)} KBs): {end_time - start_time:.2f} seconds")
        return result

    async def process_documents(self, texts: List[str]) -> str:
        """
        Process multiple documents in two steps:
        1. Preprocess each document into a KB concurrently
        2. Merge all KBs into one final document
        """
        if not texts:
            return ""

        # Step 1: Preprocess all documents concurrently
        logger.info(f"Preprocessing {len(texts)} documents")
        preprocess_start = time.time()
        tasks = [asyncio.create_task(self.preprocess_text_async(text)) for text in texts]
        preprocessed_kbs = await asyncio.gather(*tasks)
        preprocess_end = time.time()
        logger.info(f"Preprocessing completed in {preprocess_end - preprocess_start:.2f} seconds")

        # Step 2: Merge all preprocessed KBs into one final document
        logger.info(f"Merging {len(preprocessed_kbs)} KBs into final document")
        final_kb = await self.merge_all_kbs(preprocessed_kbs)
        
        return final_kb