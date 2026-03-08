"""Data models for Obsidian vault scan and import results.

Dataclasses representing the structured output of a vault scan and
import execution: file counts, detected note types, frontmatter keys,
tags, wiki-link targets, warnings, and import results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FrontmatterKeySummary:
    """Summary of a frontmatter key across all scanned notes."""

    key: str
    count: int
    sample_values: list[str] = field(default_factory=list)  # up to 5 unique samples


@dataclass
class TagSummary:
    """Summary of a tag and its occurrence count."""

    tag: str
    count: int


@dataclass
class NoteTypeGroup:
    """A group of notes sharing a detected type."""

    type_name: str
    signal_source: str  # e.g. "frontmatter:type", "folder:Projects", "tag:meeting"
    count: int
    sample_notes: list[str] = field(default_factory=list)  # up to 10 sample paths
    frontmatter_keys: list[FrontmatterKeySummary] = field(default_factory=list)


@dataclass
class TypeMapping:
    """Maps an Obsidian note type group to an RDF type."""

    target_type_iri: str
    target_type_label: str


@dataclass
class PropertyMapping:
    """Maps a frontmatter key to an RDF property."""

    target_property_iri: str
    target_property_label: str
    source: str  # "shacl" or "custom"


@dataclass
class MappingConfig:
    """Complete mapping configuration for an Obsidian import."""

    version: int = 1
    type_mappings: dict[str, TypeMapping | None] = field(default_factory=dict)
    # key: "type_name|signal_source", value: TypeMapping or None (skip)
    property_mappings: dict[str, dict[str, PropertyMapping | None]] = field(default_factory=dict)
    # key: target_type_iri, value: {frontmatter_key: PropertyMapping or None}

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        type_map = {}
        for k, v in self.type_mappings.items():
            if v is None:
                type_map[k] = None
            else:
                type_map[k] = {
                    "target_type_iri": v.target_type_iri,
                    "target_type_label": v.target_type_label,
                }
        prop_map = {}
        for type_iri, fm_dict in self.property_mappings.items():
            prop_map[type_iri] = {}
            for fm_key, pm in fm_dict.items():
                if pm is None:
                    prop_map[type_iri][fm_key] = None
                else:
                    prop_map[type_iri][fm_key] = {
                        "target_property_iri": pm.target_property_iri,
                        "target_property_label": pm.target_property_label,
                        "source": pm.source,
                    }
        return {
            "version": self.version,
            "type_mappings": type_map,
            "property_mappings": prop_map,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> MappingConfig:
        """Deserialize from a dictionary (e.g. loaded from JSON)."""
        type_mappings: dict[str, TypeMapping | None] = {}
        for k, v in data.get("type_mappings", {}).items():
            if v is None:
                type_mappings[k] = None
            else:
                type_mappings[k] = TypeMapping(
                    target_type_iri=v["target_type_iri"],
                    target_type_label=v["target_type_label"],
                )
        property_mappings: dict[str, dict[str, PropertyMapping | None]] = {}
        for type_iri, fm_dict in data.get("property_mappings", {}).items():
            property_mappings[type_iri] = {}
            for fm_key, pm in fm_dict.items():
                if pm is None:
                    property_mappings[type_iri][fm_key] = None
                else:
                    property_mappings[type_iri][fm_key] = PropertyMapping(
                        target_property_iri=pm["target_property_iri"],
                        target_property_label=pm["target_property_label"],
                        source=pm["source"],
                    )
        return cls(
            version=data.get("version", 1),
            type_mappings=type_mappings,
            property_mappings=property_mappings,
        )


@dataclass
class ScanWarning:
    """A warning generated during vault scanning."""

    severity: str  # "warning" or "error"
    category: str  # broken_link, empty_note, malformed_frontmatter
    message: str
    file_path: str


@dataclass
class VaultScanResult:
    """Complete result of scanning an Obsidian vault."""

    vault_name: str
    import_id: str
    extract_path: str
    total_files: int
    markdown_files: int
    attachment_files: int
    other_files: int
    folders: int
    type_groups: list[NoteTypeGroup] = field(default_factory=list)
    frontmatter_keys: list[FrontmatterKeySummary] = field(default_factory=list)
    tags: list[TagSummary] = field(default_factory=list)
    wikilink_targets: list[dict[str, Any]] = field(default_factory=list)  # [{target, count}]
    warnings: list[ScanWarning] = field(default_factory=list)
    scan_duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "vault_name": self.vault_name,
            "import_id": self.import_id,
            "extract_path": self.extract_path,
            "total_files": self.total_files,
            "markdown_files": self.markdown_files,
            "attachment_files": self.attachment_files,
            "other_files": self.other_files,
            "folders": self.folders,
            "type_groups": [
                {
                    "type_name": g.type_name,
                    "signal_source": g.signal_source,
                    "count": g.count,
                    "sample_notes": g.sample_notes,
                    "frontmatter_keys": [
                        {"key": k.key, "count": k.count, "sample_values": k.sample_values}
                        for k in g.frontmatter_keys
                    ],
                }
                for g in self.type_groups
            ],
            "frontmatter_keys": [
                {"key": k.key, "count": k.count, "sample_values": k.sample_values}
                for k in self.frontmatter_keys
            ],
            "tags": [{"tag": t.tag, "count": t.count} for t in self.tags],
            "wikilink_targets": self.wikilink_targets,
            "warnings": [
                {
                    "severity": w.severity,
                    "category": w.category,
                    "message": w.message,
                    "file_path": w.file_path,
                }
                for w in self.warnings
            ],
            "scan_duration_seconds": self.scan_duration_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> VaultScanResult:
        """Deserialize from a dictionary (e.g. loaded from JSON)."""
        return cls(
            vault_name=data["vault_name"],
            import_id=data["import_id"],
            extract_path=data["extract_path"],
            total_files=data["total_files"],
            markdown_files=data["markdown_files"],
            attachment_files=data["attachment_files"],
            other_files=data["other_files"],
            folders=data["folders"],
            type_groups=[
                NoteTypeGroup(
                    type_name=g["type_name"],
                    signal_source=g["signal_source"],
                    count=g["count"],
                    sample_notes=g.get("sample_notes", []),
                    frontmatter_keys=[
                        FrontmatterKeySummary(
                            key=k["key"],
                            count=k["count"],
                            sample_values=k.get("sample_values", []),
                        )
                        for k in g.get("frontmatter_keys", [])
                    ],
                )
                for g in data.get("type_groups", [])
            ],
            frontmatter_keys=[
                FrontmatterKeySummary(
                    key=k["key"],
                    count=k["count"],
                    sample_values=k.get("sample_values", []),
                )
                for k in data.get("frontmatter_keys", [])
            ],
            tags=[
                TagSummary(tag=t["tag"], count=t["count"])
                for t in data.get("tags", [])
            ],
            wikilink_targets=data.get("wikilink_targets", []),
            warnings=[
                ScanWarning(
                    severity=w["severity"],
                    category=w["category"],
                    message=w["message"],
                    file_path=w["file_path"],
                )
                for w in data.get("warnings", [])
            ],
            scan_duration_seconds=data.get("scan_duration_seconds", 0.0),
        )


@dataclass
class ImportResult:
    """Result of an Obsidian vault import execution."""

    created: int = 0
    skipped_existing: int = 0
    skipped_errors: int = 0
    edges_created: int = 0
    unresolved_links: list[tuple[str, str]] = field(default_factory=list)  # (source_path, target_name)
    errors: list[tuple[str, str]] = field(default_factory=list)  # (path, error_message)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "created": self.created,
            "skipped_existing": self.skipped_existing,
            "skipped_errors": self.skipped_errors,
            "edges_created": self.edges_created,
            "unresolved_links": [{"source": s, "target": t} for s, t in self.unresolved_links],
            "errors": [{"path": p, "message": m} for p, m in self.errors],
            "duration_seconds": self.duration_seconds,
        }
