"""SQLAlchemy ORM models for lint filter persistence.

Three tables:
- lint_suppressions: user suppresses an entire rule type (by source IRI)
- lint_dismissals: user dismisses one specific lint result (object + rule pair)
- lint_presets: named collections of suppressed rules for quick switching
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class LintSuppression(Base):
    """A user's globally suppressed lint rule, identified by source IRI."""

    __tablename__ = "lint_suppressions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    rule_source_iri: Mapped[str] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "rule_source_iri", name="uq_lint_suppression"),
    )


class LintDismissal(Base):
    """A user's dismissed individual lint result (object + rule pair)."""

    __tablename__ = "lint_dismissals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    object_iri: Mapped[str] = mapped_column(String(2048))
    rule_source_iri: Mapped[str] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        UniqueConstraint(
            "user_id", "object_iri", "rule_source_iri", name="uq_lint_dismissal"
        ),
    )


class LintPreset(Base):
    """A named collection of suppressed rule IRIs for quick switching."""

    __tablename__ = "lint_presets"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    suppressed_rules_json: Mapped[str] = mapped_column(Text(), default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        UniqueConstraint("user_id", "name", name="uq_lint_preset"),
    )
