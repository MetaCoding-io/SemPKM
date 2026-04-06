"""ExplorerConfigSpec SQLAlchemy model.

Stores named explorer panel configurations as JSON in SQLite. Each config
specifies group_by, sort_by, sort_order, type_filter, and any other
explorer panel settings. Presets (is_preset=True, user_id=NULL) are
system-level configs visible to all users.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExplorerConfigSpec(Base):
    """A named explorer panel configuration.

    Attributes:
        id: UUID primary key.
        user_id: Owner (FK to users table). NULL for system presets.
        name: Display name for the config.
        config_json: JSON string containing explorer settings.
            Example: {"group_by": "type", "sort_by": "label",
                      "sort_order": "asc", "type_filter": null}
        is_preset: True for built-in presets, False for user configs.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    __tablename__ = "explorer_configs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    config_json: Mapped[str] = mapped_column(Text(), default="{}", server_default="{}")
    is_preset: Mapped[bool] = mapped_column(Boolean(), default=False, server_default="0")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
