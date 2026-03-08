"""Data models for Obsidian vault scan results.

Dataclasses representing the structured output of a vault scan:
file counts, detected note types, frontmatter keys, tags, wiki-link
targets, and warnings.
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
