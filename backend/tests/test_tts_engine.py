"""Tests for TTS Engine."""

from __future__ import annotations


import pytest

from app.core.tts_engine import TTSEngine


@pytest.fixture
def engine() -> TTSEngine:
    return TTSEngine()


@pytest.mark.asyncio
async def test_synthesize_uses_cache_on_second_call(engine: TTSEngine) -> None:
    """Same text should be served from cache on second call."""
    fake_audio = b"FAKEAUDIO"

    call_count = 0

    async def mock_call_provider(provider: str, text: str, voice_id) -> bytes:
        nonlocal call_count
        call_count += 1
        return fake_audio

    engine._call_provider = mock_call_provider  # type: ignore[method-assign]

    result1 = await engine.synthesize("Hello world")
    result2 = await engine.synthesize("Hello world")

    assert result1 == fake_audio
    assert result2 == fake_audio
    assert call_count == 1  # Second call uses cache


@pytest.mark.asyncio
async def test_synthesize_falls_back_on_failure(engine: TTSEngine) -> None:
    """When primary TTS fails, should try next provider."""
    engine._provider = "piper"
    providers_tried: list[str] = []

    async def mock_call_provider(provider: str, text: str, voice_id) -> bytes:
        providers_tried.append(provider)
        if provider == "piper":
            raise RuntimeError("Piper not installed")
        return b"AUDIO_FROM_" + provider.encode()

    engine._call_provider = mock_call_provider  # type: ignore[method-assign]
    result = await engine.synthesize("Test fallback")

    assert providers_tried[0] == "piper"
    assert len(providers_tried) >= 2
    assert result.startswith(b"AUDIO_FROM_")


@pytest.mark.asyncio
async def test_synthesize_raises_when_all_fail(engine: TTSEngine) -> None:
    """Should raise RuntimeError when all TTS providers fail."""

    async def always_fail(provider: str, *args, **kwargs) -> bytes:
        raise RuntimeError(f"{provider} failed")

    engine._call_provider = always_fail  # type: ignore[method-assign]

    with pytest.raises(RuntimeError, match="All TTS providers failed"):
        await engine.synthesize("This should fail")
