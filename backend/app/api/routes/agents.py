"""Agent configuration CRUD routes."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.middleware.auth_middleware import get_current_user
from app.db.database import get_db
from app.models.agent_config import AgentConfig
from app.models.user import User

router = APIRouter()


class AgentCreateRequest(BaseModel):
    name: str
    description: str = ""
    industry: str = "general"
    personality: str = "professional"
    custom_prompt: str | None = None
    greeting_message: str = "Hello! Thank you for calling. How can I help you today?"
    language: str = "en"
    voice_id: str = "en_US-amy-low"
    tools_enabled: dict[str, bool] | None = None
    escalation_rules: dict[str, Any] | None = None
    business_hours: dict[str, Any] | None = None
    faqs: list[dict[str, str]] | None = None
    phone_number: str | None = None


class AgentUpdateRequest(AgentCreateRequest):
    name: str | None = None


def _agent_to_dict(agent: AgentConfig) -> dict:
    return {
        "id": agent.id,
        "organization_id": agent.organization_id,
        "name": agent.name,
        "description": agent.description,
        "industry": agent.industry,
        "personality": agent.personality,
        "custom_prompt": agent.custom_prompt,
        "greeting_message": agent.greeting_message,
        "language": agent.language,
        "voice_id": agent.voice_id,
        "tools_enabled": agent.tools_enabled,
        "escalation_rules": agent.escalation_rules,
        "business_hours": agent.business_hours,
        "faqs": agent.faqs,
        "phone_number": agent.phone_number,
        "is_active": agent.is_active,
        "created_at": agent.created_at.isoformat() if agent.created_at else None,
        "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
    }


@router.get("/")
async def list_agents(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """List all agents for the current organization."""
    result = await db.execute(
        select(AgentConfig)
        .where(AgentConfig.organization_id == current_user.organization_id)
        .order_by(AgentConfig.created_at.desc())
    )
    agents = result.scalars().all()
    return {"data": [_agent_to_dict(a) for a in agents]}


@router.post("/", status_code=201)
async def create_agent(
    body: AgentCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Create a new agent configuration."""
    agent = AgentConfig(
        organization_id=current_user.organization_id,
        name=body.name,
        description=body.description,
        industry=body.industry,
        personality=body.personality,
        custom_prompt=body.custom_prompt,
        greeting_message=body.greeting_message,
        language=body.language,
        voice_id=body.voice_id,
        tools_enabled=body.tools_enabled or {
            "book_appointment": False,
            "check_order_status": False,
            "transfer_to_human": True,
            "send_sms": False,
            "add_to_waitlist": False,
        },
        escalation_rules=body.escalation_rules,
        business_hours=body.business_hours,
        faqs=body.faqs,
        phone_number=body.phone_number,
    )
    db.add(agent)
    await db.flush()
    return _agent_to_dict(agent)


@router.get("/{agent_id}")
async def get_agent(
    agent_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Get a single agent by ID."""
    result = await db.execute(select(AgentConfig).where(AgentConfig.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent or agent.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Agent not found")

    return _agent_to_dict(agent)


@router.patch("/{agent_id}")
async def update_agent(
    agent_id: str,
    body: AgentUpdateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Update an agent configuration."""
    result = await db.execute(select(AgentConfig).where(AgentConfig.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent or agent.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = body.model_dump(exclude_unset=True, exclude_none=False)
    for field, value in update_data.items():
        if value is not None or field in ("custom_prompt", "phone_number"):
            setattr(agent, field, value)

    db.add(agent)
    await db.flush()
    return _agent_to_dict(agent)


@router.delete("/{agent_id}")
async def delete_agent(
    agent_id: str,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """Delete an agent."""
    result = await db.execute(select(AgentConfig).where(AgentConfig.id == agent_id))
    agent = result.scalar_one_or_none()

    if not agent or agent.organization_id != current_user.organization_id:
        raise HTTPException(status_code=404, detail="Agent not found")

    await db.delete(agent)
    return {"message": "Agent deleted"}
