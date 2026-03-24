"""ContextRule SQLAlchemy model.

Stores per-user rules for automatic persona switching based on context
conditions. Each rule maps a set of AND-matched context field values
to a target persona_id. Rules are evaluated in priority order (desc);
the first match wins.
"""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ContextRule(Base):
    """A context-to-persona mapping rule.

    Attributes:
        id: UUID primary key.
        user_id: Owner (FK to users).
        name: Human label for the rule (e.g. "Office Work → Focus persona").
        priority: Evaluation order — higher runs first. Ties broken by created_at ASC.
        conditions: JSON dict of context field→value pairs. All must match (AND).
        persona_id: Target persona UUID (stored as string).
        enabled: Whether the rule participates in evaluation.
        created_at: Row creation timestamp.
        updated_at: Last modification timestamp.
    """

    __tablename__ = "context_rules"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=0, server_default=sa.text("0"))
    conditions: Mapped[dict] = mapped_column(sa.JSON, nullable=False, default=dict)
    persona_id: Mapped[str] = mapped_column(String(36), nullable=False)
    enabled: Mapped[bool] = mapped_column(
        Boolean(), default=True, server_default=sa.true()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
