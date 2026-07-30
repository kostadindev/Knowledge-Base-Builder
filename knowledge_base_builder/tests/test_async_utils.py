"""Tests for async_utils.run_sync — the Jupyter/running-loop safety fix."""

import asyncio

import pytest

from knowledge_base_builder.async_utils import run_sync
from knowledge_base_builder.llm_client import LLMClient


def test_run_sync_returns_result():
    async def coro():
        await asyncio.sleep(0)
        return 42

    assert run_sync(coro()) == 42


def test_run_sync_propagates_exceptions():
    async def boom():
        raise ValueError("kaboom")

    with pytest.raises(ValueError, match="kaboom"):
        run_sync(boom())


def test_run_sync_reuses_one_loop_across_calls():
    """A Semaphore reused across calls proves all coroutines share one loop.

    asyncio primitives bind to the first loop that awaits them; using them on a
    second, different loop raises RuntimeError. If run_sync spun up a fresh loop
    per call, the second call would fail.
    """
    sem = asyncio.Semaphore(1)

    async def use_sem(value):
        async with sem:
            await asyncio.sleep(0)
            return value

    assert run_sync(use_sem("a")) == "a"
    assert run_sync(use_sem("b")) == "b"


def test_run_sync_works_inside_running_loop():
    """The core regression: calling run_sync from within a running loop.

    Under the old ``asyncio.get_event_loop().run_until_complete`` pattern this
    raised ``RuntimeError: This event loop is already running`` — exactly what
    broke the library in Jupyter/Colab.
    """
    async def inner():
        await asyncio.sleep(0)
        return "ok"

    async def outer():
        # A loop is running on this thread right now.
        return run_sync(inner())

    assert asyncio.run(outer()) == "ok"


def test_full_build_multichunk_shares_one_loop(tmp_path):
    """Realistic build: real LLMClient + semaphores, only the network mocked.

    A large input produces several LLM chunks, so run_sync is invoked multiple
    times. If those calls used different event loops, the client/LLM semaphores
    would raise 'bound to a different event loop'. This asserts the persistent
    background loop keeps them consistent.
    """
    from unittest.mock import AsyncMock, MagicMock, patch
    from knowledge_base_builder.kb_builder import KBBuilder

    big = "word " * 40000  # ~200k chars -> multiple ~80k-char chunks
    src = tmp_path / "big.txt"
    src.write_text(big, encoding="utf-8")

    with patch("knowledge_base_builder.gemini_client.ChatGoogleGenerativeAI"):
        builder = KBBuilder({"GOOGLE_API_KEY": "fake"})

    # Mock only the network layer; keep real run_async + real semaphores.
    resp = MagicMock()
    resp.content = "## Section\n\nstructured content"
    builder.llm_client.llm.ainvoke = AsyncMock(return_value=resp)

    out = str(tmp_path / "kb.md")
    result = builder.build(sources={"files": [str(src)]}, output_file=out, metadata=False)

    assert result == out
    assert builder.llm_client.llm.ainvoke.call_count >= 2
    with open(out, encoding="utf-8") as f:
        assert "Section" in f.read()


def test_llm_client_run_inside_running_loop():
    """LLMClient.run() (sync wrapper) must work from within a running loop."""

    class DummyClient(LLMClient):
        async def run_async(self, prompt: str) -> str:
            await asyncio.sleep(0)
            return f"resp:{prompt}"

    client = DummyClient(api_key="x", model="m")

    async def outer():
        return client.run("hello")

    assert asyncio.run(outer()) == "resp:hello"
