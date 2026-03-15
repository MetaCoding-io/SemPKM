"""WorkflowService — CRUD operations for WorkflowSpec.

Mirrors DashboardService pattern for consistency.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.workflow.models import WorkflowSpec, VALID_STEP_TYPES

logger = logging.getLogger(__name__)


@dataclass
class WorkflowData:
    """Lightweight read model for a workflow."""

    id: str
    user_id: str
    name: str
    description: str
    steps: list[dict] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class WorkflowService:
    """Service for workflow CRUD operations."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        steps: list[dict] | None = None,
        description: str = "",
    ) -> WorkflowData:
        """Create a new workflow.

        Args:
            user_id: Owner's UUID.
            name: Display name.
            steps: List of step configurations.
            description: Optional description.

        Returns:
            Created workflow data.

        Raises:
            ValueError: If step types are invalid.
        """
        steps = steps or []
        for step in steps:
            if step.get("type") not in VALID_STEP_TYPES:
                raise ValueError(f"Invalid step type: {step.get('type')}. Must be one of {VALID_STEP_TYPES}")

        workflow_id = uuid.uuid4()
        spec = WorkflowSpec(
            id=workflow_id,
            user_id=user_id,
            name=name,
            description=description,
            steps_json=json.dumps(steps),
        )

        async with self._session_factory() as session:
            session.add(spec)
            await session.commit()
            await session.refresh(spec)
            return self._to_data(spec)

    async def get(self, workflow_id: uuid.UUID) -> WorkflowData | None:
        """Get a workflow by ID."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(WorkflowSpec).where(WorkflowSpec.id == workflow_id)
            )
            spec = result.scalar_one_or_none()
            return self._to_data(spec) if spec else None

    async def list_for_user(self, user_id: uuid.UUID) -> list[WorkflowData]:
        """List all workflows owned by a user."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(WorkflowSpec)
                .where(WorkflowSpec.user_id == user_id)
                .order_by(WorkflowSpec.name)
            )
            specs = result.scalars().all()
            return [self._to_data(s) for s in specs]

    async def update(
        self,
        workflow_id: uuid.UUID,
        user_id: uuid.UUID,
        **updates,
    ) -> WorkflowData | None:
        """Update a workflow. Only updates provided fields."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(WorkflowSpec).where(
                    WorkflowSpec.id == workflow_id,
                    WorkflowSpec.user_id == user_id,
                )
            )
            spec = result.scalar_one_or_none()
            if not spec:
                return None

            if "name" in updates:
                spec.name = updates["name"]
            if "description" in updates:
                spec.description = updates["description"]
            if "steps" in updates:
                steps = updates["steps"]
                for step in steps:
                    if step.get("type") not in VALID_STEP_TYPES:
                        raise ValueError(f"Invalid step type: {step.get('type')}")
                spec.steps_json = json.dumps(steps)

            await session.commit()
            await session.refresh(spec)
            return self._to_data(spec)

    async def delete(self, workflow_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a workflow. Returns True if deleted."""
        async with self._session_factory() as session:
            result = await session.execute(
                delete(WorkflowSpec).where(
                    WorkflowSpec.id == workflow_id,
                    WorkflowSpec.user_id == user_id,
                )
            )
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    def _to_data(spec: WorkflowSpec) -> WorkflowData:
        """Convert ORM instance to read model."""
        try:
            steps = json.loads(spec.steps_json) if spec.steps_json else []
        except (json.JSONDecodeError, TypeError):
            steps = []

        return WorkflowData(
            id=str(spec.id),
            user_id=str(spec.user_id),
            name=spec.name,
            description=spec.description or "",
            steps=steps,
            created_at=spec.created_at.isoformat() if spec.created_at else "",
            updated_at=spec.updated_at.isoformat() if spec.updated_at else "",
        )
