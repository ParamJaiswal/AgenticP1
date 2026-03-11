"""Tests for Voice Agent."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.core.conversation_manager import ConversationState
from app.core.voice_agent import VoiceAgent


def make_state(turn_count: int = 0) -> ConversationState:
    state = ConversationState(
        call_id="test-call",
        agent_id="test-agent",
        organization_id="test-org",
    )
    state.turn_count = turn_count
    return state


BASIC_AGENT_CONFIG = {
    "id": "test-agent",
    "name": "Test Dental Clinic",
    "description": "Dental clinic AI",
    "industry": "healthcare",
    "personality": "professional",
    "greeting_message": "Hello! Thank you for calling Test Dental Clinic.",
    "tools_enabled": {
        "book_appointment": True,
        "transfer_to_human": True,
        "check_order_status": False,
        "send_sms": False,
        "add_to_waitlist": False,
    },
    "escalation_rules": {
        "sentiment_threshold": -0.5,
        "max_turns_before_escalation": 10,
        "keywords": ["human", "agent", "manager"],
    },
    "business_hours": None,
    "faqs": None,
}


@pytest.fixture
def agent() -> VoiceAgent:
    return VoiceAgent(BASIC_AGENT_CONFIG)


@pytest.mark.asyncio
async def test_escalation_keyword_triggers_transfer(agent: VoiceAgent) -> None:
    """'human' keyword should trigger escalation."""
    state = make_state()
    response, should_transfer = await agent.process_turn(
        state, "I want to speak to a human"
    )
    assert should_transfer is True


@pytest.mark.asyncio
async def test_escalation_on_max_turns(agent: VoiceAgent) -> None:
    """Exceeding max turns should trigger escalation."""
    state = make_state(turn_count=11)
    with patch.object(
        agent._llm, "chat", new_callable=AsyncMock, return_value="I can help you!"
    ):
        response, should_transfer = await agent.process_turn(state, "Help me please")
    assert should_transfer is True


@pytest.mark.asyncio
async def test_normal_turn_no_escalation(agent: VoiceAgent) -> None:
    """Normal conversation should not trigger escalation."""
    state = make_state()
    mock_response = "We have appointments available on Monday and Wednesday."

    with patch.object(
        agent._llm, "chat", new_callable=AsyncMock, return_value=mock_response
    ):
        response, should_transfer = await agent.process_turn(
            state, "I would like to book a dental appointment"
        )

    assert should_transfer is False
    assert len(response) > 0


def test_build_system_prompt_includes_company_name(agent: VoiceAgent) -> None:
    """System prompt should include the company name."""
    prompt = agent._build_system_prompt()
    assert "Test Dental Clinic" in prompt


def test_build_system_prompt_professional_personality(agent: VoiceAgent) -> None:
    """Professional personality prompt should mention 'professional'."""
    prompt = agent._build_system_prompt()
    assert "professional" in prompt.lower()


def test_business_hours_none_returns_true(agent: VoiceAgent) -> None:
    """No business hours config means always open."""
    assert agent._check_business_hours() is True
