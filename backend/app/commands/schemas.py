"""Pydantic v2 models for the SemPKM command API.

Uses discriminated unions on the `command` field to route requests to
the correct handler. Supports both single command and batch (array)
request payloads, normalizing both to a list internally.
"""

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field


# --- Parameter models ---


class ObjectCreateParams(BaseModel):
    """Parameters for creating a new object."""

    type: str  # RDF type local name, e.g. "Person", "Note"
    slug: str | None = None  # Optional human-readable slug; UUID fallback
    properties: dict[str, Any] = {}  # predicate -> value pairs (compact IRI or full)


class ObjectPatchParams(BaseModel):
    """Parameters for patching an existing object's properties."""

    iri: str  # The object IRI to patch
    properties: dict[str, Any]  # predicate -> new value (only specified predicates updated)


class BodySetParams(BaseModel):
    """Parameters for setting an object's Markdown body."""

    iri: str  # The object IRI
    body: str  # Markdown content


class EdgeCreateParams(BaseModel):
    """Parameters for creating a typed edge between objects."""

    source: str  # Source object IRI
    target: str  # Target object IRI
    predicate: str  # Relationship type IRI or compact form
    properties: dict[str, Any] = {}  # Optional edge annotations


class EdgePatchParams(BaseModel):
    """Parameters for patching edge annotation properties."""

    iri: str  # Edge resource IRI
    properties: dict[str, Any]  # Updated edge annotations


# --- Command models (discriminated union) ---


class ObjectCreateCommand(BaseModel):
    """Create a new object."""

    command: Literal["object.create"]
    params: ObjectCreateParams


class ObjectPatchCommand(BaseModel):
    """Patch an existing object's properties."""

    command: Literal["object.patch"]
    params: ObjectPatchParams


class BodySetCommand(BaseModel):
    """Set an object's Markdown body."""

    command: Literal["body.set"]
    params: BodySetParams


class EdgeCreateCommand(BaseModel):
    """Create a typed edge between objects."""

    command: Literal["edge.create"]
    params: EdgeCreateParams


class EdgePatchCommand(BaseModel):
    """Patch edge annotation properties."""

    command: Literal["edge.patch"]
    params: EdgePatchParams


# Discriminated union type
Command = Annotated[
    Union[
        ObjectCreateCommand,
        ObjectPatchCommand,
        BodySetCommand,
        EdgeCreateCommand,
        EdgePatchCommand,
    ],
    Field(discriminator="command"),
]


# --- Request / Response models ---


class CommandResult(BaseModel):
    """Result of a single command execution."""

    iri: str  # The IRI of the created/modified resource
    event_iri: str  # The event graph IRI
    command: str  # The command type that was executed


class CommandResponse(BaseModel):
    """Response for the POST /api/commands endpoint."""

    results: list[CommandResult]
    event_iri: str  # The shared event graph IRI
    timestamp: str  # ISO 8601 timestamp
