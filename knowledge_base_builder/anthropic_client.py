import logging
import asyncio
import time
from langchain_anthropic import ChatAnthropic
from langchain.schema import HumanMessage

from knowledge_base_builder.llm_client import LLMClient

logger = logging.getLogger(__name__)

class AnthropicClient(LLMClient):
    """Asynchronous client for Anthropic's Claude models via LangChain."""
    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-7-sonnet",
        temperature: float = 0.7,
        max_retries: int = 3,
        max_concurrency: int = 8,
    ):
        super().__init__(api_key, model, temperature, max_retries, max_concurrency)
        self.llm = ChatAnthropic(
            model=model,
            temperature=temperature,
            anthropic_api_key=api_key,
        )

    async def run_async(self, prompt: str) -> str:
        """
        Send prompt to Anthropic and return the response.
        Uses retries + exponential backoff.
        """
        start_time = time.time()
        for attempt in range(1, self.max_retries + 1):
            try:
                async with self._sem:
                    result = await self.llm.ainvoke([HumanMessage(content=prompt)])
                    end_time = time.time()
                    logger.debug(f" Anthropic API call: {end_time - start_time:.2f} seconds")
                    return result.content if hasattr(result, "content") else result
            except Exception as e:
                if attempt == self.max_retries:
                    end_time = time.time()
                    logger.debug(f" Anthropic API call failed after {end_time - start_time:.2f} seconds and {attempt} attempts")
                    raise
                # backoff: 2, 4, 8, ...
                backoff_time = 2 ** attempt
                logger.warning(f" Anthropic API call attempt {attempt} failed, retrying in {backoff_time} seconds...")
                await asyncio.sleep(backoff_time) 