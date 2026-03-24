"""UserContext SQLAlchemy model.

Stores the latest context snapshot per user: location zone, activity,
time period, calendar state, and device. One row per user (upsert pattern).
"""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserContext(Base):
    """Per-user context snapshot.

    Attributes:
        id: UUID primary key.
        user_id: Owner (FK to users, unique — one row per user).
        location_zone: Coarse location label (e.g. "office", "home", "transit").
        activity: Activity state (e.g. "stationary", "walking", "driving").
        time_period: Time-of-day bucket (e.g. "work_hours", "evening", "night").
        calendar_event: Current/next calendar event summary text.
        calendar_busy: Whether the user is in a busy calendar slot.
        device_id: Opaque device identifier (no PII).
        updated_at: Last context update timestamp.
        created_at: Row creation timestamp.
    """

    __tablename__ = "user_context"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        unique=True,
    )
    location_zone: Mapped[str | None] = mapped_column(String(100), nullable=True)
    activity: Mapped[str | None] = mapped_column(String(50), nullable=True)
    time_period: Mapped[str | None] = mapped_column(String(50), nullable=True)
    calendar_event: Mapped[str | None] = mapped_column(String(500), nullable=True)
    calendar_busy: Mapped[bool] = mapped_column(
        Boolean(), default=False, server_default=sa.false()
    )
    device_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
