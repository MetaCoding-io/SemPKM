"""Pydantic models for federation API request/response shapes."""

from pydantic import BaseModel


class PatchExportResponse(BaseModel):
    """Response from the patch export endpoint."""

    patch_text: str
    event_count: int
    since: str
    graph_iri: str


class SharedGraphInfo(BaseModel):
    """Information about a shared named graph."""

    graph_iri: str
    name: str
    created: str
    member_count: int
