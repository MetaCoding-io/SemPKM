"""Data models for Notion workspace scan results and mapping configuration.

Dataclasses representing the structured output of scanning a Notion
workspace ZIP export: detected databases with CSV column schemas,
standalone markdown pages, cross-database relation candidates,
scan warnings, and aggregate statistics.

Also provides mapping configuration dataclasses for the import wizard:
TypeMapping, PropertyMapping, RelationMapping, and MappingConfig with
JSON serialization for persistence as mapping_config.json.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class NotionColumn:
    """A single column from a Notion database CSV with its inferred type."""

    name: str
    inferred_type: str  # text, select, multi_select, date, checkbox, url, number, relation
    sample_values: list[str] = field(default_factory=list)  # up to 5 unique non-empty samples
    non_empty_count: int = 0


@dataclass
class NotionDatabase:
    """A Notion database folder with its CSV schema and row data."""

    name: str
    folder_path: str
    csv_path: str
    columns: list[NotionColumn] = field(default_factory=list)
    row_count: int = 0
    row_titles: list[str] = field(default_factory=list)  # all first-column values (for relation detection)
    sample_rows: list[dict[str, str]] = field(default_factory=list)  # up to 5 sample dicts


@dataclass
class NotionPage:
    """A standalone markdown page (not inside a database folder)."""

    title: str
    file_path: str
    has_body: bool = False


@dataclass
class DetectedRelation:
    """A cross-database relation candidate detected by title overlap."""

    source_db_name: str
    source_column: str
    target_db_name: str
    match_ratio: float  # fraction of non-empty values matching target DB titles


@dataclass
class ScanWarning:
    """A warning generated during Notion export scanning."""

    severity: str  # "warning" or "error"
    category: str  # malformed_csv, empty_database, parse_error, etc.
    message: str
    file_path: str


@dataclass
class NotionScanResult:
    """Complete result of scanning a Notion workspace ZIP export."""

    workspace_name: str
    import_id: str
    extract_path: str
    databases: list[NotionDatabase] = field(default_factory=list)
    standalone_pages: list[NotionPage] = field(default_factory=list)
    detected_relations: list[DetectedRelation] = field(default_factory=list)
    warnings: list[ScanWarning] = field(default_factory=list)
    total_files: int = 0
    csv_files: int = 0
    markdown_files: int = 0
    scan_duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "workspace_name": self.workspace_name,
            "import_id": self.import_id,
            "extract_path": self.extract_path,
            "databases": [
                {
                    "name": db.name,
                    "folder_path": db.folder_path,
                    "csv_path": db.csv_path,
                    "columns": [
                        {
                            "name": col.name,
                            "inferred_type": col.inferred_type,
                            "sample_values": col.sample_values,
                            "non_empty_count": col.non_empty_count,
                        }
                        for col in db.columns
                    ],
                    "row_count": db.row_count,
                    "row_titles": db.row_titles,
                    "sample_rows": db.sample_rows,
                }
                for db in self.databases
            ],
            "standalone_pages": [
                {
                    "title": p.title,
                    "file_path": p.file_path,
                    "has_body": p.has_body,
                }
                for p in self.standalone_pages
            ],
            "detected_relations": [
                {
                    "source_db_name": r.source_db_name,
                    "source_column": r.source_column,
                    "target_db_name": r.target_db_name,
                    "match_ratio": r.match_ratio,
                }
                for r in self.detected_relations
            ],
            "warnings": [
                {
                    "severity": w.severity,
                    "category": w.category,
                    "message": w.message,
                    "file_path": w.file_path,
                }
                for w in self.warnings
            ],
            "total_files": self.total_files,
            "csv_files": self.csv_files,
            "markdown_files": self.markdown_files,
            "scan_duration_seconds": self.scan_duration_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> NotionScanResult:
        """Deserialize from a dictionary (e.g. loaded from JSON)."""
        return cls(
            workspace_name=data["workspace_name"],
            import_id=data["import_id"],
            extract_path=data["extract_path"],
            databases=[
                NotionDatabase(
                    name=db["name"],
                    folder_path=db["folder_path"],
                    csv_path=db["csv_path"],
                    columns=[
                        NotionColumn(
                            name=col["name"],
                            inferred_type=col["inferred_type"],
                            sample_values=col.get("sample_values", []),
                            non_empty_count=col.get("non_empty_count", 0),
                        )
                        for col in db.get("columns", [])
                    ],
                    row_count=db.get("row_count", 0),
                    row_titles=db.get("row_titles", []),
                    sample_rows=db.get("sample_rows", []),
                )
                for db in data.get("databases", [])
            ],
            standalone_pages=[
                NotionPage(
                    title=p["title"],
                    file_path=p["file_path"],
                    has_body=p.get("has_body", False),
                )
                for p in data.get("standalone_pages", [])
            ],
            detected_relations=[
                DetectedRelation(
                    source_db_name=r["source_db_name"],
                    source_column=r["source_column"],
                    target_db_name=r["target_db_name"],
                    match_ratio=r["match_ratio"],
                )
                for r in data.get("detected_relations", [])
            ],
            warnings=[
                ScanWarning(
                    severity=w["severity"],
                    category=w["category"],
                    message=w["message"],
                    file_path=w["file_path"],
                )
                for w in data.get("warnings", [])
            ],
            total_files=data.get("total_files", 0),
            csv_files=data.get("csv_files", 0),
            markdown_files=data.get("markdown_files", 0),
            scan_duration_seconds=data.get("scan_duration_seconds", 0.0),
        )


# ---------------------------------------------------------------------------
# Mapping configuration dataclasses (import wizard steps 3–6)
# ---------------------------------------------------------------------------


@dataclass
class TypeMapping:
    """Maps a Notion database to an RDF type."""

    target_type_iri: str
    target_type_label: str


@dataclass
class PropertyMapping:
    """Maps a Notion CSV column to an RDF property."""

    target_property_iri: str
    target_property_label: str
    source: str  # "shacl" or "custom"


@dataclass
class RelationMapping:
    """Maps a detected cross-database relation to an RDF edge predicate."""

    target_predicate_iri: str
    target_predicate_label: str
    target_type_iri: str
    target_type_label: str


@dataclass
class MappingConfig:
    """Complete mapping configuration for a Notion import.

    Persisted as ``mapping_config.json`` in the import directory and
    updated incrementally by the auto-save POST endpoints during each
    wizard step.
    """

    version: int = 1
    # key: database name → TypeMapping or None (skip)
    type_mappings: dict[str, TypeMapping | None] = field(default_factory=dict)
    # outer key: target_type_iri, inner key: column_name → PropertyMapping or None
    property_mappings: dict[str, dict[str, PropertyMapping | None]] = field(
        default_factory=dict
    )
    # key: "source_db|source_column" → RelationMapping or None (skip)
    relation_mappings: dict[str, RelationMapping | None] = field(default_factory=dict)
    standalone_page_type_iri: str | None = None
    standalone_page_type_label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        type_map: dict[str, Any] = {}
        for k, v in self.type_mappings.items():
            if v is None:
                type_map[k] = None
            else:
                type_map[k] = {
                    "target_type_iri": v.target_type_iri,
                    "target_type_label": v.target_type_label,
                }

        prop_map: dict[str, dict[str, Any]] = {}
        for type_iri, col_dict in self.property_mappings.items():
            prop_map[type_iri] = {}
            for col_name, pm in col_dict.items():
                if pm is None:
                    prop_map[type_iri][col_name] = None
                else:
                    prop_map[type_iri][col_name] = {
                        "target_property_iri": pm.target_property_iri,
                        "target_property_label": pm.target_property_label,
                        "source": pm.source,
                    }

        rel_map: dict[str, Any] = {}
        for k, v in self.relation_mappings.items():
            if v is None:
                rel_map[k] = None
            else:
                rel_map[k] = {
                    "target_predicate_iri": v.target_predicate_iri,
                    "target_predicate_label": v.target_predicate_label,
                    "target_type_iri": v.target_type_iri,
                    "target_type_label": v.target_type_label,
                }

        return {
            "version": self.version,
            "type_mappings": type_map,
            "property_mappings": prop_map,
            "relation_mappings": rel_map,
            "standalone_page_type_iri": self.standalone_page_type_iri,
            "standalone_page_type_label": self.standalone_page_type_label,
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
        for type_iri, col_dict in data.get("property_mappings", {}).items():
            property_mappings[type_iri] = {}
            for col_name, pm in col_dict.items():
                if pm is None:
                    property_mappings[type_iri][col_name] = None
                else:
                    property_mappings[type_iri][col_name] = PropertyMapping(
                        target_property_iri=pm["target_property_iri"],
                        target_property_label=pm["target_property_label"],
                        source=pm["source"],
                    )

        relation_mappings: dict[str, RelationMapping | None] = {}
        for k, v in data.get("relation_mappings", {}).items():
            if v is None:
                relation_mappings[k] = None
            else:
                relation_mappings[k] = RelationMapping(
                    target_predicate_iri=v["target_predicate_iri"],
                    target_predicate_label=v["target_predicate_label"],
                    target_type_iri=v["target_type_iri"],
                    target_type_label=v["target_type_label"],
                )

        return cls(
            version=data.get("version", 1),
            type_mappings=type_mappings,
            property_mappings=property_mappings,
            relation_mappings=relation_mappings,
            standalone_page_type_iri=data.get("standalone_page_type_iri"),
            standalone_page_type_label=data.get("standalone_page_type_label"),
        )


@dataclass
class ImportResult:
    """Result of a Notion workspace import execution."""

    created: int = 0
    skipped: int = 0
    edges_created: int = 0
    unresolved_relations: list[tuple[str, str]] = field(default_factory=list)
    errors: list[tuple[str, str]] = field(default_factory=list)
    duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dictionary."""
        return {
            "created": self.created,
            "skipped": self.skipped,
            "edges_created": self.edges_created,
            "unresolved_relations": [
                {"source": s, "target": t} for s, t in self.unresolved_relations
            ],
            "errors": [{"path": p, "message": m} for p, m in self.errors],
            "duration_seconds": self.duration_seconds,
        }
