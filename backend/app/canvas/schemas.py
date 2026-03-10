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


class WikilinkResolveRequest(BaseModel):
    """Request body for resolving wiki-link titles to IRIs."""

    titles: list[str] = Field(
        ..., max_length=50, description="Wiki-link display text to resolve to IRIs"
    )


class WikilinkResolveResponse(BaseModel):
    """Response for wiki-link title resolution."""

    resolved: dict[str, str | None]  # {title: iri_or_null}


class BatchEdgesRequest(BaseModel):
    """Request body for discovering edges between a set of IRIs."""

    iris: list[str] = Field(
        ..., min_length=1, max_length=100, description="IRIs to find edges between"
    )


class BatchEdge(BaseModel):
    """A single edge between two IRIs."""

    source: str
    target: str
    predicate: str
    predicate_label: str


class BatchEdgesResponse(BaseModel):
    """Response for batch edge discovery."""

    edges: list[BatchEdge]
