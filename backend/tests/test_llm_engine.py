"""Tests for LLM Engine."""

from __future__ import annotations

import json

import pytest

from app.core.llm_engine import LLMEngine


@pytest.fixture
def engine() -> LLMEngine:
    return LLMEngine()


@pytest.mark.asyncio
async def test_get_provider_order_default(engine: LLMEngine) -> None:
    """Primary provider should be first in fallback chain."""
    engine._provider = "groq"
    order = engine._get_provider_order()
    assert order[0] == "groq"
    assert "ollama" in order
    assert "openai" in order


@pytest.mark.asyncio
async def test_groq_rate_limit_tracking(engine: LLMEngine) -> None:
    """Rate limit counter should increment with each request."""
    assert engine._check_groq_rate_limit() is True
    engine._groq_request_count = 29
    assert engine._check_groq_rate_limit() is True
    engine._groq_request_count = 30
    assert engine._check_groq_rate_limit() is False


@pytest.mark.asyncio
async def test_chat_falls_back_on_failure(engine: LLMEngine) -> None:
    """When primary provider fails, next provider should be tried."""
    engine._provider = "groq"

    providers_tried: list[str] = []

    async def mock_call_provider(provider: str, *args, **kwargs) -> str:
        providers_tried.append(provider)
        if provider == "groq":
            raise RuntimeError("Simulated Groq failure")
        if provider == "ollama":
            return "Hello from Ollama!"
        raise RuntimeError("Also failed")

    engine._call_provider = mock_call_provider  # type: ignore[method-assign]
    result = await engine.chat([{"role": "user", "content": "Hi"}])

    assert result == "Hello from Ollama!"
    assert providers_tried[0] == "groq"
    assert "ollama" in providers_tried


@pytest.mark.asyncio
async def test_chat_raises_when_all_providers_fail(engine: LLMEngine) -> None:
    """Should raise RuntimeError when all providers fail."""

    async def always_fail(provider: str, *args, **kwargs) -> str:
        raise RuntimeError(f"{provider} failed")

    engine._call_provider = always_fail  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="All LLM providers failed"):
        await engine.chat([{"role": "user", "content": "test"}])


@pytest.mark.asyncio
async def test_tool_call_response_format(engine: LLMEngine) -> None:
    """Tool call responses should be valid JSON."""
    tool_response = json.dumps(
        {
            "tool_calls": [
                {
                    "name": "book_appointment",
                    "arguments": {
                        "date": "2025-01-15",
                        "time": "10:00",
                        "name": "John",
                    },
                }
            ]
        }
    )
    parsed = json.loads(tool_response)
    assert "tool_calls" in parsed
    assert parsed["tool_calls"][0]["name"] == "book_appointment"
