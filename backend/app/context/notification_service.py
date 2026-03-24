"""NotificationService — token CRUD, preference management, context-aware
suppression, and FCM dispatch with no-op mode.

When ``firebase_app`` is None the service operates in no-op mode: all
send calls are skipped with a warning log.  This allows the full test
suite to run without Firebase credentials.
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.context.notification_models import DeviceToken, NotificationPreferences

logger = logging.getLogger(__name__)

# ── helpers ──────────────────────────────────────────────────────

_DEFAULT_ENABLED_TYPES = [
    "overdue_tasks",
    "validation_warnings",
    "context_changes",
]


def _token_prefix(token: str) -> str:
    """Return the first 20 chars of a token + '...' for safe logging."""
    return token[:20] + "..." if len(token) > 20 else token


def _parse_time(hhmm: str) -> tuple[int, int]:
    """Parse 'HH:MM' into (hour, minute).  Raises ValueError on bad input."""
    parts = hhmm.strip().split(":")
    return int(parts[0]), int(parts[1])


# ── service ──────────────────────────────────────────────────────


class NotificationService:
    """Push-notification orchestrator with context-aware suppression.

    Parameters
    ----------
    session_factory:
        Async session factory for DB access.
    context_service:
        Optional ``ContextService`` for calendar-busy suppression.
    firebase_app:
        An initialised ``firebase_admin.App``.  ``None`` → no-op mode.
    """

    def __init__(
        self,
        session_factory,
        context_service=None,
        firebase_app=None,
    ) -> None:
        self._session_factory = session_factory
        self._context_service = context_service
        self._firebase_app = firebase_app

    # ── Token CRUD ───────────────────────────────────────────────

    async def register_token(
        self,
        user_id: uuid.UUID,
        token: str,
        platform: str,
        device_name: str | None = None,
    ) -> DeviceToken:
        """Register or update a device token (upsert by token value)."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(DeviceToken).where(DeviceToken.token == token)
            )
            row = result.scalar_one_or_none()

            if row is None:
                row = DeviceToken(
                    id=uuid.uuid4(),
                    user_id=user_id,
                    token=token,
                    platform=platform,
                    device_name=device_name,
                )
                session.add(row)
                logger.info(
                    "notification.token_registered user_id=%s platform=%s token_prefix=%s",
                    user_id,
                    platform,
                    _token_prefix(token),
                )
            else:
                row.user_id = user_id
                row.platform = platform
                row.device_name = device_name
                logger.info(
                    "notification.token_updated user_id=%s platform=%s token_prefix=%s",
                    user_id,
                    platform,
                    _token_prefix(token),
                )

            await session.commit()
            await session.refresh(row)
            return row

    async def unregister_token(self, token: str) -> bool:
        """Delete a device token.  Returns True if a row was deleted."""
        async with self._session_factory() as session:
            result = await session.execute(
                delete(DeviceToken).where(DeviceToken.token == token)
            )
            await session.commit()
            deleted = result.rowcount > 0
            if deleted:
                logger.info(
                    "notification.token_unregistered token_prefix=%s",
                    _token_prefix(token),
                )
            return deleted

    async def get_tokens_for_user(self, user_id: uuid.UUID) -> list[DeviceToken]:
        """Return all device tokens for a user."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(DeviceToken).where(DeviceToken.user_id == user_id)
            )
            return list(result.scalars().all())

    # ── Preferences ──────────────────────────────────────────────

    async def get_preferences(self, user_id: uuid.UUID) -> dict[str, Any]:
        """Return notification preferences for a user (defaults if no row)."""
        async with self._session_factory() as session:
            result = await session.execute(
                select(NotificationPreferences).where(
                    NotificationPreferences.user_id == user_id
                )
            )
            row = result.scalar_one_or_none()

            if row is None:
                return {
                    "enabled": True,
                    "quiet_hours_start": None,
                    "quiet_hours_end": None,
                    "suppress_when_busy": True,
                    "enabled_types": _DEFAULT_ENABLED_TYPES,
                }

            return {
                "enabled": row.enabled,
                "quiet_hours_start": row.quiet_hours_start,
                "quiet_hours_end": row.quiet_hours_end,
                "suppress_when_busy": row.suppress_when_busy,
                "enabled_types": (
                    json.loads(row.enabled_types)
                    if row.enabled_types
                    else _DEFAULT_ENABLED_TYPES
                ),
            }

    async def update_preferences(
        self, user_id: uuid.UUID, **fields
    ) -> dict[str, Any]:
        """Upsert notification preferences.  Only provided fields are written."""
        _WRITABLE = frozenset(
            {
                "enabled",
                "quiet_hours_start",
                "quiet_hours_end",
                "suppress_when_busy",
                "enabled_types",
            }
        )
        async with self._session_factory() as session:
            result = await session.execute(
                select(NotificationPreferences).where(
                    NotificationPreferences.user_id == user_id
                )
            )
            row = result.scalar_one_or_none()

            if row is None:
                row = NotificationPreferences(
                    id=uuid.uuid4(), user_id=user_id
                )
                session.add(row)

            for key in _WRITABLE:
                if key in fields:
                    value = fields[key]
                    # Serialise enabled_types list → JSON string for storage
                    if key == "enabled_types" and isinstance(value, list):
                        value = json.dumps(value)
                    setattr(row, key, value)

            await session.commit()
            await session.refresh(row)

            return {
                "enabled": row.enabled,
                "quiet_hours_start": row.quiet_hours_start,
                "quiet_hours_end": row.quiet_hours_end,
                "suppress_when_busy": row.suppress_when_busy,
                "enabled_types": (
                    json.loads(row.enabled_types)
                    if row.enabled_types
                    else _DEFAULT_ENABLED_TYPES
                ),
            }

    # ── Suppression ──────────────────────────────────────────────

    async def should_suppress(
        self,
        user_id: uuid.UUID,
        notification_type: str | None = None,
        *,
        _now: datetime | None = None,
    ) -> tuple[bool, str | None]:
        """Decide whether a notification should be suppressed.

        Returns ``(True, reason)`` if suppressed, ``(False, None)`` if allowed.

        The private ``_now`` parameter allows tests to inject a fixed time.
        """
        prefs = await self.get_preferences(user_id)

        # (a) Master disable
        if not prefs["enabled"]:
            logger.info(
                "notification.suppressed user_id=%s reason=disabled", user_id
            )
            return True, "disabled"

        # (b) Type not in enabled list
        if notification_type is not None:
            enabled = prefs["enabled_types"]
            if isinstance(enabled, list) and notification_type not in enabled:
                logger.info(
                    "notification.suppressed user_id=%s reason=type_disabled type=%s",
                    user_id,
                    notification_type,
                )
                return True, "type_disabled"

        # (c) Calendar busy
        if prefs["suppress_when_busy"] and self._context_service is not None:
            ctx = await self._context_service.get_current(user_id)
            if ctx is not None and ctx.calendar_busy:
                logger.info(
                    "notification.suppressed user_id=%s reason=calendar_busy",
                    user_id,
                )
                return True, "calendar_busy"

        # (d) Quiet hours
        start_str = prefs["quiet_hours_start"]
        end_str = prefs["quiet_hours_end"]
        if start_str and end_str:
            try:
                start_h, start_m = _parse_time(start_str)
                end_h, end_m = _parse_time(end_str)
                now = _now or datetime.now(timezone.utc)
                now_minutes = now.hour * 60 + now.minute
                start_minutes = start_h * 60 + start_m
                end_minutes = end_h * 60 + end_m

                in_quiet: bool
                if start_minutes > end_minutes:
                    # Midnight span (e.g. 22:00 → 07:00)
                    in_quiet = now_minutes >= start_minutes or now_minutes < end_minutes
                else:
                    # Normal range (e.g. 22:00 → 23:00)
                    in_quiet = start_minutes <= now_minutes < end_minutes

                if in_quiet:
                    logger.info(
                        "notification.suppressed user_id=%s reason=quiet_hours",
                        user_id,
                    )
                    return True, "quiet_hours"
            except (ValueError, IndexError):
                logger.warning(
                    "notification.quiet_hours_parse_error user_id=%s start=%s end=%s",
                    user_id,
                    start_str,
                    end_str,
                )

        return False, None

    # ── Dispatch ─────────────────────────────────────────────────

    async def send_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
    ) -> str | None:
        """Send a single FCM notification.  Returns message ID or None.

        In no-op mode (firebase_app is None) logs a warning and returns None.
        On ``UnregisteredError`` the stale token is auto-deleted.
        """
        if self._firebase_app is None:
            logger.warning(
                "notification.skipped reason=firebase_not_configured token_prefix=%s",
                _token_prefix(token),
            )
            return None

        from firebase_admin import messaging  # lazy import — heavy

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data=data or {},
            token=token,
        )

        try:
            msg_id: str = await asyncio.to_thread(
                messaging.send, message, app=self._firebase_app
            )
            logger.info(
                "notification.sent token_prefix=%s msg_id=%s",
                _token_prefix(token),
                msg_id,
            )
            return msg_id
        except messaging.UnregisteredError:
            logger.warning(
                "notification.token_expired token_prefix=%s",
                _token_prefix(token),
            )
            await self.unregister_token(token)
            return None
        except Exception:
            logger.exception(
                "notification.send_error token_prefix=%s",
                _token_prefix(token),
            )
            return None

    async def send_to_user(
        self,
        user_id: uuid.UUID,
        title: str,
        body: str,
        data: dict[str, str] | None = None,
        notification_type: str | None = None,
    ) -> list[str | None]:
        """Send a notification to all of a user's devices, with suppression.

        Returns a list of message IDs (or None for skipped/failed sends).
        """
        suppressed, reason = await self.should_suppress(
            user_id, notification_type=notification_type
        )
        if suppressed:
            logger.info(
                "notification.suppressed user_id=%s reason=%s type=%s",
                user_id,
                reason,
                notification_type,
            )
            return []

        tokens = await self.get_tokens_for_user(user_id)
        if not tokens:
            logger.info(
                "notification.skipped user_id=%s reason=no_tokens", user_id
            )
            return []

        results = []
        for dt in tokens:
            msg_id = await self.send_notification(
                dt.token, title, body, data=data
            )
            results.append(msg_id)

        return results
