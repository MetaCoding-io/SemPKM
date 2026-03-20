"""Data models for Notion workspace scan results.

Dataclasses representing the structured output of scanning a Notion
workspace ZIP export: detected databases with CSV column schemas,
standalone markdown pages, cross-database relation candidates,
scan warnings, and aggregate statistics.
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
