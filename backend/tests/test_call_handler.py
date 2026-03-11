"""Tests for Call Handler."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Import all models first to ensure SQLAlchemy relationships are resolved
import app.models  # noqa: F401

from app.core.call_handler import CallHandler
from app.core.conversation_manager import get_conversation_manager


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.add = MagicMock()
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.execute = AsyncMock()
    return db


SAMPLE_AGENT_CONFIG = {
    "id": "agent-1",
    "name": "Support Agent",
    "greeting_message": "Hello! How can I assist you today?",
    "personality": "professional",
    "tools_enabled": {"transfer_to_human": True},
    "escalation_rules": {"keywords": ["human"], "max_turns_before_escalation": 10},
    "business_hours": None,
    "faqs": None,
    "voice_id": None,
    "language": "en",
    "industry": "general",
    "custom_prompt": None,
}


@pytest.mark.asyncio
async def test_handle_inbound_call_returns_greeting() -> None:
    """Inbound call handler should return greeting text and audio."""
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    fake_audio = b"FAKEAUDIO"

    with (
        patch("app.core.call_handler.get_tts_engine") as mock_tts_factory,
        patch("app.core.call_handler.get_stt_engine"),
    ):
        mock_tts = MagicMock()
        mock_tts.synthesize = AsyncMock(return_value=fake_audio)
        mock_tts_factory.return_value = mock_tts

        handler = CallHandler(mock_db)
        greeting_text, greeting_audio = await handler.handle_inbound_call(
            call_id="call-123",
            caller_number="+15551234567",
            called_number="+15559876543",
            agent_config=SAMPLE_AGENT_CONFIG,
            organization_id="org-1",
        )

    assert greeting_text == "Hello! How can I assist you today?"
    assert greeting_audio == fake_audio


@pytest.mark.asyncio
async def test_process_audio_chunk_returns_response() -> None:
    """Audio processing should return transcription and TTS response."""
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()

    # Pre-create conversation state
    mgr = get_conversation_manager()
    await mgr.create("call-456", "agent-1", "org-1")

    with (
        patch("app.core.call_handler.get_stt_engine") as mock_stt_factory,
        patch("app.core.call_handler.get_tts_engine") as mock_tts_factory,
        patch("app.core.call_handler.create_voice_agent") as mock_agent_factory,
    ):
        mock_stt = MagicMock()
        mock_stt.transcribe = AsyncMock(return_value="I need help with my order")
        mock_stt_factory.return_value = mock_stt

        mock_tts = MagicMock()
        mock_tts.synthesize = AsyncMock(return_value=b"RESPONSE_AUDIO")
        mock_tts_factory.return_value = mock_tts

        mock_agent = MagicMock()
        mock_agent.process_turn = AsyncMock(
            return_value=("I can help you with your order.", False)
        )
        mock_agent_factory.return_value = mock_agent

        handler = CallHandler(mock_db)
        text, audio, should_transfer = await handler.process_audio_chunk(
            call_id="call-456",
            audio_data=b"AUDIO",
            agent_config=SAMPLE_AGENT_CONFIG,
        )

    assert text == "I can help you with your order."
    assert audio == b"RESPONSE_AUDIO"
    assert should_transfer is False

    # Cleanup
    await mgr.end("call-456")
