"""Tool executor — function calling for AI agent actions.

Built-in tools:
  - book_appointment
  - check_order_status
  - transfer_to_human
  - send_sms
  - add_to_waitlist
"""

from __future__ import annotations

import json
from typing import Any

import structlog

log = structlog.get_logger()

# --- Tool schemas (for LLM function calling) ---

TOOL_DEFINITIONS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": "Book an appointment for a customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {"type": "string", "description": "Date (YYYY-MM-DD)"},
                    "time": {"type": "string", "description": "Time (HH:MM, 24h)"},
                    "name": {"type": "string", "description": "Customer full name"},
                    "phone": {"type": "string", "description": "Customer phone number"},
                    "service": {"type": "string", "description": "Service requested"},
                },
                "required": ["date", "time", "name", "phone"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_order_status",
            "description": "Check the status of a customer order",
            "parameters": {
                "type": "object",
                "properties": {
                    "order_id": {"type": "string", "description": "Order ID / number"},
                },
                "required": ["order_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_to_human",
            "description": "Transfer the call to a human agent",
            "parameters": {
                "type": "object",
                "properties": {
                    "reason": {"type": "string", "description": "Reason for transfer"},
                },
                "required": ["reason"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_to_waitlist",
            "description": "Add a customer to a service waitlist",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "phone": {"type": "string"},
                    "service": {"type": "string"},
                },
                "required": ["name", "phone", "service"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "send_sms",
            "description": "Send an SMS confirmation to the customer",
            "parameters": {
                "type": "object",
                "properties": {
                    "phone": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["phone", "message"],
            },
        },
    },
]


class ToolExecutor:
    """Executes tool calls made by the LLM agent."""

    def __init__(self, agent_config: dict | None = None) -> None:
        self._config = agent_config or {}

    async def execute(self, tool_name: str, arguments: dict[str, Any]) -> str:
        """Execute a named tool and return the result as a string."""
        log.info("Executing tool", tool=tool_name, args=arguments)

        handlers = {
            "book_appointment": self._book_appointment,
            "check_order_status": self._check_order_status,
            "transfer_to_human": self._transfer_to_human,
            "add_to_waitlist": self._add_to_waitlist,
            "send_sms": self._send_sms,
        }

        handler = handlers.get(tool_name)
        if handler is None:
            return f"Error: Unknown tool '{tool_name}'"

        try:
            return await handler(**arguments)
        except Exception as exc:
            log.error("Tool execution failed", tool=tool_name, error=str(exc))
            return f"Error executing {tool_name}: {exc}"

    async def execute_llm_response(
        self, llm_response: str
    ) -> tuple[str | None, str | None]:
        """Parse LLM response and execute tool if detected.

        Returns:
            (tool_result, tool_name) or (None, None) if not a tool call.
        """
        try:
            parsed = json.loads(llm_response)
            if "tool_calls" in parsed:
                for call in parsed["tool_calls"]:
                    result = await self.execute(call["name"], call["arguments"])
                    return result, call["name"]
        except (json.JSONDecodeError, KeyError):
            pass
        return None, None

    async def _book_appointment(
        self,
        date: str,
        time: str,
        name: str,
        phone: str,
        service: str = "General",
        **kwargs: Any,
    ) -> str:
        # In a real implementation, this would call a CRM / calendar API
        log.info("Booking appointment", date=date, time=time, name=name, phone=phone)
        return (
            f"Appointment booked successfully for {name} on {date} at {time} "
            f"for {service}. A confirmation will be sent to {phone}."
        )

    async def _check_order_status(self, order_id: str, **kwargs: Any) -> str:
        # Placeholder — would call e-commerce API in production
        return (
            f"Order #{order_id}: Your order is currently being processed and "
            "is expected to be delivered within 3-5 business days."
        )

    async def _transfer_to_human(self, reason: str = "", **kwargs: Any) -> str:
        return f"TRANSFER_TO_HUMAN:{reason}"

    async def _add_to_waitlist(
        self, name: str, phone: str, service: str, **kwargs: Any
    ) -> str:
        return (
            f"Added {name} to the waitlist for {service}. "
            f"We'll contact you at {phone} when a slot becomes available."
        )

    async def _send_sms(self, phone: str, message: str, **kwargs: Any) -> str:
        # Would use Telnyx/Twilio SMS in production
        log.info("SMS send requested", phone=phone, msg_len=len(message))
        return f"SMS sent to {phone} successfully."


def get_enabled_tools(tools_config: dict) -> list[dict]:
    """Filter TOOL_DEFINITIONS to only enabled tools."""
    enabled = {name for name, enabled in tools_config.items() if enabled}
    return [t for t in TOOL_DEFINITIONS if t["function"]["name"] in enabled]
