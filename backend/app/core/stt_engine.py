"""STT Engine — Speech-to-Text with pluggable providers.

Priority (CPU-optimized, near-zero cost):
  1. Groq Whisper API (FREE tier — fast, no local compute)
  2. faster-whisper (local CPU, INT8 quantized)
  3. Vosk (ultra-lightweight, offline)
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

import structlog

from config import settings

log = structlog.get_logger()


class STTEngine:
    """Unified Speech-to-Text interface."""

    def __init__(self) -> None:
        self._provider = settings.STT_PROVIDER
        self._groq_client: Any | None = None
        self._whisper_model: Any | None = None
        self._vosk_model: Any | None = None

    async def transcribe(self, audio_data: bytes, language: str = "en") -> str:
        """Transcribe audio bytes to text.

        Args:
            audio_data: Raw audio (WAV format preferred).
            language: BCP-47 language code.

        Returns:
            Transcribed text string.
        """
        providers = self._get_provider_order()
        last_error: Exception | None = None

        for provider in providers:
            try:
                text = await self._call_provider(provider, audio_data, language)
                log.debug("STT transcription", provider=provider, chars=len(text))
                return text
            except Exception as exc:
                log.warning("STT provider failed", provider=provider, error=str(exc))
                last_error = exc
                continue

        raise RuntimeError(f"All STT providers failed. Last: {last_error}")

    def _get_provider_order(self) -> list[str]:
        primary = self._provider
        order = [primary]
        fallbacks = ["groq_whisper", "faster_whisper", "vosk"]
        for fb in fallbacks:
            if fb != primary:
                order.append(fb)
        return order

    async def _call_provider(
        self, provider: str, audio_data: bytes, language: str
    ) -> str:
        if provider == "groq_whisper":
            return await self._transcribe_groq(audio_data, language)
        elif provider == "faster_whisper":
            return await self._transcribe_faster_whisper(audio_data, language)
        elif provider == "vosk":
            return await self._transcribe_vosk(audio_data)
        else:
            raise ValueError(f"Unknown STT provider: {provider}")

    async def _transcribe_groq(self, audio_data: bytes, language: str) -> str:
        """Use Groq Whisper API (free tier, very fast)."""
        if not settings.GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY not configured")

        if self._groq_client is None:
            from groq import AsyncGroq

            self._groq_client = AsyncGroq(
                api_key=settings.GROQ_API_KEY.get_secret_value()
            )

        # Write to temp file (Groq requires file-like object)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            with open(tmp_path, "rb") as f:
                transcription = await self._groq_client.audio.transcriptions.create(
                    file=("audio.wav", f, "audio/wav"),
                    model="whisper-large-v3-turbo",
                    language=language,
                    response_format="text",
                )
            return str(transcription).strip()
        finally:
            os.unlink(tmp_path)

    async def _transcribe_faster_whisper(self, audio_data: bytes, language: str) -> str:
        """Use faster-whisper locally (CPU, INT8 quantized — free)."""
        import asyncio

        if self._whisper_model is None:
            try:
                from faster_whisper import WhisperModel

                self._whisper_model = WhisperModel(
                    settings.WHISPER_MODEL_SIZE,
                    device="cpu",
                    compute_type="int8",
                )
                log.info(
                    "faster-whisper model loaded",
                    size=settings.WHISPER_MODEL_SIZE,
                )
            except ImportError:
                raise RuntimeError(
                    "faster-whisper not installed. Install with: pip install faster-whisper"
                )

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            # Run in thread pool to avoid blocking event loop
            loop = asyncio.get_event_loop()
            segments, _ = await loop.run_in_executor(
                None,
                lambda: self._whisper_model.transcribe(
                    tmp_path, language=language if language != "en" else None
                ),
            )
            return " ".join(seg.text for seg in segments).strip()
        finally:
            os.unlink(tmp_path)

    async def _transcribe_vosk(self, audio_data: bytes) -> str:
        """Use Vosk (ultra-lightweight, fully offline — free)."""
        import asyncio
        import json as json_lib

        if self._vosk_model is None:
            try:
                from vosk import Model

                if not os.path.exists(settings.VOSK_MODEL_PATH):
                    raise RuntimeError(
                        f"Vosk model not found at {settings.VOSK_MODEL_PATH}. "
                        "Download from https://alphacephei.com/vosk/models"
                    )
                self._vosk_model = Model(settings.VOSK_MODEL_PATH)
            except ImportError:
                raise RuntimeError("vosk not installed. Install with: pip install vosk")

        loop = asyncio.get_event_loop()

        def _run_vosk() -> str:
            from vosk import KaldiRecognizer

            rec = KaldiRecognizer(self._vosk_model, 16000)
            rec.AcceptWaveform(audio_data)
            result = json_lib.loads(rec.FinalResult())
            return result.get("text", "")

        return await loop.run_in_executor(None, _run_vosk)


# Singleton
_stt_engine: STTEngine | None = None


def get_stt_engine() -> STTEngine:
    global _stt_engine
    if _stt_engine is None:
        _stt_engine = STTEngine()
    return _stt_engine
