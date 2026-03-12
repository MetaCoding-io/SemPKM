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


class SharedGraphCreate(BaseModel):
    """Request to create a new shared graph."""

    name: str
    description: str = ""
    required_model: str = ""


class SharedGraphResponse(BaseModel):
    """Shared graph details with membership and sync status."""

    graph_iri: str
    name: str
    description: str
    created: str
    members: list[str]
    last_sync: str | None
    pending_count: int


class InvitationSend(BaseModel):
    """Request to send a shared graph invitation to a remote user."""

    recipient_handle: str  # WebID URL or user@domain
    graph_iri: str
    message: str = ""


class SyncResult(BaseModel):
    """Result of a sync pull/apply operation."""

    pulled: int
    applied: int
    errors: list[str]


class NotificationSend(BaseModel):
    """Request to send a notification to a remote user."""

    recipient_handle: str
    notification_type: str  # recommendation or message
    object_iri: str | None = None
    content: str | None = None


class ContactInfo(BaseModel):
    """Information about a known remote contact."""

    webid: str
    label: str
    instance_url: str
    last_seen: str | None
