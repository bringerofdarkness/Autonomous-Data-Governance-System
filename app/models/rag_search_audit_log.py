import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RagSearchAuditLog(Base):
    __tablename__ = "rag_search_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    query: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    result_limit: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    min_score: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    matches_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    matched_document_ids: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    matched_point_ids: Mapped[list[str]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
    )

    extra_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    actor = relationship("User")
