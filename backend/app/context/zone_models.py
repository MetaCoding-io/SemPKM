"""ContextZone SQLAlchemy model.

Stores per-user geofence zones with center coordinates, radius, and
enabled flag. Zone data is kept in SQLite (not RDF) per D336 —
privacy-by-design for location coordinates. Each zone defines a
circular geofence for mobile location-based context switching.
"""

import uuid
from datetime import datetime

import sqlalchemy as sa
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ContextZone(Base):
    """A circular geofence zone tied to a user.

    Attributes:
        id: UUID primary key.
        user_id: Owner (FK to users).
        name: Human label for the zone (e.g. "Home", "Office").
        latitude: Center latitude in decimal degrees.
        longitude: Center longitude in decimal degrees.
        radius_meters: Geofence radius in meters (default 200).
        enabled: Whether the zone participates in geofencing.
        created_at: Row creation timestamp.
        updated_at: Last modification timestamp.
    """

    __tablename__ = "context_zones"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    radius_meters: Mapped[float] = mapped_column(
        Float, default=200.0, server_default=sa.text("200.0"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(
        Boolean(), default=True, server_default=sa.true()
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
