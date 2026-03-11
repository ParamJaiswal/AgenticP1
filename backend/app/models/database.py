"""SQLAlchemy models for database tables."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Organization(Base):
    """Tenant / Company that uses the platform."""

    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="starter")
    monthly_minutes_limit: Mapped[int] = mapped_column(Integer, default=500)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    users: Mapped[list["User"]] = relationship("User", back_populates="organization")  # noqa: F821
    agents: Mapped[list["AgentConfig"]] = relationship(  # noqa: F821
        "AgentConfig", back_populates="organization"
    )
    calls: Mapped[list["Call"]] = relationship("Call", back_populates="organization")  # noqa: F821
    knowledge_docs: Mapped[list["KnowledgeDocument"]] = relationship(  # noqa: F821
        "KnowledgeDocument", back_populates="organization"
    )
