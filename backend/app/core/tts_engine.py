"""TTS Engine — Text-to-Speech with pluggable CPU-optimized providers.

Priority (CPU-only, near-zero cost):
  1. Piper TTS (neural, CPU, low-latency, free, offline)
  2. Edge TTS (Microsoft free, high quality, needs internet)
  3. gTTS (Google free, decent quality, needs internet)
"""

from __future__ import annotations

import asyncio
import io
import os
import tempfile
from typing import Any

import structlog

from config import settings

log = structlog.get_logger()

# Cache for repeated phrases to reduce API calls
_phrase_cache: dict[str, bytes] = {}
_CACHE_MAX = 200


class TTSEngine:
    """Unified Text-to-Speech interface."""

    def __init__(self) -> None:
        self._provider = settings.TTS_PROVIDER
        self._piper_process: Any | None = None

    async def synthesize(self, text: str, voice_id: str | None = None) -> bytes:
        """Convert text to audio bytes (WAV format).

        Args:
            text: Text to synthesize.
            voice_id: Optional voice identifier (provider-specific).

        Returns:
            Audio bytes in WAV/MP3 format.
        """
        cache_key = f"{self._provider}:{voice_id or 'default'}:{text}"
        if cache_key in _phrase_cache:
            return _phrase_cache[cache_key]

        providers = self._get_provider_order()
        last_error: Exception | None = None

        for provider in providers:
            try:
                audio = await self._call_provider(provider, text, voice_id)
                # Cache if small enough
                if len(_phrase_cache) < _CACHE_MAX:
                    _phrase_cache[cache_key] = audio
                return audio
            except Exception as exc:
                log.warning("TTS provider failed", provider=provider, error=str(exc))
                last_error = exc
                continue

        raise RuntimeError(f"All TTS providers failed. Last: {last_error}")

    def _get_provider_order(self) -> list[str]:
        primary = self._provider
        order = [primary]
        fallbacks = ["piper", "edge_tts", "gtts"]
        for fb in fallbacks:
            if fb != primary:
                order.append(fb)
        return order

    async def _call_provider(
        self, provider: str, text: str, voice_id: str | None
    ) -> bytes:
        if provider == "piper":
            return await self._synthesize_piper(text, voice_id)
        elif provider == "edge_tts":
            return await self._synthesize_edge_tts(text, voice_id)
        elif provider == "gtts":
            return await self._synthesize_gtts(text)
        else:
            raise ValueError(f"Unknown TTS provider: {provider}")

    async def _synthesize_piper(self, text: str, voice_id: str | None) -> bytes:
        """Use Piper TTS (offline, neural, CPU-friendly)."""
        voice = voice_id or settings.PIPER_VOICE
        model_path = os.path.join(settings.PIPER_MODEL_PATH, f"{voice}.onnx")
        config_path = model_path + ".json"

        if not os.path.exists(model_path):
            raise RuntimeError(
                f"Piper model not found at {model_path}. "
                "Download from https://github.com/rhasspy/piper/releases"
            )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out_file:
            out_path = out_file.name

        try:
            proc = await asyncio.create_subprocess_exec(
                "piper",
                "--model",
                model_path,
                "--config",
                config_path,
                "--output_file",
                out_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate(input=text.encode())
            with open(out_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(out_path):
                os.unlink(out_path)

    async def _synthesize_edge_tts(self, text: str, voice_id: str | None) -> bytes:
        """Use Microsoft Edge TTS (free, high quality, requires internet)."""
        try:
            import edge_tts
        except ImportError:
            raise RuntimeError("edge-tts not installed: pip install edge-tts")

        voice = voice_id or settings.EDGE_TTS_VOICE

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(tmp_path)
            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    async def _synthesize_gtts(self, text: str) -> bytes:
        """Use Google gTTS (free, requires internet)."""
        try:
            from gtts import gTTS
        except ImportError:
            raise RuntimeError("gtts not installed: pip install gtts")

        loop = asyncio.get_event_loop()

        def _run() -> bytes:
            tts = gTTS(text=text, lang=settings.TTS_LANGUAGE, slow=False)
            buf = io.BytesIO()
            tts.write_to_fp(buf)
            return buf.getvalue()

        return await loop.run_in_executor(None, _run)


# Singleton
_tts_engine: TTSEngine | None = None


def get_tts_engine() -> TTSEngine:
    global _tts_engine
    if _tts_engine is None:
        _tts_engine = TTSEngine()
    return _tts_engine
