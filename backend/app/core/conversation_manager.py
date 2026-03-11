"""Conversation Manager — manages state for active calls."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ConversationState:
    """State for a single active call."""

    call_id: str
    agent_id: str
    organization_id: str
    messages: list[dict[str, str]] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    turn_count: int = 0
    is_active: bool = True
    escalated: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_message(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})
        if role == "user":
            self.turn_count += 1

    def get_messages(self, max_turns: int = 20) -> list[dict[str, str]]:
        """Return last N turns to keep context window manageable."""
        # Always keep system message if present
        if self.messages and self.messages[0]["role"] == "system":
            system = self.messages[:1]
            recent = self.messages[1:][-max_turns * 2 :]
            return system + recent
        return self.messages[-max_turns * 2 :]


class ConversationManager:
    """In-memory store for active call states."""

    def __init__(self) -> None:
        self._sessions: dict[str, ConversationState] = {}
        self._lock = asyncio.Lock()

    async def create(
        self, call_id: str, agent_id: str, organization_id: str
    ) -> ConversationState:
        async with self._lock:
            state = ConversationState(
                call_id=call_id,
                agent_id=agent_id,
                organization_id=organization_id,
            )
            self._sessions[call_id] = state
            return state

    async def get(self, call_id: str) -> ConversationState | None:
        return self._sessions.get(call_id)

    async def update(self, state: ConversationState) -> None:
        async with self._lock:
            self._sessions[state.call_id] = state

    async def end(self, call_id: str) -> ConversationState | None:
        async with self._lock:
            state = self._sessions.pop(call_id, None)
            if state:
                state.is_active = False
            return state

    def active_count(self) -> int:
        return len(self._sessions)


# Singleton
_conversation_manager: ConversationManager | None = None


def get_conversation_manager() -> ConversationManager:
    global _conversation_manager
    if _conversation_manager is None:
        _conversation_manager = ConversationManager()
    return _conversation_manager
