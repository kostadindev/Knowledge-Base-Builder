"""Utilities for running coroutines from synchronous code.

The builder exposes a synchronous API but drives async LLM/IO work internally.
Naively using ``asyncio.get_event_loop().run_until_complete(...)`` raises
``RuntimeError: This event loop is already running`` when called from within an
already-running event loop -- most notably Jupyter/Colab, which is exactly where
many users run this library (and whose notebooks it ingests).

To be robust everywhere, all coroutines are executed on a single, dedicated
background-thread event loop. Using one *persistent* loop (rather than a fresh
``asyncio.run`` per call) keeps asyncio primitives such as ``asyncio.Semaphore``
bound to a consistent loop across successive calls.
"""

import asyncio
import threading
from typing import Any, Coroutine

__all__ = ["run_sync"]


class _BackgroundLoop:
    """Lazily-started event loop running on a daemon thread."""

    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock = threading.Lock()

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        loop = self._loop
        if loop is not None and not loop.is_closed():
            return loop
        with self._lock:
            loop = self._loop
            if loop is not None and not loop.is_closed():
                return loop
            loop = asyncio.new_event_loop()
            thread = threading.Thread(
                target=self._run_loop, args=(loop,), daemon=True, name="kbb-async-loop"
            )
            thread.start()
            self._loop = loop
            return loop

    @staticmethod
    def _run_loop(loop: asyncio.AbstractEventLoop) -> None:
        asyncio.set_event_loop(loop)
        loop.run_forever()

    def run(self, coro: "Coroutine[Any, Any, Any]") -> Any:
        loop = self._ensure_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result()


_runner = _BackgroundLoop()


def run_sync(coro: "Coroutine[Any, Any, Any]") -> Any:
    """Run *coro* to completion and return its result.

    Safe to call from ordinary synchronous code *and* from within an
    already-running event loop (the coroutine runs on a separate background loop,
    so it never conflicts with the caller's loop).
    """
    return _runner.run(coro)
