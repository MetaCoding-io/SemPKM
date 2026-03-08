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


class SessionCreateBody(BaseModel):
    """Request body for creating a named canvas session."""

    name: str = Field(..., min_length=1, max_length=100)
    document: dict[str, Any] = Field(default_factory=dict)


class SessionEntry(BaseModel):
    """A single saved canvas session."""

    id: str
    name: str
    updated_at: str | None = None


class SessionListResponse(BaseModel):
    """Response for listing canvas sessions."""

    sessions: list[SessionEntry]
    active_session_id: str | None = None
