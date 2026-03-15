"""DashboardSpec SQLAlchemy model.

Stores dashboard definitions as JSON in SQLite. Each dashboard has a
layout template name and a list of block configurations.

Tech debt (v1): These are model-layer concepts that belong in RDF named
graphs. SQLite JSON is used for faster iteration. Migration to RDF is
planned for a follow-up milestone.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Valid layout template names
VALID_LAYOUTS = {"single", "sidebar-main", "grid-2x2", "grid-3", "top-bottom"}

# Valid block types
VALID_BLOCK_TYPES = {"view-embed", "markdown", "object-embed", "create-form", "sparql-result", "divider"}


class DashboardSpec(Base):
    """A user-defined dashboard composed of blocks in a grid layout.

    Attributes:
        id: UUID primary key.
        user_id: Owner (FK to users table).
        name: Display name for the dashboard.
        description: Optional description.
        layout: CSS Grid template name (e.g. 'grid-2x2', 'sidebar-main').
        blocks_json: JSON string containing block configurations.
            Each block: {"type": str, "slot": str, "config": dict}
            - view-embed: {"spec_iri": str, "height": str?}
            - markdown: {"content": str}
            - object-embed: {"object_iri": str, "mode": "read"|"edit"}
            - create-form: {"target_class": str, "defaults": dict?}
            - sparql-result: {"query": str, "label": str?}
            - divider: {}
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    __tablename__ = "dashboard_specs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text(), default="", server_default="")
    layout: Mapped[str] = mapped_column(String(50), default="single", server_default="single")
    blocks_json: Mapped[str] = mapped_column(Text(), default="[]", server_default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
