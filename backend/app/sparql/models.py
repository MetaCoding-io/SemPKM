"""SQLAlchemy ORM models for SPARQL query history, saved queries, sharing, and promoted views.

Tables: sparql_query_history (auto-saved on execution),
saved_sparql_queries (user-managed named queries),
shared_query_access (many-to-many sharing join table),
promoted_query_views (dashboard-pinned query views).
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SparqlQueryHistory(Base):
    """Auto-saved SPARQL query execution record, scoped per user."""

    __tablename__ = "sparql_query_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    query_text: Mapped[str] = mapped_column(Text(), nullable=False)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class SavedSparqlQuery(Base):
    """User-managed named SPARQL query with optional description."""

    __tablename__ = "saved_sparql_queries"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    query_text: Mapped[str] = mapped_column(Text(), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SharedQueryAccess(Base):
    """Join table for many-to-many query sharing between users."""

    __tablename__ = "shared_query_access"
    __table_args__ = (
        UniqueConstraint("query_id", "shared_with_user_id", name="uq_shared_query_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("saved_sparql_queries.id", ondelete="CASCADE"), index=True
    )
    shared_with_user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    shared_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_viewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PromotedQueryView(Base):
    """Dashboard-pinned query view for Plan 54-02."""

    __tablename__ = "promoted_query_views"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    query_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("saved_sparql_queries.id", ondelete="CASCADE"), unique=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    display_label: Mapped[str] = mapped_column(String(255), nullable=False)
    renderer_type: Mapped[str] = mapped_column(String(20), default="table")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
