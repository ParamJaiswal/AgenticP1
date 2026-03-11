"""Voice Agent — configurable per-tenant AI brain.

Each company gets their own agent configuration including:
- Personality and greeting
- Available tools
- Escalation rules
- Business hours
- FAQ knowledge
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Any

import structlog

from app.core.conversation_manager import ConversationState
from app.core.llm_engine import get_llm_engine
from app.core.tool_executor import ToolExecutor, get_enabled_tools

log = structlog.get_logger()

PERSONALITY_PROMPTS = {
    "friendly": "You are a warm, friendly, and helpful customer service agent. Be conversational and empathetic.",
    "professional": "You are a professional, efficient, and courteous customer service agent. Be concise and accurate.",
    "casual": "You are a casual, relaxed customer service agent. Speak naturally and informally.",
}


class VoiceAgent:
    """AI agent brain — processes user speech and generates responses."""

    def __init__(self, agent_config: dict[str, Any]) -> None:
        self._config = agent_config
        self._llm = get_llm_engine()
        self._tool_executor = ToolExecutor(agent_config)

    def _build_system_prompt(self) -> str:
        """Build the system prompt from agent configuration."""
        personality = self._config.get("personality", "professional")
        personality_desc = PERSONALITY_PROMPTS.get(personality, PERSONALITY_PROMPTS["professional"])

        if self._config.get("custom_prompt"):
            personality_desc = self._config["custom_prompt"]

        company_name = self._config.get("name", "our company")
        industry = self._config.get("industry", "business")

        tools_config = self._config.get("tools_enabled", {})
        enabled_tools = [name for name, enabled in tools_config.items() if enabled]
        tools_desc = (
            f"You have access to these tools: {', '.join(enabled_tools)}."
            if enabled_tools
            else "You don't have specific tool access."
        )

        # FAQ section
        faqs = self._config.get("faqs") or []
        faq_section = ""
        if faqs:
            faq_lines = "\n".join(
                f"Q: {faq['question']}\nA: {faq['answer']}" for faq in faqs[:10]
            )
            faq_section = f"\n\nFrequently Asked Questions:\n{faq_lines}"

        # Escalation keywords
        escalation_config = self._config.get("escalation_rules", {})
        escalation_keywords = escalation_config.get(
            "keywords", ["human", "agent", "manager", "supervisor"]
        )

        system_prompt = f"""You are a voice AI customer service agent for {company_name} ({industry}).

{personality_desc}

{tools_desc}

Important rules:
- Keep responses SHORT and conversational (under 3 sentences for voice).
- If the customer asks to speak to a human, says "{'" or "'.join(escalation_keywords[:3])}", use transfer_to_human tool.
- Be helpful and resolve issues efficiently.
- Do not make up information — say "I'll need to check on that" if unsure.
- You are on a phone call. Do not use markdown, lists, or special characters.{faq_section}"""

        return system_prompt

    def _check_business_hours(self) -> bool:
        """Returns True if currently within business hours."""
        business_hours = self._config.get("business_hours")
        if not business_hours:
            return True  # No restriction = always open

        now = datetime.now()
        day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        today = day_names[now.weekday()]

        day_config = business_hours.get(today)
        if not day_config:
            return False  # Closed today

        try:
            open_h, open_m = map(int, day_config["open"].split(":"))
            close_h, close_m = map(int, day_config["close"].split(":"))
            open_time = time(open_h, open_m)
            close_time = time(close_h, close_m)
            return open_time <= now.time() <= close_time
        except (KeyError, ValueError):
            return True

    async def process_turn(
        self, state: ConversationState, user_text: str
    ) -> tuple[str, bool]:
        """Process a conversation turn.

        Args:
            state: Current conversation state.
            user_text: Transcribed user speech.

        Returns:
            (response_text, should_transfer_to_human)
        """
        # Add user message
        state.add_message("user", user_text)

        # Check if outside business hours
        if not self._check_business_hours() and state.turn_count == 1:
            response = (
                f"Thank you for calling {self._config.get('name', 'us')}. "
                "We are currently closed. Please call back during business hours. "
                "Goodbye!"
            )
            state.add_message("assistant", response)
            return response, False

        # Check escalation triggers
        escalation_config = self._config.get("escalation_rules", {})
        keywords = escalation_config.get("keywords", ["human", "agent", "manager"])
        user_lower = user_text.lower()
        if any(kw in user_lower for kw in keywords):
            response = "Of course! Let me transfer you to a human agent right away. Please hold."
            state.add_message("assistant", response)
            return response, True

        # Max turns check
        max_turns = escalation_config.get("max_turns_before_escalation", 10)
        if state.turn_count > max_turns:
            response = "I'll transfer you to a team member who can better assist you. Please hold."
            state.add_message("assistant", response)
            return response, True

        # Build tools list
        tools_config = self._config.get("tools_enabled", {})
        tools = get_enabled_tools(tools_config) if any(tools_config.values()) else None

        # Get LLM response
        system_prompt = self._build_system_prompt()
        messages = state.get_messages()

        llm_response = await self._llm.chat(
            messages=messages,
            system_prompt=system_prompt,
            tools=tools,
            temperature=0.7,
            max_tokens=256,  # Short for voice
        )

        # Check for tool call
        tool_result, tool_name = await self._tool_executor.execute_llm_response(
            llm_response
        )

        if tool_name == "transfer_to_human":
            response = "Let me transfer you to a human agent. Please hold."
            state.add_message("assistant", response)
            return response, True

        if tool_result:
            # Get LLM to phrase the tool result naturally
            state.add_message("tool", f"Tool result for {tool_name}: {tool_result}")
            response = await self._llm.chat(
                messages=state.get_messages(),
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=128,
            )
        else:
            response = llm_response

        state.add_message("assistant", response)
        return response, False


def create_voice_agent(agent_config: dict[str, Any]) -> VoiceAgent:
    """Factory function for creating voice agents."""
    return VoiceAgent(agent_config)
