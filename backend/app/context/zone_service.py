"""ZoneService — CRUD for user geofence zones.

All operations are scoped by user_id for tenant isolation.
Uses the same async_sessionmaker pattern as ContextService.
"""

import logging
import uuid
from datetime import datetime

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.zone_models import ContextZone

logger = logging.getLogger(__name__)

# Fields callers may update on a zone.
_UPDATABLE_FIELDS = frozenset({"name", "latitude", "longitude", "radius_meters", "enabled"})


class ZoneService:
    """CRUD service for per-user geofence zones."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        latitude: float,
        longitude: float,
        radius_meters: float = 200.0,
        enabled: bool = True,
    ) -> ContextZone:
        """Create a new geofence zone for *user_id*."""
        async with self._session_factory() as session:
            zone = ContextZone(
                id=uuid.uuid4(),
                user_id=user_id,
                name=name,
                latitude=latitude,
                longitude=longitude,
                radius_meters=radius_meters,
                enabled=enabled,
            )
            session.add(zone)
            await session.commit()
            await session.refresh(zone)

            logger.info(
                "context.zone_crud action=create user_id=%s zone_id=%s name=%s",
                user_id,
                zone.id,
                zone.name,
            )
            return zone

    async def list_for_user(self, user_id: uuid.UUID) -> list[ContextZone]:
        """Return all zones belonging to *user_id*, ordered by name."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ContextZone)
                .where(ContextZone.user_id == user_id)
                .order_by(ContextZone.name)
            )
            return list(result.scalars().all())

    async def get(self, zone_id: uuid.UUID, user_id: uuid.UUID) -> ContextZone | None:
        """Return a single zone if it belongs to *user_id*, else None."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(ContextZone).where(
                    ContextZone.id == zone_id,
                    ContextZone.user_id == user_id,
                )
            )
            return result.scalar_one_or_none()

    async def update(
        self, zone_id: uuid.UUID, user_id: uuid.UUID, **fields
    ) -> ContextZone | None:
        """Update a zone. Only provided fields in _UPDATABLE_FIELDS are changed.

        Returns the updated zone, or None if not found / not owned.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(ContextZone).where(
                    ContextZone.id == zone_id,
                    ContextZone.user_id == user_id,
                )
            )
            zone = result.scalar_one_or_none()
            if zone is None:
                return None

            for key in _UPDATABLE_FIELDS:
                if key in fields:
                    setattr(zone, key, fields[key])

            await session.commit()
            await session.refresh(zone)

            logger.info(
                "context.zone_crud action=update user_id=%s zone_id=%s fields=%s",
                user_id,
                zone_id,
                list(fields.keys()),
            )
            return zone

    async def delete(self, zone_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        """Delete a zone. Returns True if a row was removed, False otherwise."""
        async with self._session_factory() as session:
            result = await session.execute(
                delete(ContextZone).where(
                    ContextZone.id == zone_id,
                    ContextZone.user_id == user_id,
                )
            )
            await session.commit()
            deleted = result.rowcount > 0

            if deleted:
                logger.info(
                    "context.zone_crud action=delete user_id=%s zone_id=%s",
                    user_id,
                    zone_id,
                )
            return deleted
