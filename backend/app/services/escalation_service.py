"""Escalation service — smart human handoff."""

from __future__ import annotations

import structlog

from app.core.conversation_manager import ConversationState

log = structlog.get_logger()

ANGER_KEYWORDS = [
    "angry", "furious", "terrible", "awful", "horrible", "useless",
    "incompetent", "worst", "ridiculous", "unacceptable", "lawsuit",
    "lawyer", "sue", "refund", "cancel",
]


class EscalationService:
    """Determines when to escalate a call to a human agent."""

    def should_escalate(
        self,
        state: ConversationState,
        latest_user_text: str,
        agent_config: dict,
    ) -> tuple[bool, str]:
        """Check multiple escalation triggers.

        Returns:
            (should_escalate, reason)
        """
        rules = agent_config.get("escalation_rules", {})

        # 1. Explicit keywords
        keywords = rules.get("keywords", ["human", "agent", "manager"])
        text_lower = latest_user_text.lower()
        for kw in keywords:
            if kw in text_lower:
                return True, f"Keyword trigger: '{kw}'"

        # 2. Anger detection
        anger_count = sum(1 for kw in ANGER_KEYWORDS if kw in text_lower)
        if anger_count >= 2:
            return True, "Anger detected in customer message"

        # 3. Max turns
        max_turns = rules.get("max_turns_before_escalation", 15)
        if state.turn_count >= max_turns:
            return True, f"Max conversation turns reached ({max_turns})"

        # 4. Repeated same intent (no resolution)
        if state.turn_count >= 3:
            recent = state.messages[-6:]
            user_msgs = [m["content"].lower() for m in recent if m["role"] == "user"]
            if len(user_msgs) >= 2:
                # Simple repetition check
                if any(
                    self._similarity(user_msgs[-1], prev) > 0.7
                    for prev in user_msgs[:-1]
                ):
                    return True, "Customer repeating same question"

        return False, ""

    def _similarity(self, a: str, b: str) -> float:
        """Simple word-overlap similarity (no ML needed)."""
        words_a = set(a.split())
        words_b = set(b.split())
        if not words_a or not words_b:
            return 0.0
        intersection = words_a & words_b
        return len(intersection) / max(len(words_a), len(words_b))
