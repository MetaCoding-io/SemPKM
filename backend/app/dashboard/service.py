"""DashboardService — CRUD operations for DashboardSpec.

Provides async methods for creating, reading, updating, and deleting
dashboard definitions stored in SQLite.
"""

import json
import logging
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.dashboard.models import DashboardSpec, VALID_LAYOUTS, VALID_BLOCK_TYPES

logger = logging.getLogger(__name__)


@dataclass
class DashboardData:
    """Lightweight read model for a dashboard."""

    id: str
    user_id: str
    name: str
    description: str
    layout: str
    blocks: list[dict] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class DashboardService:
    """Service for dashboard CRUD operations."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        layout: str = "single",
        blocks: list[dict] | None = None,
        description: str = "",
    ) -> DashboardData:
        """Create a new dashboard.

        Args:
            user_id: Owner's UUID.
            name: Display name.
            layout: Grid layout template name.
            blocks: List of block configurations.
            description: Optional description.

        Returns:
            Created dashboard data.

        Raises:
            ValueError: If layout or block types are invalid.
        """
        if layout not in VALID_LAYOUTS:
            raise ValueError(f"Invalid layout: {layout}. Must be one of {VALID_LAYOUTS}")

        blocks = blocks or []
        for block in blocks:
            if block.get("type") not in VALID_BLOCK_TYPES:
                raise ValueError(f"Invalid block type: {block.get('type')}. Must be one of {VALID_BLOCK_TYPES}")

        dashboard_id = uuid.uuid4()
        spec = DashboardSpec(
            id=dashboard_id,
            user_id=user_id,
            name=name,
            description=description,
            layout=layout,
            blocks_json=json.dumps(blocks),
        )

        async with self._session_factory() as session:
            session.add(spec)
            await session.commit()
            await session.refresh(spec)
            return self._to_data(spec)

    async def get(self, dashboard_id: uuid.UUID) -> DashboardData | None:
        """Get a dashboard by ID. Returns None if not found."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(DashboardSpec).where(DashboardSpec.id == dashboard_id)
            )
            spec = result.scalar_one_or_none()
            return self._to_data(spec) if spec else None

    async def list_for_user(self, user_id: uuid.UUID) -> list[DashboardData]:
        """List all dashboards owned by a user."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(DashboardSpec)
                .where(DashboardSpec.user_id == user_id)
                .order_by(DashboardSpec.name)
            )
            specs = result.scalars().all()
            return [self._to_data(s) for s in specs]

    async def update(
        self,
        dashboard_id: uuid.UUID,
        user_id: uuid.UUID,
        **updates,
    ) -> DashboardData | None:
        """Update a dashboard. Only updates provided fields.

        Args:
            dashboard_id: Dashboard UUID.
            user_id: Must match owner for authorization.
            **updates: Fields to update (name, description, layout, blocks).

        Returns:
            Updated dashboard data, or None if not found/unauthorized.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(DashboardSpec).where(
                    DashboardSpec.id == dashboard_id,
                    DashboardSpec.user_id == user_id,
                )
            )
            spec = result.scalar_one_or_none()
            if not spec:
                return None

            if "name" in updates:
                spec.name = updates["name"]
            if "description" in updates:
                spec.description = updates["description"]
            if "layout" in updates:
                if updates["layout"] not in VALID_LAYOUTS:
                    raise ValueError(f"Invalid layout: {updates['layout']}")
                spec.layout = updates["layout"]
            if "blocks" in updates:
                blocks = updates["blocks"]
                for block in blocks:
                    if block.get("type") not in VALID_BLOCK_TYPES:
                        raise ValueError(f"Invalid block type: {block.get('type')}")
                spec.blocks_json = json.dumps(blocks)

            await session.commit()
            await session.refresh(spec)
            return self._to_data(spec)

    async def delete(self, dashboard_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a dashboard. Returns True if deleted, False if not found."""
        async with self._session_factory() as session:
            result = await session.execute(
                delete(DashboardSpec).where(
                    DashboardSpec.id == dashboard_id,
                    DashboardSpec.user_id == user_id,
                )
            )
            await session.commit()
            return result.rowcount > 0

    @staticmethod
    def _to_data(spec: DashboardSpec) -> DashboardData:
        """Convert a DashboardSpec ORM instance to a DashboardData read model."""
        try:
            blocks = json.loads(spec.blocks_json) if spec.blocks_json else []
        except (json.JSONDecodeError, TypeError):
            blocks = []

        return DashboardData(
            id=str(spec.id),
            user_id=str(spec.user_id),
            name=spec.name,
            description=spec.description or "",
            layout=spec.layout,
            blocks=blocks,
            created_at=spec.created_at.isoformat() if spec.created_at else "",
            updated_at=spec.updated_at.isoformat() if spec.updated_at else "",
        )
