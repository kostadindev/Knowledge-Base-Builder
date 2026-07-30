import logging
import asyncio
import time
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage

from knowledge_base_builder.llm_client import LLMClient
from knowledge_base_builder.async_utils import run_sync

logger = logging.getLogger(__name__)

class GeminiClient(LLMClient):
    """Asynchronous client for Google's Gemini AI via LangChain."""
    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.0-flash",
        temperature: float = 0.7,
        max_retries: int = 3,
        max_concurrency: int = 8,
    ):
        super().__init__(api_key, model, temperature, max_retries, max_concurrency)
        self.llm = ChatGoogleGenerativeAI(
            model=model,
            temperature=temperature,
            api_key=api_key,
        )

    async def run_async(self, prompt: str) -> str:
        """
        Send prompt to Gemini and return the response.
        Uses retries + exponential backoff.
        """
        start_time = time.time()
        for attempt in range(1, self.max_retries + 1):
            try:
                async with self._sem:
                    result = await self.llm.ainvoke([HumanMessage(content=prompt)])
                    end_time = time.time()
                    logger.debug(f" Gemini API call: {end_time - start_time:.2f} seconds")
                    return result.content if hasattr(result, "content") else result
            except Exception as e:
                if attempt == self.max_retries:
                    end_time = time.time()
                    logger.debug(f" Gemini API call failed after {end_time - start_time:.2f} seconds and {attempt} attempts")
                    raise
                # backoff: 2, 4, 8, ...
                backoff_time = 2 ** attempt
                logger.warning(f" Gemini API call attempt {attempt} failed, retrying in {backoff_time} seconds...")
                await asyncio.sleep(backoff_time)

    # Keep a synchronous alias if you still need it elsewhere
    def run(self, prompt: str) -> str:
        start_time = time.time()
        result = run_sync(self.run_async(prompt))
        end_time = time.time()
        logger.debug(f" Gemini API call (sync): {end_time - start_time:.2f} seconds")
        return result.content if hasattr(result, "content") else result