"""Calls API routes."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth_middleware import get_current_user
from app.db.database import get_db
from app.models.call import Call
from app.models.conversation import ConversationTurn
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from app.services.telephony_service import get_telephony_service

router = APIRouter()


class InitiateCallRequest(BaseModel):
    to_number: str
    agent_id: str


@router.get("/")
async def list_calls(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(20, le=100),
    offset: int = Query(0, ge=0),
    status: str | None = Query(None),
    sentiment: str | None = Query(None),
) -> dict:
    """List calls for the current organization."""
    svc = AnalyticsService(db)

    query = select(Call).where(Call.organization_id == current_user.organization_id)
    if status:
        query = query.where(Call.status == status)
    if sentiment:
        query = query.where(Call.sentiment_label == sentiment)

    query = query.order_by(Call.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    calls = result.scalars().all()

    # Total count
    from sqlalchemy import func

    count_q = await db.execute(
        select(func.count(Call.id)).where(
            Call.organization_id == current_user.organization_id
        )
    )
    total = count_q.scalar() or 0

    return {
        "data": [svc._call_to_dict(c) for c in calls],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/{call_id}")
async def get_call(
    call_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get a single call with transcript."""
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()

    if not call or call.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Call not found")

    # Load transcript
    turns_result = await db.execute(
        select(ConversationTurn)
        .where(ConversationTurn.call_id == call_id)
        .order_by(ConversationTurn.created_at)
    )
    turns = turns_result.scalars().all()

    svc = AnalyticsService(db)
    call_dict = svc._call_to_dict(call)
    call_dict["transcript_turns"] = [
        {"role": t.role, "content": t.content, "timestamp": t.created_at.isoformat()}
        for t in turns
    ]
    return call_dict


@router.post("/initiate", status_code=201)
async def initiate_call(
    body: InitiateCallRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Initiate an outbound call."""
    from app.services.billing_service import BillingService

    billing = BillingService(db)
    can_call, reason = await billing.check_can_make_call(current_user.organization_id)
    if not can_call:
        raise HTTPException(status_code=402, detail=reason)

    telephony = get_telephony_service()
    result = await telephony.initiate_outbound_call(to_number=body.to_number)

    # Create call record
    call = Call(
        organization_id=current_user.organization_id,
        agent_id=body.agent_id,
        direction="outbound",
        called_number=body.to_number,
        status="initiated",
        external_call_id=result.get("call_control_id") or result.get("call_id"),
    )
    db.add(call)
    await db.flush()

    return {
        "call_id": call.id,
        "external_id": call.external_call_id,
        "status": "initiated",
    }


@router.delete("/{call_id}")
async def delete_call(
    call_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Delete a call record."""
    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()

    if not call or call.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Call not found")

    await db.delete(call)
    return {"message": "Call deleted"}
