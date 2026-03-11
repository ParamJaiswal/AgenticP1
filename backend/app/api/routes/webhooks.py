"""Webhook handlers for Telnyx and Twilio call events.

Handles:
- call.initiated → create call record
- call.answered → start AI processing
- call.hangup → finalize call record
- WebSocket audio stream
"""

from __future__ import annotations

from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.call_handler import CallHandler
from app.db.database import get_db
from app.models.agent_config import AgentConfig
from app.models.call import Call

log = structlog.get_logger()
router = APIRouter()


async def _get_agent_for_number(
    phone_number: str, db: AsyncSession
) -> AgentConfig | None:
    """Find the agent assigned to a phone number."""
    result = await db.execute(
        select(AgentConfig).where(
            AgentConfig.phone_number == phone_number,
            AgentConfig.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


@router.post("/telnyx")
async def telnyx_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Handle Telnyx call events."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("data", {}).get("event_type", "")
    event_data = payload.get("data", {}).get("payload", {})

    log.info("Telnyx webhook received", event_type=event_type)

    if event_type == "call.initiated":
        await _handle_call_initiated(event_data, db)
    elif event_type == "call.answered":
        await _handle_call_answered(event_data, db)
    elif event_type == "call.hangup":
        await _handle_call_hangup(event_data, db)

    return {"status": "ok"}


@router.post("/twilio")
async def twilio_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> str:
    """Handle Twilio call webhooks. Returns TwiML."""
    form = await request.form()
    call_sid = form.get("CallSid", "")
    caller = form.get("From", "")
    called = form.get("To", "")
    call_status = form.get("CallStatus", "")

    log.info("Twilio webhook", call_sid=call_sid, status=call_status)

    if call_status == "ringing":
        # Find agent and create call record
        agent = await _get_agent_for_number(called, db)
        if agent:
            call = Call(
                organization_id=agent.organization_id,
                agent_id=agent.id,
                direction="inbound",
                caller_number=caller,
                called_number=called,
                status="active",
                external_call_id=call_sid,
            )
            db.add(call)
            await db.flush()

    # Return TwiML to keep the call alive
    greeting = "Hello! Please wait while I connect you to our AI assistant."
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say>{greeting}</Say>
    <Pause length="60"/>
</Response>"""


async def _handle_call_initiated(data: dict, db: AsyncSession) -> None:
    """Create call record when a call is initiated."""
    call_control_id = data.get("call_control_id", "")
    direction = data.get("direction", "inbound")
    from_num = data.get("from", "")
    to_num = data.get("to", "")

    agent = await _get_agent_for_number(
        to_num if direction == "inbound" else from_num, db
    )

    call = Call(
        organization_id=agent.organization_id if agent else "unknown",
        agent_id=agent.id if agent else None,
        direction=direction,
        caller_number=from_num,
        called_number=to_num,
        status="initiated",
        external_call_id=call_control_id,
    )
    db.add(call)
    await db.flush()


async def _handle_call_answered(data: dict, db: AsyncSession) -> None:
    """Update call status when answered."""
    from datetime import datetime
    from sqlalchemy import update

    call_control_id = data.get("call_control_id", "")
    await db.execute(
        update(Call)
        .where(Call.external_call_id == call_control_id)
        .values(status="active", started_at=datetime.utcnow())
    )


async def _handle_call_hangup(data: dict, db: AsyncSession) -> None:
    """Finalize call on hangup."""
    from sqlalchemy import select

    call_control_id = data.get("call_control_id", "")
    result = await db.execute(
        select(Call).where(Call.external_call_id == call_control_id)
    )
    call = result.scalar_one_or_none()

    if call:
        handler = CallHandler(db)
        await handler.end_call(call.id, resolution="completed")


@router.websocket("/stream/{call_id}")
async def audio_stream(
    websocket: WebSocket,
    call_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """WebSocket endpoint for real-time audio streaming during a call."""
    await websocket.accept()
    log.info("Audio stream connected", call_id=call_id)

    # Load call + agent config
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()
    if not call:
        await websocket.close(code=4004, reason="Call not found")
        return

    agent_result = await db.execute(
        select(AgentConfig).where(AgentConfig.id == call.agent_id)
    )
    agent = agent_result.scalar_one_or_none()
    agent_config = _agent_to_dict(agent) if agent else {}

    handler = CallHandler(db)

    # Send greeting on connect
    try:
        greeting_text, greeting_audio = await handler.handle_inbound_call(
            call_id=call_id,
            caller_number=call.caller_number or "",
            called_number=call.called_number or "",
            agent_config=agent_config,
            organization_id=call.organization_id,
        )
        await websocket.send_bytes(greeting_audio)
    except Exception as exc:
        log.error("Error sending greeting", error=str(exc))
        await websocket.close()
        return

    # Main audio loop
    try:
        while True:
            message = await websocket.receive()
            if message["type"] == "websocket.disconnect":
                break

            if "bytes" in message and message["bytes"]:
                audio_data = message["bytes"]
                try:
                    text, response_audio, should_transfer = await handler.process_audio_chunk(
                        call_id=call_id,
                        audio_data=audio_data,
                        agent_config=agent_config,
                    )
                    if response_audio:
                        await websocket.send_bytes(response_audio)

                    if should_transfer:
                        await websocket.send_json({"event": "transfer"})
                        break
                except Exception as exc:
                    log.error("Audio processing error", call_id=call_id, error=str(exc))

    except WebSocketDisconnect:
        log.info("Audio stream disconnected", call_id=call_id)
    finally:
        await handler.end_call(call_id)
        log.info("Audio stream ended", call_id=call_id)


def _agent_to_dict(agent: AgentConfig | None) -> dict:
    if not agent:
        return {}
    return {
        "id": agent.id,
        "name": agent.name,
        "personality": agent.personality,
        "custom_prompt": agent.custom_prompt,
        "greeting_message": agent.greeting_message,
        "tools_enabled": agent.tools_enabled,
        "escalation_rules": agent.escalation_rules,
        "business_hours": agent.business_hours,
        "faqs": agent.faqs,
        "voice_id": agent.voice_id,
        "language": agent.language,
        "industry": agent.industry,
    }
