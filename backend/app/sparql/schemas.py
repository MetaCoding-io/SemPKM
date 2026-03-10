"""Pydantic request/response schemas for SPARQL history, saved queries, and vocabulary."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QueryHistoryOut(BaseModel):
    """Response schema for a single query history entry."""

    id: uuid.UUID
    query_text: str
    executed_at: datetime

    model_config = ConfigDict(from_attributes=True)


class SavedQueryCreate(BaseModel):
    """Request schema for creating a saved query."""

    name: str
    description: str | None = None
    query_text: str


class SavedQueryUpdate(BaseModel):
    """Request schema for updating a saved query (all fields optional)."""

    name: str | None = None
    description: str | None = None
    query_text: str | None = None


class SavedQueryOut(BaseModel):
    """Response schema for a saved query."""

    id: uuid.UUID
    name: str
    description: str | None
    query_text: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class VocabularyItem(BaseModel):
    """A single vocabulary entity (class, property, or datatype)."""

    qname: str
    full_iri: str
    badge: str  # "C" for class, "P" for property, "D" for datatype
    label: str | None = None


class VocabularyOut(BaseModel):
    """Response schema for vocabulary endpoint."""

    prefixes: dict[str, str]
    items: list[VocabularyItem]
    model_version: int
