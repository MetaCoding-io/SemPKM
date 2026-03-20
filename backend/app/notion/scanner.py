"""Notion workspace ZIP scanner.

Scans an extracted Notion workspace directory, parsing CSV files for
database schemas and row data, detecting standalone markdown pages,
inferring column types, and identifying cross-database relations.

Follows the VaultScanner pattern from the Obsidian importer: an async
scan() method delegates to _do_scan() on a background thread via
asyncio.to_thread.
"""

import asyncio
import csv
import logging
import os
import re
import time
from pathlib import Path
from typing import Any

from .broadcast import ScanBroadcast, SSEEvent
from .models import (
    DetectedRelation,
    NotionColumn,
    NotionDatabase,
    NotionPage,
    NotionScanResult,
    ScanWarning,
)

logger = logging.getLogger(__name__)

# Regex: strip a 32-character lowercase hex Notion ID from end of a name,
# preceded by one or more whitespace characters.
_NOTION_ID_RE = re.compile(r"\s+[0-9a-f]{32}$")

# URL pattern for column type inference
_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _strip_notion_id(name: str) -> str:
    """Strip the trailing 32-hex-char Notion ID from a name.

    Notion appends ` <32 hex chars>` to every filename and folder name.
    Only strips exactly 32 hex characters preceded by whitespace.

    >>> _strip_notion_id("My Database abc123def456abc123def456abc1")
    'My Database'
    >>> _strip_notion_id("Short abc123")
    'Short abc123'
    """
    return _NOTION_ID_RE.sub("", name)


def _infer_column_type(values: list[str]) -> str:
    """Infer the column type from a list of cell values.

    Returns one of: text, select, multi_select, date, checkbox, url, number.
    The "relation" type is assigned later during cross-DB detection.

    Type precedence (checked in order on non-empty values):
    1. checkbox — all values are "Yes" or "No"
    2. url — all values start with http:// or https://
    3. number — all values parseable as float
    4. date — all values parseable by dateutil.parser.parse()
    5. multi_select — comma-separated with few unique components
    6. select — ≤20 unique values
    7. text — default fallback
    """
    non_empty = [v for v in values if v.strip()]
    if not non_empty:
        return "text"

    # 1. Checkbox: all "Yes" or "No"
    checkbox_vals = {"yes", "no"}
    if all(v.strip().lower() in checkbox_vals for v in non_empty):
        return "checkbox"

    # 2. URL: all start with http:// or https://
    if all(_URL_RE.match(v.strip()) for v in non_empty):
        return "url"

    # 3. Number: all parseable as float
    all_number = True
    for v in non_empty:
        try:
            float(v.strip())
        except (ValueError, OverflowError):
            all_number = False
            break
    if all_number:
        return "number"

    # 4. Date: all parseable via dateutil
    try:
        from dateutil.parser import parse as _parse_date, ParserError

        all_date = True
        for v in non_empty:
            try:
                _parse_date(v.strip())
            except (ParserError, ValueError, OverflowError):
                all_date = False
                break
        if all_date:
            return "date"
    except ImportError:
        # dateutil not available — skip date detection
        pass

    # 5. Multi-select: comma-separated with few unique components relative
    #    to unique cell count.  Conservative: at least 2 cells must contain
    #    commas, and unique components < 2× unique cell count.
    cells_with_commas = [v for v in non_empty if "," in v]
    if len(cells_with_commas) >= 2:
        components: set[str] = set()
        for v in non_empty:
            for part in v.split(","):
                part = part.strip()
                if part:
                    components.add(part.lower())
        unique_cells = len(set(v.strip().lower() for v in non_empty))
        if components and len(components) < 2 * unique_cells and len(components) <= 30:
            return "multi_select"

    # 6. Select: ≤20 unique non-empty values
    unique = set(v.strip() for v in non_empty)
    if len(unique) <= 20:
        return "select"

    # 7. Default: text
    return "text"


class NotionScanner:
    """Scans an extracted Notion workspace and produces a NotionScanResult."""

    def __init__(
        self, extract_path: Path, import_id: str, broadcast: ScanBroadcast
    ) -> None:
        self.extract_path = extract_path
        self.import_id = import_id
        self.broadcast = broadcast

    async def scan(self) -> NotionScanResult:
        """Run the scan in a background thread to avoid blocking the event loop."""
        return await asyncio.to_thread(self._do_scan)

    def _do_scan(self) -> NotionScanResult:
        """Synchronous scan logic — called from a background thread."""
        start = time.monotonic()

        workspace_root = self._detect_workspace_root()
        workspace_name = workspace_root.name

        warnings: list[ScanWarning] = []

        # ── Phase 1: Walk directory tree, classify files ──────────────
        all_files: list[Path] = []
        for dirpath, dirnames, filenames in os.walk(workspace_root):
            dp = Path(dirpath)
            # Skip macOS junk and hidden dirs
            dirnames[:] = [
                d for d in dirnames if not d.startswith(".") and d != "__MACOSX"
            ]
            for fn in filenames:
                if not fn.startswith("."):
                    all_files.append(dp / fn)

        total_files = len(all_files)
        csv_files: list[Path] = []
        md_files: list[Path] = []
        for f in all_files:
            ext = f.suffix.lower()
            if ext == ".csv":
                csv_files.append(f)
            elif ext == ".md":
                md_files.append(f)

        # ── Phase 2: Detect database folders ──────────────────────────
        # A database folder contains a CSV whose stem (after ID stripping)
        # matches the folder name (after ID stripping).
        databases: list[NotionDatabase] = []
        db_folder_paths: set[str] = set()  # track which folders are databases

        for csv_path in csv_files:
            csv_stem_clean = _strip_notion_id(csv_path.stem)
            folder = csv_path.parent
            folder_name_clean = _strip_notion_id(folder.name)

            if csv_stem_clean.lower() == folder_name_clean.lower() and folder != workspace_root:
                db = self._parse_database(
                    csv_path, folder, csv_stem_clean, workspace_root, warnings
                )
                if db is not None:
                    databases.append(db)
                    db_folder_paths.add(str(folder.resolve()))

        # Broadcast progress
        self.broadcast.publish(
            SSEEvent(
                event="scan_progress",
                data={
                    "scanned": len(csv_files),
                    "total": total_files,
                    "current_file": "Detecting databases...",
                },
            )
        )

        # ── Phase 3: Detect standalone pages ──────────────────────────
        standalone_pages: list[NotionPage] = []
        for md_file in md_files:
            # A page is standalone if it's NOT inside a database folder
            md_dir = str(md_file.parent.resolve())
            inside_db = any(md_dir.startswith(dbfp) for dbfp in db_folder_paths)
            if not inside_db:
                title = _strip_notion_id(md_file.stem)
                try:
                    body = md_file.read_text(encoding="utf-8", errors="replace").strip()
                    has_body = len(body) > 0
                except Exception:
                    has_body = False
                rel_path = str(md_file.relative_to(workspace_root))
                standalone_pages.append(
                    NotionPage(title=title, file_path=rel_path, has_body=has_body)
                )

        # Broadcast progress
        self.broadcast.publish(
            SSEEvent(
                event="scan_progress",
                data={
                    "scanned": len(csv_files) + len(md_files),
                    "total": total_files,
                    "current_file": "Detecting relations...",
                },
            )
        )

        # ── Phase 4: Cross-DB relation detection ──────────────────────
        detected_relations = self._detect_relations(databases)

        duration = time.monotonic() - start

        # Broadcast completion
        self.broadcast.publish(
            SSEEvent(
                event="scan_complete",
                data={"import_id": self.import_id},
            )
        )

        return NotionScanResult(
            workspace_name=workspace_name,
            import_id=self.import_id,
            extract_path=str(self.extract_path),
            databases=databases,
            standalone_pages=standalone_pages,
            detected_relations=detected_relations,
            warnings=warnings,
            total_files=total_files,
            csv_files=len(csv_files),
            markdown_files=len(md_files),
            scan_duration_seconds=round(duration, 2),
        )

    def _detect_workspace_root(self) -> Path:
        """Auto-detect workspace root directory.

        If the extracted ZIP has a single top-level directory, use it as
        the workspace root. Otherwise use extract_path directly.
        """
        entries = list(self.extract_path.iterdir())
        visible = [
            e
            for e in entries
            if not e.name.startswith(".") and e.name != "__MACOSX"
        ]
        if len(visible) == 1 and visible[0].is_dir():
            return visible[0]
        return self.extract_path

    def _parse_database(
        self,
        csv_path: Path,
        folder: Path,
        db_name: str,
        workspace_root: Path,
        warnings: list[ScanWarning],
    ) -> NotionDatabase | None:
        """Parse a single database CSV and return a NotionDatabase.

        Returns None if the CSV cannot be read at all.
        """
        rel_folder = str(folder.relative_to(workspace_root))
        rel_csv = str(csv_path.relative_to(workspace_root))

        try:
            text = csv_path.read_text(encoding="utf-8-sig", errors="replace")
        except Exception as exc:
            warnings.append(
                ScanWarning(
                    severity="error",
                    category="malformed_csv",
                    message=f"Cannot read CSV: {exc}",
                    file_path=rel_csv,
                )
            )
            return None

        try:
            reader = csv.DictReader(text.splitlines())
            fieldnames = reader.fieldnames
            if not fieldnames:
                warnings.append(
                    ScanWarning(
                        severity="warning",
                        category="empty_database",
                        message="CSV has no columns (empty header row)",
                        file_path=rel_csv,
                    )
                )
                return NotionDatabase(
                    name=db_name,
                    folder_path=rel_folder,
                    csv_path=rel_csv,
                    columns=[],
                    row_count=0,
                    row_titles=[],
                    sample_rows=[],
                )

            rows: list[dict[str, str]] = []
            for row in reader:
                rows.append(row)

        except Exception as exc:
            warnings.append(
                ScanWarning(
                    severity="error",
                    category="malformed_csv",
                    message=f"Error parsing CSV: {exc}",
                    file_path=rel_csv,
                )
            )
            return None

        if not rows:
            warnings.append(
                ScanWarning(
                    severity="warning",
                    category="empty_database",
                    message="CSV has headers but no data rows",
                    file_path=rel_csv,
                )
            )

        # Collect column values
        col_values: dict[str, list[str]] = {col: [] for col in fieldnames}
        for row in rows:
            for col in fieldnames:
                col_values[col].append(row.get(col, ""))

        # Row titles = values in the first column
        first_col = fieldnames[0]
        row_titles = [v for v in col_values[first_col] if v.strip()]

        # Infer column types
        columns: list[NotionColumn] = []
        for col_name in fieldnames:
            vals = col_values[col_name]
            inferred_type = _infer_column_type(vals)
            non_empty = [v for v in vals if v.strip()]
            samples = list(dict.fromkeys(non_empty))[:5]  # unique, preserving order
            columns.append(
                NotionColumn(
                    name=col_name,
                    inferred_type=inferred_type,
                    sample_values=samples,
                    non_empty_count=len(non_empty),
                )
            )

        # Sample rows (up to 5)
        sample_rows = rows[:5]

        db = NotionDatabase(
            name=db_name,
            folder_path=rel_folder,
            csv_path=rel_csv,
            columns=columns,
            row_count=len(rows),
            row_titles=row_titles,
            sample_rows=sample_rows,
        )
        # Stash all column values as a transient attribute for relation
        # detection.  Not serialized — only used during the scan.
        db._all_column_values = col_values  # type: ignore[attr-defined]
        return db

    def _detect_relations(
        self, databases: list[NotionDatabase]
    ) -> list[DetectedRelation]:
        """Detect cross-database relations by title overlap.

        For each text-typed column in each database, check if >80% of its
        non-empty values match titles in another database's row_titles.
        If so, emit a DetectedRelation and upgrade the column type to
        "relation".
        """
        if len(databases) < 2:
            return []

        # Build title sets per database (case-insensitive for matching)
        db_title_sets: dict[str, set[str]] = {}
        for db in databases:
            db_title_sets[db.name] = {t.strip().lower() for t in db.row_titles if t.strip()}

        relations: list[DetectedRelation] = []

        for db in databases:
            for col in db.columns:
                if col.inferred_type not in ("text", "select"):
                    continue

                non_empty_vals = [
                    v.strip() for v in _get_column_values(db, col.name) if v.strip()
                ]
                if not non_empty_vals:
                    continue

                # Check against every other database
                for target_db in databases:
                    if target_db.name == db.name:
                        continue

                    target_titles = db_title_sets.get(target_db.name, set())
                    if not target_titles:
                        continue

                    matches = sum(
                        1 for v in non_empty_vals if v.lower() in target_titles
                    )
                    ratio = matches / len(non_empty_vals)

                    if ratio > 0.80:
                        col.inferred_type = "relation"
                        relations.append(
                            DetectedRelation(
                                source_db_name=db.name,
                                source_column=col.name,
                                target_db_name=target_db.name,
                                match_ratio=round(ratio, 2),
                            )
                        )
                        break  # once we find a relation target, stop checking others

        return relations


def _get_column_values(db: NotionDatabase, col_name: str) -> list[str]:
    """Extract all values for a column from the database's sample_rows.

    Since we store up to 5 sample rows but need ALL rows for relation
    detection, we reconstruct from row_titles for the first column.
    For other columns we rely on sample_rows — but relation detection
    really needs all values.

    The proper approach: store all column values during parsing.
    We use a simple workaround: the scanner stores values in a transient
    attribute during scanning. For the public API (after from_dict()),
    we fall back to sample_rows.
    """
    # Check for transient _all_column_values (set during scan)
    all_vals = getattr(db, "_all_column_values", None)
    if all_vals and col_name in all_vals:
        return all_vals[col_name]

    # Fallback: extract from sample_rows (limited)
    return [row.get(col_name, "") for row in db.sample_rows]
