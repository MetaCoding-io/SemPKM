"""Context Zones CRUD API — manage user geofence zones.

Endpoints:
- GET    /api/context/zones       — list zones for authenticated user
- POST   /api/context/zones       — create a new zone
- PUT    /api/context/zones/{id}  — update a zone
- DELETE /api/context/zones/{id}  — delete a zone
"""

import logging
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_user_or_api
from app.auth.models import User
from app.dependencies import get_zone_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/context/zones", tags=["context-zones"])


# ── Request / Response models ────────────────────────────────────


class ZoneCreateRequest(BaseModel):
    """Payload for POST /api/context/zones."""

    name: str = Field(..., min_length=1, max_length=100)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius_meters: float = Field(default=200.0, ge=50, le=10000)
    enabled: bool = Field(default=True)


class ZoneUpdateRequest(BaseModel):
    """Payload for PUT /api/context/zones/{zone_id}. All fields optional."""

    name: str | None = Field(default=None, min_length=1, max_length=100)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    radius_meters: float | None = Field(default=None, ge=50, le=10000)
    enabled: bool | None = None


def _zone_to_dict(zone) -> dict:
    """Convert a ContextZone ORM instance to a JSON-serializable dict."""
    return {
        "id": str(zone.id),
        "user_id": str(zone.user_id),
        "name": zone.name,
        "latitude": zone.latitude,
        "longitude": zone.longitude,
        "radius_meters": zone.radius_meters,
        "enabled": zone.enabled,
        "created_at": zone.created_at.isoformat() if isinstance(zone.created_at, datetime) else str(zone.created_at or ""),
        "updated_at": zone.updated_at.isoformat() if isinstance(zone.updated_at, datetime) else str(zone.updated_at or ""),
    }


# ── Endpoints ────────────────────────────────────────────────────


@router.get("/")
async def list_zones(
    user: User = Depends(get_current_user_or_api),
    zone_service=Depends(get_zone_service),
):
    """List all geofence zones for the authenticated user."""
    zones = await zone_service.list_for_user(user.id)
    return [_zone_to_dict(z) for z in zones]


@router.post("/", status_code=201)
async def create_zone(
    body: ZoneCreateRequest,
    user: User = Depends(get_current_user_or_api),
    zone_service=Depends(get_zone_service),
):
    """Create a new geofence zone."""
    zone = await zone_service.create(
        user_id=user.id,
        name=body.name,
        latitude=body.latitude,
        longitude=body.longitude,
        radius_meters=body.radius_meters,
        enabled=body.enabled,
    )
    return _zone_to_dict(zone)


@router.put("/{zone_id}")
async def update_zone(
    zone_id: uuid.UUID,
    body: ZoneUpdateRequest,
    user: User = Depends(get_current_user_or_api),
    zone_service=Depends(get_zone_service),
):
    """Update a geofence zone. Only provided fields are changed."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update")

    zone = await zone_service.update(zone_id, user.id, **updates)
    if zone is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    return _zone_to_dict(zone)


@router.delete("/{zone_id}", status_code=204)
async def delete_zone(
    zone_id: uuid.UUID,
    user: User = Depends(get_current_user_or_api),
    zone_service=Depends(get_zone_service),
):
    """Delete a geofence zone."""
    deleted = await zone_service.delete(zone_id, user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Zone not found")
    return None
