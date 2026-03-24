"""DeviceToken and NotificationPreferences SQLAlchemy models.

DeviceToken stores FCM device tokens per user (multiple devices allowed).
NotificationPreferences stores per-user notification settings (one row per user).
"""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class DeviceToken(Base):
    """FCM device token — one row per device.

    Attributes:
        id: UUID primary key.
        user_id: Owner (FK to users, indexed).
        token: FCM registration token (unique across all users).
        platform: "ios" or "android".
        device_name: Human-readable device label (optional).
        created_at: Row creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "device_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    token: Mapped[str] = mapped_column(String(500), unique=True, nullable=False)
    platform: Mapped[str] = mapped_column(String(10), nullable=False)
    device_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class NotificationPreferences(Base):
    """Per-user notification preferences — one row per user.

    Attributes:
        id: UUID primary key.
        user_id: Owner (FK to users, unique — one row per user).
        enabled: Master enable/disable toggle.
        quiet_hours_start: Start of quiet window, format "HH:MM" (nullable).
        quiet_hours_end: End of quiet window, format "HH:MM" (nullable).
        suppress_when_busy: Suppress notifications when calendar_busy is True.
        enabled_types: JSON array as string listing enabled notification types
                       (e.g. '["overdue_tasks","validation_warnings"]'). Nullable
                       means all types are enabled.
    """

    __tablename__ = "notification_preferences"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        unique=True,
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean(), default=True, server_default=sa.true()
    )
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5), nullable=True)
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5), nullable=True)
    suppress_when_busy: Mapped[bool] = mapped_column(
        Boolean(), default=True, server_default=sa.true()
    )
    enabled_types: Mapped[str | None] = mapped_column(String(500), nullable=True)
