"""ExplorerConfigService — CRUD operations for ExplorerConfigSpec.

Provides async methods for creating, reading, updating, and deleting
explorer panel configurations stored in SQLite. Handles built-in preset
seeding (By Type, By Tag).
"""

import json
import logging
import uuid
from dataclasses import dataclass, field

from sqlalchemy import select, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.browser.explorer_models import ExplorerConfigSpec

logger = logging.getLogger(__name__)


# Built-in preset definitions
PRESETS = [
    {
        "name": "By Type",
        "config": {"group_by": "type", "sort_by": "label", "sort_order": "asc"},
    },
    {
        "name": "By Tag",
        "config": {"group_by": "tag", "sort_by": "label", "sort_order": "asc"},
    },
]


@dataclass
class ExplorerConfigData:
    """Lightweight read model for an explorer configuration."""

    id: str
    user_id: str | None
    name: str
    config: dict = field(default_factory=dict)
    is_preset: bool = False
    created_at: str = ""
    updated_at: str = ""


class ExplorerConfigService:
    """Service for explorer configuration CRUD operations."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        config: dict | None = None,
    ) -> ExplorerConfigData:
        """Create a new user explorer configuration.

        Args:
            user_id: Owner's UUID.
            name: Display name.
            config: Explorer settings dict.

        Returns:
            Created configuration data.
        """
        config = config or {}
        config_id = uuid.uuid4()
        spec = ExplorerConfigSpec(
            id=config_id,
            user_id=user_id,
            name=name,
            config_json=json.dumps(config),
            is_preset=False,
        )

        async with self._session_factory() as session:
            session.add(spec)
            await session.commit()
            await session.refresh(spec)
            return self._to_data(spec)

    async def get(self, config_id: uuid.UUID) -> ExplorerConfigData | None:
        """Get a configuration by ID. Returns None if not found."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ExplorerConfigSpec).where(ExplorerConfigSpec.id == config_id)
            )
            spec = result.scalar_one_or_none()
            return self._to_data(spec) if spec else None

    async def list_for_user(self, user_id: uuid.UUID) -> list[ExplorerConfigData]:
        """List all configs owned by a user plus all presets.

        Returns presets (is_preset=True, user_id=NULL) and user's own
        configs, ordered by presets first then by name.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(ExplorerConfigSpec)
                .where(
                    or_(
                        ExplorerConfigSpec.user_id == user_id,
                        ExplorerConfigSpec.is_preset == True,  # noqa: E712
                    )
                )
                .order_by(
                    ExplorerConfigSpec.is_preset.desc(),
                    ExplorerConfigSpec.name,
                )
            )
            specs = result.scalars().all()
            return [self._to_data(s) for s in specs]

    async def update(
        self,
        config_id: uuid.UUID,
        user_id: uuid.UUID,
        **updates,
    ) -> ExplorerConfigData | None:
        """Update a user configuration. Only updates provided fields.

        Presets cannot be updated by users.

        Args:
            config_id: Config UUID.
            user_id: Must match owner for authorization.
            **updates: Fields to update (name, config).

        Returns:
            Updated config data, or None if not found/unauthorized.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(ExplorerConfigSpec).where(
                    ExplorerConfigSpec.id == config_id,
                    ExplorerConfigSpec.user_id == user_id,
                    ExplorerConfigSpec.is_preset == False,  # noqa: E712
                )
            )
            spec = result.scalar_one_or_none()
            if not spec:
                return None

            if "name" in updates:
                spec.name = updates["name"]
            if "config" in updates:
                spec.config_json = json.dumps(updates["config"])

            await session.commit()
            await session.refresh(spec)
            return self._to_data(spec)

    async def delete(self, config_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a user configuration. Presets cannot be deleted.

        Returns True if deleted, False if not found or is a preset.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                delete(ExplorerConfigSpec).where(
                    ExplorerConfigSpec.id == config_id,
                    ExplorerConfigSpec.user_id == user_id,
                    ExplorerConfigSpec.is_preset == False,  # noqa: E712
                )
            )
            await session.commit()
            return result.rowcount > 0

    async def get_or_create_presets(self) -> list[ExplorerConfigData]:
        """Ensure built-in presets exist and return them.

        Creates 'By Type' and 'By Tag' presets if they don't already exist.
        Presets have is_preset=True and user_id=NULL.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(ExplorerConfigSpec).where(
                    ExplorerConfigSpec.is_preset == True  # noqa: E712
                )
            )
            existing = result.scalars().all()
            existing_names = {s.name for s in existing}

            created = []
            for preset in PRESETS:
                if preset["name"] not in existing_names:
                    spec = ExplorerConfigSpec(
                        id=uuid.uuid4(),
                        user_id=None,
                        name=preset["name"],
                        config_json=json.dumps(preset["config"]),
                        is_preset=True,
                    )
                    session.add(spec)
                    created.append(spec)

            if created:
                await session.commit()
                for spec in created:
                    await session.refresh(spec)
                logger.info("Created %d explorer presets", len(created))

            # Return all presets (existing + newly created)
            result = await session.execute(
                select(ExplorerConfigSpec)
                .where(ExplorerConfigSpec.is_preset == True)  # noqa: E712
                .order_by(ExplorerConfigSpec.name)
            )
            all_presets = result.scalars().all()
            return [self._to_data(s) for s in all_presets]

    @staticmethod
    def _to_data(spec: ExplorerConfigSpec) -> ExplorerConfigData:
        """Convert an ExplorerConfigSpec ORM instance to a read model."""
        try:
            config = json.loads(spec.config_json) if spec.config_json else {}
        except (json.JSONDecodeError, TypeError):
            config = {}

        return ExplorerConfigData(
            id=str(spec.id),
            user_id=str(spec.user_id) if spec.user_id else None,
            name=spec.name,
            config=config,
            is_preset=spec.is_preset,
            created_at=spec.created_at.isoformat() if spec.created_at else "",
            updated_at=spec.updated_at.isoformat() if spec.updated_at else "",
        )
