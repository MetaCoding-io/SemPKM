"""Data models for RDF import: parsed subjects, parse results, import results."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from rdflib import Graph


@dataclass
class SubjectInfo:
    """One parsed RDF subject with extracted metadata."""

    iri: str
    types: list[str]
    label: str | None
    property_count: int
    is_blank_node: bool
    triples: list[tuple]  # (s, p, o) raw triples for this subject


@dataclass
class RdfParseResult:
    """Result of parsing RDF content — subjects, metadata, and any errors."""

    subjects: list[SubjectInfo]
    total_triples: int
    format_used: str
    errors: list[str]
    raw_graph: Graph | None = None


@dataclass
class RdfImportResult:
    """Result of executing an RDF import into the EventStore."""

    created: int = 0
    skipped: int = 0
    errors: list[dict[str, Any]] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "created": self.created,
            "skipped": self.skipped,
            "errors": self.errors,
            "duration_seconds": self.duration_seconds,
        }
