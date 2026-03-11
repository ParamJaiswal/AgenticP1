"""Tests for STT Engine."""

from __future__ import annotations

import pytest

from app.core.stt_engine import STTEngine


@pytest.fixture
def engine() -> STTEngine:
    return STTEngine()


@pytest.mark.asyncio
async def test_transcribe_falls_back_on_failure(engine: STTEngine) -> None:
    """When primary STT fails, should fall back to next provider."""
    engine._provider = "groq_whisper"
    providers_tried: list[str] = []

    async def mock_call_provider(provider: str, audio: bytes, language: str) -> str:
        providers_tried.append(provider)
        if provider == "groq_whisper":
            raise RuntimeError("No API key")
        return "Hello from fallback"

    engine._call_provider = mock_call_provider  # type: ignore[method-assign]
    result = await engine.transcribe(b"AUDIO")

    assert providers_tried[0] == "groq_whisper"
    assert result == "Hello from fallback"


@pytest.mark.asyncio
async def test_transcribe_raises_when_all_fail(engine: STTEngine) -> None:
    """Should raise RuntimeError when all STT providers fail."""

    async def always_fail(provider: str, *args, **kwargs) -> str:
        raise RuntimeError(f"{provider} unavailable")

    engine._call_provider = always_fail  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="All STT providers failed"):
        await engine.transcribe(b"AUDIO")


def test_provider_order_starts_with_primary(engine: STTEngine) -> None:
    """Provider order should start with the configured primary."""
    engine._provider = "faster_whisper"
    order = engine._get_provider_order()
    assert order[0] == "faster_whisper"
    assert "groq_whisper" in order
    assert "vosk" in order
