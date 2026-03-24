"""Notification API router — device token registration, preference CRUD,
and diagnostic test-send endpoint.

All endpoints require authentication via session cookie or API key
(``get_current_user_or_api``).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, field_validator

from app.auth.dependencies import get_current_user_or_api
from app.auth.models import User

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/notifications",
    tags=["notifications"],
)


# ── Request / Response schemas ───────────────────────────────────


class RegisterTokenRequest(BaseModel):
    token: str
    platform: str
    device_name: str | None = None

    @field_validator("platform")
    @classmethod
    def validate_platform(cls, v: str) -> str:
        allowed = {"ios", "android"}
        if v not in allowed:
            raise ValueError(f"platform must be one of {allowed}")
        return v


class UpdatePreferencesRequest(BaseModel):
    enabled: bool | None = None
    quiet_hours_start: str | None = None
    quiet_hours_end: str | None = None
    suppress_when_busy: bool | None = None
    enabled_types: list[str] | None = None

    @field_validator("quiet_hours_start", "quiet_hours_end")
    @classmethod
    def validate_time_format(cls, v: str | None) -> str | None:
        if v is None:
            return v
        parts = v.strip().split(":")
        if len(parts) != 2:
            raise ValueError("Time must be in HH:MM format")
        try:
            h, m = int(parts[0]), int(parts[1])
            if not (0 <= h <= 23 and 0 <= m <= 59):
                raise ValueError()
        except (ValueError, IndexError):
            raise ValueError("Time must be in HH:MM format with valid hour (0-23) and minute (0-59)")
        return v


# ── Dependency helper ────────────────────────────────────────────


def _get_notification_service(request: Request):
    """Extract NotificationService from app.state (set in lifespan)."""
    svc = getattr(request.app.state, "notification_service", None)
    if svc is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Notification service not available",
        )
    return svc


# ── Endpoints ────────────────────────────────────────────────────


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_token(
    body: RegisterTokenRequest,
    request: Request,
    user: User = Depends(get_current_user_or_api),
):
    """Register (or update) a device push token for the current user."""
    service = _get_notification_service(request)
    token_row = await service.register_token(
        user_id=user.id,
        token=body.token,
        platform=body.platform,
        device_name=body.device_name,
    )
    return {
        "id": str(token_row.id),
        "platform": token_row.platform,
        "device_name": token_row.device_name,
        "created_at": str(token_row.created_at),
    }


@router.get("/preferences")
async def get_preferences(
    request: Request,
    user: User = Depends(get_current_user_or_api),
):
    """Return notification preferences for the current user (defaults if no row)."""
    service = _get_notification_service(request)
    prefs = await service.get_preferences(user.id)
    return prefs


@router.put("/preferences")
async def update_preferences(
    body: UpdatePreferencesRequest,
    request: Request,
    user: User = Depends(get_current_user_or_api),
):
    """Update notification preferences for the current user.

    Only provided fields are changed; omitted fields keep their current value.
    """
    service = _get_notification_service(request)
    fields: dict[str, Any] = {}
    if body.enabled is not None:
        fields["enabled"] = body.enabled
    if body.quiet_hours_start is not None:
        fields["quiet_hours_start"] = body.quiet_hours_start
    if body.quiet_hours_end is not None:
        fields["quiet_hours_end"] = body.quiet_hours_end
    if body.suppress_when_busy is not None:
        fields["suppress_when_busy"] = body.suppress_when_busy
    if body.enabled_types is not None:
        fields["enabled_types"] = body.enabled_types

    if not fields:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No fields provided to update",
        )

    updated = await service.update_preferences(user.id, **fields)
    return updated


@router.post("/test")
async def test_notification(
    request: Request,
    user: User = Depends(get_current_user_or_api),
):
    """Send a test notification to all user's registered devices.

    Returns the number of messages sent and whether suppression was active.
    """
    service = _get_notification_service(request)

    # Check suppression first so we can report it
    suppressed, reason = await service.should_suppress(user.id, notification_type="test")
    if suppressed:
        return {"sent_count": 0, "suppressed": True, "reason": reason}

    tokens = await service.get_tokens_for_user(user.id)
    if not tokens:
        return {"sent_count": 0, "suppressed": False, "reason": "no_devices"}

    results = await service.send_to_user(
        user.id,
        "SemPKM Test",
        "Push notifications are working!",
        notification_type="test",
    )
    sent_count = sum(1 for r in results if r is not None)
    return {"sent_count": sent_count, "suppressed": False, "reason": None}
