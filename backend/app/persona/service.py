"""PersonaService — CRUD + activation + state management for workspace personas.

Provides async methods for creating, listing, updating, deleting, activating,
and saving state for workspace personas stored in SQLite. Enforces the
single-active-persona-per-user constraint.
"""

import logging
import uuid
from dataclasses import dataclass

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.persona.models import Persona

logger = logging.getLogger(__name__)


@dataclass
class PersonaData:
    """Lightweight read model for a persona."""

    id: str
    user_id: str
    name: str
    layout_json: str
    sidebar_positions_json: str
    explorer_mode: str
    is_active: bool
    created_at: str
    updated_at: str


class PersonaService:
    """Service for persona CRUD operations and workspace state management."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        layout_json: str = "",
        sidebar_positions_json: str = "",
        explorer_mode: str = "by-type",
    ) -> PersonaData:
        """Create a new persona.

        Args:
            user_id: Owner's UUID.
            name: Display name for the persona.
            layout_json: Serialized dockview layout.
            sidebar_positions_json: Serialized sidebar positions.
            explorer_mode: Explorer grouping mode.

        Returns:
            Created persona data.
        """
        persona = Persona(
            id=uuid.uuid4(),
            user_id=user_id,
            name=name,
            layout_json=layout_json or "{}",
            sidebar_positions_json=sidebar_positions_json or "{}",
            explorer_mode=explorer_mode,
            is_active=False,
        )

        async with self._session_factory() as session:
            session.add(persona)
            await session.commit()
            await session.refresh(persona)
            logger.info("Persona created: %s (user=%s)", persona.name, user_id)
            return self._to_data(persona)

    async def list_for_user(self, user_id: uuid.UUID) -> list[PersonaData]:
        """List all personas for a user, ordered by name."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Persona)
                .where(Persona.user_id == user_id)
                .order_by(Persona.name)
            )
            personas = result.scalars().all()
            return [self._to_data(p) for p in personas]

    async def get(self, persona_id: uuid.UUID) -> PersonaData | None:
        """Get a persona by ID. Returns None if not found."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Persona).where(Persona.id == persona_id)
            )
            persona = result.scalar_one_or_none()
            return self._to_data(persona) if persona else None

    async def update(
        self,
        persona_id: uuid.UUID,
        user_id: uuid.UUID,
        **updates,
    ) -> PersonaData | None:
        """Update a persona's name. Returns None if not found or wrong user.

        Args:
            persona_id: Persona UUID.
            user_id: Must match owner for authorization.
            **updates: Fields to update (only 'name' is accepted).

        Returns:
            Updated persona data, or None if not found/unauthorized.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(Persona).where(
                    Persona.id == persona_id,
                    Persona.user_id == user_id,
                )
            )
            persona = result.scalar_one_or_none()
            if not persona:
                logger.warning(
                    "Persona update failed: not found or wrong user (id=%s, user=%s)",
                    persona_id,
                    user_id,
                )
                return None

            if "name" in updates:
                persona.name = updates["name"]

            await session.commit()
            await session.refresh(persona)
            return self._to_data(persona)

    async def delete(self, persona_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a persona. If it was active, activates first remaining persona.

        Returns:
            True if deleted, False if not found or wrong user.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(Persona).where(
                    Persona.id == persona_id,
                    Persona.user_id == user_id,
                )
            )
            persona = result.scalar_one_or_none()
            if not persona:
                return False

            was_active = persona.is_active
            await session.delete(persona)
            await session.flush()

            # If the deleted persona was active, activate the first remaining one
            if was_active:
                remaining = await session.execute(
                    select(Persona)
                    .where(Persona.user_id == user_id)
                    .order_by(Persona.name)
                    .limit(1)
                )
                next_persona = remaining.scalar_one_or_none()
                if next_persona:
                    next_persona.is_active = True
                    logger.info(
                        "Persona auto-activated after delete: %s", next_persona.name
                    )

            await session.commit()
            logger.info("Persona deleted: id=%s (user=%s)", persona_id, user_id)
            return True

    async def activate(
        self, persona_id: uuid.UUID, user_id: uuid.UUID
    ) -> PersonaData | None:
        """Activate a persona, deactivating all others for the user.

        Enforces the single-active-persona constraint: deactivate all,
        then activate the requested one.

        Returns:
            Activated persona data, or None if not found/wrong user.
        """
        async with self._session_factory() as session:
            # Verify the target persona exists and belongs to user
            result = await session.execute(
                select(Persona).where(
                    Persona.id == persona_id,
                    Persona.user_id == user_id,
                )
            )
            persona = result.scalar_one_or_none()
            if not persona:
                logger.warning(
                    "Persona activate failed: not found or wrong user (id=%s, user=%s)",
                    persona_id,
                    user_id,
                )
                return None

            # Deactivate all user's personas
            await session.execute(
                update(Persona)
                .where(Persona.user_id == user_id)
                .values(is_active=False)
            )

            # Activate the target
            persona.is_active = True
            await session.commit()
            await session.refresh(persona)
            logger.info("Persona activated: %s (user=%s)", persona.name, user_id)
            return self._to_data(persona)

    async def get_active(self, user_id: uuid.UUID) -> PersonaData | None:
        """Get the user's active persona. Returns None if no persona is active."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(Persona).where(
                    Persona.user_id == user_id,
                    Persona.is_active == True,  # noqa: E712
                )
            )
            persona = result.scalar_one_or_none()
            return self._to_data(persona) if persona else None

    async def save_state(
        self,
        persona_id: uuid.UUID,
        user_id: uuid.UUID,
        layout_json: str | None = None,
        sidebar_positions_json: str | None = None,
        explorer_mode: str | None = None,
    ) -> PersonaData | None:
        """Save workspace state to a persona. Only updates provided fields.

        Args:
            persona_id: Persona UUID.
            user_id: Must match owner for authorization.
            layout_json: Dockview serialized layout (if provided).
            sidebar_positions_json: Sidebar positions (if provided).
            explorer_mode: Explorer grouping mode (if provided).

        Returns:
            Updated persona data, or None if not found/unauthorized.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(Persona).where(
                    Persona.id == persona_id,
                    Persona.user_id == user_id,
                )
            )
            persona = result.scalar_one_or_none()
            if not persona:
                logger.warning(
                    "Persona save_state failed: not found or wrong user (id=%s, user=%s)",
                    persona_id,
                    user_id,
                )
                return None

            if layout_json is not None:
                persona.layout_json = layout_json
            if sidebar_positions_json is not None:
                persona.sidebar_positions_json = sidebar_positions_json
            if explorer_mode is not None:
                persona.explorer_mode = explorer_mode

            await session.commit()
            await session.refresh(persona)
            return self._to_data(persona)

    @staticmethod
    def _to_data(persona: Persona) -> PersonaData:
        """Convert a Persona ORM instance to a PersonaData read model."""
        return PersonaData(
            id=str(persona.id),
            user_id=str(persona.user_id),
            name=persona.name,
            layout_json=persona.layout_json or "{}",
            sidebar_positions_json=persona.sidebar_positions_json or "{}",
            explorer_mode=persona.explorer_mode or "by-type",
            is_active=persona.is_active,
            created_at=persona.created_at.isoformat() if persona.created_at else "",
            updated_at=persona.updated_at.isoformat() if persona.updated_at else "",
        )
