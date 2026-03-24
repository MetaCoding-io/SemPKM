"""ContextService — upsert + staleness detection for user context.

One row per user. Updates merge only the fields explicitly provided.
Staleness is computed at read time based on a configurable TTL.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.models import UserContext

logger = logging.getLogger(__name__)

# ── Default TTL: 15 minutes ──────────────────────────────────────
DEFAULT_TTL_SECONDS = 900

# Fields on UserContext that callers may update via keyword args.
_UPDATABLE_FIELDS = frozenset(
    {
        "location_zone",
        "activity",
        "time_period",
        "calendar_event",
        "calendar_busy",
        "device_id",
    }
)


@dataclass
class ContextData:
    """Read-model for a user's current context snapshot."""

    user_id: str
    location_zone: str | None = None
    activity: str | None = None
    time_period: str | None = None
    calendar_event: str | None = None
    calendar_busy: bool = False
    device_id: str | None = None
    is_stale: bool = False
    ttl_seconds: int = DEFAULT_TTL_SECONDS
    updated_at: str = ""
    created_at: str = ""


class ContextService:
    """Upsert / read service for per-user context state."""

    def __init__(self, session_factory) -> None:
        self._session_factory = session_factory

    # ── write ────────────────────────────────────────────────────
    async def update(self, user_id: uuid.UUID, **fields) -> ContextData:
        """Upsert the context row for *user_id*.

        Only the keyword arguments that are explicitly provided (and
        present in ``_UPDATABLE_FIELDS``) are written. Missing keys
        leave the stored value unchanged.

        Returns the full context snapshot after the write, with
        ``is_stale`` always ``False`` (we just wrote it).
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserContext).where(UserContext.user_id == user_id)
            )
            row = result.scalar_one_or_none()

            if row is None:
                # INSERT — new context row
                row = UserContext(id=uuid.uuid4(), user_id=user_id)
                for key in _UPDATABLE_FIELDS:
                    if key in fields:
                        setattr(row, key, fields[key])
                session.add(row)
            else:
                # UPDATE — merge only provided fields
                for key in _UPDATABLE_FIELDS:
                    if key in fields:
                        setattr(row, key, fields[key])

            await session.commit()
            await session.refresh(row)

            logger.info(
                "context.update user_id=%s location_zone=%s device_id=%s",
                user_id,
                row.location_zone,
                row.device_id,
            )
            return self._to_data(row, is_stale=False)

    # ── read ─────────────────────────────────────────────────────
    async def get_current(
        self,
        user_id: uuid.UUID,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> ContextData | None:
        """Return the current context for *user_id*, or ``None``.

        ``is_stale`` is True when ``updated_at`` is more than
        *ttl_seconds* in the past.
        """
        async with self._session_factory() as session:
            result = await session.execute(
                select(UserContext).where(UserContext.user_id == user_id)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None

            # Handle naive datetimes from SQLite (see KNOWLEDGE.md)
            updated = row.updated_at
            if updated is not None and updated.tzinfo is None:
                updated = updated.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            age_seconds = (now - updated).total_seconds() if updated else float("inf")
            is_stale = age_seconds > ttl_seconds

            if is_stale:
                logger.info(
                    "context.stale user_id=%s age_seconds=%.1f ttl=%d",
                    user_id,
                    age_seconds,
                    ttl_seconds,
                )

            return self._to_data(row, is_stale=is_stale, ttl_seconds=ttl_seconds)

    # ── internal ─────────────────────────────────────────────────
    @staticmethod
    def _to_data(
        row: UserContext,
        *,
        is_stale: bool = False,
        ttl_seconds: int = DEFAULT_TTL_SECONDS,
    ) -> ContextData:
        return ContextData(
            user_id=str(row.user_id),
            location_zone=row.location_zone,
            activity=row.activity,
            time_period=row.time_period,
            calendar_event=row.calendar_event,
            calendar_busy=row.calendar_busy,
            device_id=row.device_id,
            is_stale=is_stale,
            ttl_seconds=ttl_seconds,
            updated_at=row.updated_at.isoformat() if row.updated_at else "",
            created_at=row.created_at.isoformat() if row.created_at else "",
        )
