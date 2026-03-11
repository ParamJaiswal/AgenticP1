"""Call model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class Call(Base):
    """Represents a single phone call."""

    __tablename__ = "calls"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    agent_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("agent_configs.id", ondelete="SET NULL"), nullable=True
    )

    # Call metadata
    external_call_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )  # Telnyx/Twilio ID
    direction: Mapped[str] = mapped_column(
        String(10), default="inbound"
    )  # inbound | outbound
    caller_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    called_number: Mapped[str | None] = mapped_column(String(20), nullable=True)

    # Status tracking
    status: Mapped[str] = mapped_column(
        String(50), default="initiated"
    )  # initiated|active|completed|failed|transferred

    # Timing
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # AI analysis
    transcript: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    sentiment_score: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # -1.0 to 1.0
    sentiment_label: Mapped[str | None] = mapped_column(
        String(20), nullable=True
    )  # positive|neutral|negative
    resolution: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # resolved|escalated|abandoned

    # Recording
    recording_path: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Cost tracking
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Organization", back_populates="calls"
    )
    agent: Mapped["AgentConfig | None"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "AgentConfig", back_populates="calls"
    )
    conversation_turns: Mapped[list["ConversationTurn"]] = relationship(  # noqa: F821
        "ConversationTurn", back_populates="call", cascade="all, delete-orphan"
    )
