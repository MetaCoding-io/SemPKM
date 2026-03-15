"""WorkflowSpec SQLAlchemy model.

Stores workflow definitions as JSON in SQLite. Each workflow has an
ordered list of steps, each specifying a type (view, dashboard, form)
and its configuration.

Tech debt (v1): These are model-layer concepts that belong in RDF.
SQLite JSON is used for faster iteration. Migration to RDF planned.

Additional tech debt: v1 workflow runs are ephemeral (in-memory).
Users want: history of completed runs, resume interrupted workflows,
track frequency. Persisted run records planned for follow-up.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


# Valid step types
VALID_STEP_TYPES = {"view", "dashboard", "form"}


class WorkflowSpec(Base):
    """A user-defined workflow with ordered steps.

    Attributes:
        id: UUID primary key.
        user_id: Owner (FK to users table).
        name: Display name for the workflow.
        description: Optional description.
        steps_json: JSON string containing step configurations.
            Each step: {"type": str, "label": str, "config": dict}
            - view: {"spec_iri": str, "renderer_type": str?}
            - dashboard: {"dashboard_id": str}
            - form: {"target_class": str, "defaults": dict?}
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    __tablename__ = "workflow_specs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text(), default="", server_default="")
    steps_json: Mapped[str] = mapped_column(Text(), default="[]", server_default="[]")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
