"""Call Handler — orchestrates the full call lifecycle.

Flow:
  1. Phone rings → Telnyx webhook → start WebSocket audio stream
  2. Audio chunks → STT Engine → text
  3. Text + conversation history + knowledge context → LLM → response
  4. Response text → TTS Engine → audio chunks
  5. Audio chunks → WebSocket → back to caller
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.conversation_manager import ConversationState, get_conversation_manager
from app.core.stt_engine import get_stt_engine
from app.core.tts_engine import get_tts_engine
from app.core.voice_agent import create_voice_agent
from app.models.call import Call
from app.models.conversation import ConversationTurn

log = structlog.get_logger()


class CallHandler:
    """Orchestrates a complete AI phone call."""

    def __init__(self, db: AsyncSession) -> None:
        self._db = db
        self._stt = get_stt_engine()
        self._tts = get_tts_engine()
        self._conv_manager = get_conversation_manager()

    async def handle_inbound_call(
        self,
        call_id: str,
        caller_number: str,
        called_number: str,
        agent_config: dict[str, Any],
        organization_id: str,
    ) -> tuple[str, bytes]:
        """Handle a new inbound call.

        Returns:
            (greeting_text, greeting_audio_bytes)
        """
        log.info(
            "Handling inbound call",
            call_id=call_id,
            caller=caller_number,
            agent=agent_config.get("name"),
        )

        # Create conversation state
        state = await self._conv_manager.create(
            call_id=call_id,
            agent_id=str(agent_config.get("id", "")),
            organization_id=organization_id,
        )

        # Generate greeting audio
        greeting = agent_config.get(
            "greeting_message",
            "Hello! Thank you for calling. How can I help you today?",
        )

        audio = await self._tts.synthesize(greeting, agent_config.get("voice_id"))

        # Log first assistant turn
        state.add_message("assistant", greeting)
        await self._conv_manager.update(state)

        return greeting, audio

    async def process_audio_chunk(
        self,
        call_id: str,
        audio_data: bytes,
        agent_config: dict[str, Any],
        language: str = "en",
    ) -> tuple[str, bytes, bool]:
        """Process an audio chunk from the caller.

        Returns:
            (user_text, response_audio, should_transfer)
        """
        state = await self._conv_manager.get(call_id)
        if state is None:
            raise ValueError(f"No active call state for call_id={call_id}")

        # STT: audio → text
        user_text = await self._stt.transcribe(audio_data, language=language)
        if not user_text.strip():
            return "", b"", False

        log.info("User said", call_id=call_id, text=user_text[:100])

        # AI: text → response
        agent = create_voice_agent(agent_config)
        response_text, should_transfer = await agent.process_turn(state, user_text)

        # TTS: response text → audio
        response_audio = await self._tts.synthesize(
            response_text, agent_config.get("voice_id")
        )

        # Persist turn
        await self._save_turn(call_id, "user", user_text)
        await self._save_turn(call_id, "assistant", response_text)

        await self._conv_manager.update(state)

        return response_text, response_audio, should_transfer

    async def end_call(
        self, call_id: str, resolution: str = "completed"
    ) -> ConversationState | None:
        """End a call and return the final conversation state."""
        state = await self._conv_manager.end(call_id)
        if state:
            # Update call record in DB
            from sqlalchemy import update

            duration = int(
                (datetime.utcnow() - state.started_at).total_seconds()
            )
            await self._db.execute(
                update(Call)
                .where(Call.id == call_id)
                .values(
                    status="completed",
                    ended_at=datetime.utcnow(),
                    duration_seconds=duration,
                    resolution=resolution,
                )
            )
            await self._db.commit()
            log.info(
                "Call ended",
                call_id=call_id,
                duration=duration,
                resolution=resolution,
            )
        return state

    async def _save_turn(self, call_id: str, role: str, content: str) -> None:
        """Persist a conversation turn to the database."""
        turn = ConversationTurn(call_id=call_id, role=role, content=content)
        self._db.add(turn)
        # Flush but don't commit (caller manages transaction)
        await self._db.flush()
