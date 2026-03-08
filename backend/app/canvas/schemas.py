"""Pydantic schemas for Spatial Canvas persistence endpoints."""

from typing import Any

from pydantic import BaseModel, Field


class CanvasPutBody(BaseModel):
    """Request body for saving a canvas document."""

    document: dict[str, Any] = Field(default_factory=dict)


class CanvasResponse(BaseModel):
    """Response payload for canvas load/save endpoints."""

    canvas_id: str
    document: dict[str, Any]
    updated_at: str | None = None
