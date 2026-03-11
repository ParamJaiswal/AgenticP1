"""Telephony Service — Telnyx (primary) + Twilio (fallback).

Telnyx is the cheapest SIP provider at ~$0.005/min inbound.
"""

from __future__ import annotations

from typing import Any

import structlog

from config import settings

log = structlog.get_logger()


class TelephonyService:
    """Unified telephony interface for call management."""

    def __init__(self) -> None:
        self._provider = settings.TELEPHONY_PROVIDER
        self._telnyx_client: Any | None = None
        self._twilio_client: Any | None = None

    async def initiate_outbound_call(
        self,
        to_number: str,
        from_number: str | None = None,
        webhook_url: str | None = None,
    ) -> dict[str, Any]:
        """Initiate an outbound call."""
        from_num = (
            from_number or settings.TELNYX_PHONE_NUMBER or settings.TWILIO_PHONE_NUMBER
        )
        if not from_num:
            raise ValueError("No from phone number configured")

        if self._provider == "telnyx":
            return await self._telnyx_call(to_number, from_num, webhook_url)
        elif self._provider == "twilio":
            return await self._twilio_call(to_number, from_num, webhook_url)
        else:
            raise ValueError(f"Unknown telephony provider: {self._provider}")

    async def _telnyx_call(
        self, to: str, from_: str, webhook_url: str | None
    ) -> dict[str, Any]:
        """Make a call via Telnyx API."""
        if not settings.TELNYX_API_KEY:
            raise RuntimeError("TELNYX_API_KEY not configured")

        import aiohttp

        headers = {
            "Authorization": f"Bearer {settings.TELNYX_API_KEY.get_secret_value()}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "connection_id": settings.TELNYX_CONNECTION_ID,
            "to": to,
            "from": from_,
        }
        if webhook_url:
            payload["webhook_url"] = webhook_url

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.telnyx.com/v2/calls",
                json=payload,
                headers=headers,
            ) as resp:
                data = await resp.json()
                if resp.status not in (200, 201):
                    raise RuntimeError(f"Telnyx error {resp.status}: {data}")
                return data.get("data", data)

    async def _twilio_call(
        self, to: str, from_: str, webhook_url: str | None
    ) -> dict[str, Any]:
        """Make a call via Twilio (fallback)."""
        if not settings.TWILIO_ACCOUNT_SID or not settings.TWILIO_AUTH_TOKEN:
            raise RuntimeError("Twilio credentials not configured")

        import asyncio

        from twilio.rest import Client

        client = Client(
            settings.TWILIO_ACCOUNT_SID.get_secret_value(),
            settings.TWILIO_AUTH_TOKEN.get_secret_value(),
        )

        loop = asyncio.get_event_loop()
        call = await loop.run_in_executor(
            None,
            lambda: client.calls.create(
                to=to,
                from_=from_,
                url=webhook_url or "http://demo.twilio.com/docs/voice.xml",
            ),
        )
        return {"call_id": call.sid, "status": call.status}

    async def send_sms(self, to: str, message: str, from_: str | None = None) -> dict:
        """Send an SMS via Telnyx."""
        if not settings.TELNYX_API_KEY:
            raise RuntimeError("TELNYX_API_KEY not configured")

        import aiohttp

        from_num = from_ or settings.TELNYX_PHONE_NUMBER
        headers = {
            "Authorization": f"Bearer {settings.TELNYX_API_KEY.get_secret_value()}",
            "Content-Type": "application/json",
        }
        payload = {"from": from_num, "to": to, "text": message}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api.telnyx.com/v2/messages",
                json=payload,
                headers=headers,
            ) as resp:
                data = await resp.json()
                if resp.status not in (200, 201):
                    raise RuntimeError(f"Telnyx SMS error {resp.status}: {data}")
                return data.get("data", data)

    async def list_phone_numbers(self) -> list[dict]:
        """List phone numbers for the account."""
        if not settings.TELNYX_API_KEY:
            return []

        import aiohttp

        headers = {
            "Authorization": f"Bearer {settings.TELNYX_API_KEY.get_secret_value()}",
        }
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://api.telnyx.com/v2/phone_numbers",
                headers=headers,
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json()
                return data.get("data", [])


_telephony_service: TelephonyService | None = None


def get_telephony_service() -> TelephonyService:
    global _telephony_service
    if _telephony_service is None:
        _telephony_service = TelephonyService()
    return _telephony_service
