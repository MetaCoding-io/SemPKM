"""Persona SQLAlchemy model.

Stores workspace persona definitions in SQLite. Each persona captures
a named workspace configuration: dockview layout, sidebar panel positions,
and explorer mode. Only one persona per user can be active at a time.
"""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Persona(Base):
    """A named workspace configuration (layout, sidebar positions, explorer mode).

    Attributes:
        id: UUID primary key.
        user_id: Owner (FK to users table).
        name: Display name for the persona (e.g. "Research", "Writing").
        layout_json: Dockview serialized layout JSON string.
        sidebar_positions_json: Sidebar panel positions JSON string.
        explorer_mode: Explorer panel grouping mode (e.g. "by-type", "by-namespace").
        is_active: Whether this persona is the user's currently active one.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    __tablename__ = "personas"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    layout_json: Mapped[str] = mapped_column(Text(), default="{}", server_default="{}")
    sidebar_positions_json: Mapped[str] = mapped_column(
        Text(), default="{}", server_default="{}"
    )
    explorer_mode: Mapped[str] = mapped_column(
        String(50), default="by-type", server_default="by-type"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean(), default=False, server_default=sa.false()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
