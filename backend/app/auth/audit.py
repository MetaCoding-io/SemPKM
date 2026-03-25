"""Security audit logging helper (F-029/F-030).

Provides a single async function to record security events into the
SecurityAuditLog table. Designed to be fire-and-forget — audit logging
should never block or crash the calling operation.
"""

import json
import logging
import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth.models import SecurityAuditLog

logger = logging.getLogger(__name__)


async def log_security_event(
    session_factory: async_sessionmaker[AsyncSession],
    event_type: str,
    source_ip: str,
    user_id: uuid.UUID | None = None,
    detail: dict[str, Any] | None = None,
) -> None:
    """Record a security event to the audit log table.

    This function manages its own session so callers don't need to
    pass one. It catches all exceptions internally — audit logging
    must never fail the parent operation.

    Args:
        session_factory: SQLAlchemy async session factory.
        event_type: One of AUDIT_EVENT_TYPES (login_success, login_failed, etc.)
        source_ip: Client IP address.
        user_id: User UUID if known (None for failed logins by unknown users).
        detail: Optional dict with event-specific data (serialised as JSON).
    """
    try:
        async with session_factory() as session:
            entry = SecurityAuditLog(
                event_type=event_type,
                user_id=user_id,
                source_ip=source_ip,
                detail=json.dumps(detail or {}),
            )
            session.add(entry)
            await session.commit()
    except Exception:
        # Audit logging must never crash the calling operation.
        logger.warning("Failed to write security audit log entry", exc_info=True)
