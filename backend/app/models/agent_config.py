"""Agent configuration model."""

import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class AgentConfig(Base):
    """AI Agent configuration per tenant."""

    __tablename__ = "agent_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    industry: Mapped[str] = mapped_column(String(100), default="general")

    # Personality & voice
    personality: Mapped[str] = mapped_column(String(50), default="professional")
    custom_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    greeting_message: Mapped[str] = mapped_column(
        Text,
        default="Hello! Thank you for calling. How can I help you today?",
    )
    language: Mapped[str] = mapped_column(String(10), default="en")
    voice_id: Mapped[str] = mapped_column(String(100), default="en_US-amy-low")

    # Tools enabled for this agent
    tools_enabled: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "book_appointment": False,
            "check_order_status": False,
            "transfer_to_human": True,
            "send_sms": False,
            "add_to_waitlist": False,
        },
    )

    # Escalation rules
    escalation_rules: Mapped[dict] = mapped_column(
        JSON,
        default=lambda: {
            "sentiment_threshold": -0.5,
            "max_turns_before_escalation": 10,
            "keywords": ["human", "agent", "manager", "supervisor"],
        },
    )

    # Business hours (JSON: {"monday": {"open": "09:00", "close": "17:00"}, ...})
    business_hours: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # FAQ (list of {question, answer} dicts)
    faqs: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Phone number assigned to this agent
    phone_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Organization", back_populates="agents"
    )
    calls: Mapped[list["Call"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Call", back_populates="agent"
    )
