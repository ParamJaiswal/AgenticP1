"""Knowledge document model."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class KnowledgeDocument(Base):
    """A document uploaded to the knowledge base."""

    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    doc_type: Mapped[str] = mapped_column(String(20), default="file")  # file | url
    status: Mapped[str] = mapped_column(String(20), default="processing")  # processing | ready | error
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), onupdate=func.now()
    )

    organization: Mapped["Organization"] = relationship(  # type: ignore[name-defined]  # noqa: F821
        "Organization", back_populates="knowledge_docs"
    )
