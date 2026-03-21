import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any
import time

logger = logging.getLogger(__name__)

class LLMClient(ABC):
    """Abstract base class for LLM clients."""
    
    def __init__(
        self,
        api_key: str,
        model: str,
        temperature: float = 0.7,
        max_retries: int = 3,
        max_concurrency: int = 8,
    ):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_retries = max_retries
        self._sem = asyncio.Semaphore(max_concurrency)
    
    @abstractmethod
    async def run_async(self, prompt: str) -> str:
        """Send prompt to the LLM and return the response asynchronously."""
        pass
    
    def run(self, prompt: str) -> str:
        """Synchronous wrapper for run_async."""
        start_time = time.time()
        result = asyncio.get_event_loop().run_until_complete(self.run_async(prompt))
        end_time = time.time()
        logger.debug(f"{self.__class__.__name__} API call (sync): {end_time - start_time:.2f} seconds")
        return result 