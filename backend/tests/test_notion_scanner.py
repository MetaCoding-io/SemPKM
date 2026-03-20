"""Tests for the Notion workspace ZIP scanner.

Covers CSV parsing, Notion ID stripping, column type inference,
cross-database relation detection, standalone page detection,
BOM handling, malformed CSV resilience, and result serialization.
"""

import asyncio
import csv
import io
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from app.notion.models import (
    DetectedRelation,
    NotionColumn,
    NotionDatabase,
    NotionPage,
    NotionScanResult,
    ScanWarning,
)
from app.notion.scanner import NotionScanner, _infer_column_type, _strip_notion_id


# ────────────────────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────────────────────


def _make_broadcast() -> MagicMock:
    """Return a mock ScanBroadcast that silently accepts publish() calls."""
    bc = MagicMock()
    bc.publish = MagicMock()
    return bc


def _create_notion_export(
    tmp_path: Path,
    databases: dict[str, list[dict[str, str]]] | None = None,
    standalone_pages: dict[str, str] | None = None,
    workspace_name: str = "My Workspace abc123abc123abc123abc123abc123ab",
    nested: bool = True,
    bom: bool = False,
) -> Path:
    """Build a synthetic Notion export directory structure.

    Args:
        tmp_path: pytest tmp_path fixture
        databases: {folder_name: [row_dicts]}  — folder_name includes Notion ID
        standalone_pages: {filename: body_content}
        workspace_name: top-level folder name (with Notion ID)
        nested: if True, wrap everything in a workspace_name top-level dir
        bom: if True, write CSV files with UTF-8 BOM
    """
    root = tmp_path / workspace_name if nested else tmp_path
    root.mkdir(parents=True, exist_ok=True)

    if databases:
        for folder_name, rows in databases.items():
            db_dir = root / folder_name
            db_dir.mkdir(parents=True, exist_ok=True)

            # CSV file with same stem as folder
            csv_path = db_dir / f"{folder_name}.csv"
            if rows:
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=list(rows[0].keys()))
                writer.writeheader()
                writer.writerows(rows)
                csv_text = output.getvalue()
            else:
                csv_text = ""

            if bom:
                csv_path.write_bytes(b"\xef\xbb\xbf" + csv_text.encode("utf-8"))
            else:
                csv_path.write_text(csv_text, encoding="utf-8")

            # Markdown body files for each row (using first column as title)
            if rows:
                first_col = list(rows[0].keys())[0]
                for row in rows:
                    title = row[first_col]
                    if title:
                        md_name = f"{title} aabbccddaabbccddaabbccddaabbccdd.md"
                        (db_dir / md_name).write_text(
                            f"# {title}\n\nBody content for {title}.",
                            encoding="utf-8",
                        )

    if standalone_pages:
        for filename, body in standalone_pages.items():
            (root / filename).write_text(body, encoding="utf-8")

    return tmp_path


def _run_scan(tmp_path: Path, import_id: str = "test-import") -> NotionScanResult:
    """Run a synchronous scan on a tmp_path Notion export."""
    bc = _make_broadcast()
    scanner = NotionScanner(tmp_path, import_id, bc)
    return asyncio.run(scanner.scan())


# ────────────────────────────────────────────────────────────────
#  ID Stripping
# ────────────────────────────────────────────────────────────────


def test_strip_notion_id_32_hex():
    """Strips exactly 32 hex chars preceded by whitespace."""
    assert _strip_notion_id("Projects abc123abc123abc123abc123abc123ab") == "Projects"


def test_strip_notion_id_short_hex_preserved():
    """Does NOT strip fewer than 32 hex chars."""
    assert _strip_notion_id("Projects abc123") == "Projects abc123"


def test_strip_notion_id_no_space_prefix():
    """Does NOT strip if hex chars are not preceded by whitespace."""
    name = "Projectsabc123abc123abc123abc123abc123ab"
    assert _strip_notion_id(name) == name


def test_strip_notion_id_no_hex():
    """Returns name unchanged when no hex suffix is present."""
    assert _strip_notion_id("Just A Name") == "Just A Name"


def test_strip_notion_id_multiple_spaces():
    """Strips ID even with multiple spaces before the hex."""
    assert _strip_notion_id("My Page  abc123abc123abc123abc123abc123ab") == "My Page"


# ────────────────────────────────────────────────────────────────
#  Column Type Inference
# ────────────────────────────────────────────────────────────────


def test_infer_type_checkbox():
    assert _infer_column_type(["Yes", "No", "Yes", "No"]) == "checkbox"


def test_infer_type_checkbox_case_insensitive():
    assert _infer_column_type(["yes", "NO", "Yes"]) == "checkbox"


def test_infer_type_url():
    assert _infer_column_type(["https://example.com", "http://foo.bar"]) == "url"


def test_infer_type_number():
    assert _infer_column_type(["1.5", "42", "-3.14", "0"]) == "number"


def test_infer_type_date():
    assert _infer_column_type(["2024-01-15", "2024-06-30", "2023-12-25"]) == "date"


def test_infer_type_select():
    """≤20 unique values → select."""
    vals = ["Red", "Blue", "Green", "Red", "Blue"]
    assert _infer_column_type(vals) == "select"


def test_infer_type_multi_select():
    """Comma-separated values with few unique components → multi_select."""
    vals = ["Tag1, Tag2", "Tag2, Tag3", "Tag1, Tag3", "Tag1, Tag2, Tag3"]
    assert _infer_column_type(vals) == "multi_select"


def test_infer_type_text_default():
    """Varied long content defaults to text."""
    vals = [f"Paragraph {i} of unique content about topic {i * 7}" for i in range(50)]
    assert _infer_column_type(vals) == "text"


def test_infer_type_empty_values():
    """All empty values → text."""
    assert _infer_column_type(["", "", ""]) == "text"


def test_infer_type_mixed_empty():
    """Mostly empty with some checkbox values → infers from non-empty."""
    vals = ["", "", "Yes", "No", ""]
    assert _infer_column_type(vals) == "checkbox"


# ────────────────────────────────────────────────────────────────
#  Full Scan Tests
# ────────────────────────────────────────────────────────────────


def test_scan_single_database(tmp_path):
    """One CSV database with 3 rows, correct column detection."""
    _create_notion_export(
        tmp_path,
        databases={
            "Tasks abc123abc123abc123abc123abc123ab": [
                {"Name": "Buy milk", "Status": "Done", "Priority": "High"},
                {"Name": "Write code", "Status": "In Progress", "Priority": "Medium"},
                {"Name": "Read book", "Status": "Done", "Priority": "Low"},
            ]
        },
    )
    result = _run_scan(tmp_path)
    assert len(result.databases) == 1
    db = result.databases[0]
    assert db.name == "Tasks"
    assert db.row_count == 3
    assert len(db.columns) == 3
    # Status has 2 unique values → select
    status_col = next(c for c in db.columns if c.name == "Status")
    assert status_col.inferred_type == "select"


def test_scan_standalone_pages(tmp_path):
    """Markdown files outside database folders are detected as standalone."""
    _create_notion_export(
        tmp_path,
        databases={
            "Tasks abc123abc123abc123abc123abc123ab": [
                {"Name": "Task 1", "Status": "Done"},
            ]
        },
        standalone_pages={
            "Meeting Notes aabbccddaabbccddaabbccddaabbccdd.md": "# Meeting\nNotes here.",
            "Quick Thought 11223344112233441122334411223344.md": "Just a thought.",
        },
    )
    result = _run_scan(tmp_path)
    assert len(result.standalone_pages) == 2
    titles = {p.title for p in result.standalone_pages}
    assert "Meeting Notes" in titles
    assert "Quick Thought" in titles
    assert all(p.has_body for p in result.standalone_pages)


def test_scan_cross_db_relation(tmp_path):
    """Column values matching another DB's titles → DetectedRelation."""
    _create_notion_export(
        tmp_path,
        databases={
            "Tasks abc123abc123abc123abc123abc123ab": [
                {"Name": "Task 1", "Assignee": "Alice"},
                {"Name": "Task 2", "Assignee": "Bob"},
                {"Name": "Task 3", "Assignee": "Alice"},
                {"Name": "Task 4", "Assignee": "Charlie"},
                {"Name": "Task 5", "Assignee": "Bob"},
            ],
            "People abc123abc123abc123abc123abc123cd": [
                {"Name": "Alice", "Role": "Engineer"},
                {"Name": "Bob", "Role": "Designer"},
                {"Name": "Charlie", "Role": "PM"},
            ],
        },
    )
    result = _run_scan(tmp_path)
    assert len(result.detected_relations) >= 1
    rel = result.detected_relations[0]
    assert rel.source_column == "Assignee"
    assert rel.target_db_name == "People"
    assert rel.match_ratio >= 0.80

    # The Assignee column type should be upgraded to "relation"
    tasks_db = next(db for db in result.databases if db.name == "Tasks")
    assignee_col = next(c for c in tasks_db.columns if c.name == "Assignee")
    assert assignee_col.inferred_type == "relation"


def test_scan_relation_below_threshold(tmp_path):
    """<80% match → not detected as relation."""
    _create_notion_export(
        tmp_path,
        databases={
            "Tasks abc123abc123abc123abc123abc123ab": [
                {"Name": "Task 1", "Category": "Alpha"},
                {"Name": "Task 2", "Category": "Beta"},
                {"Name": "Task 3", "Category": "Gamma"},
                {"Name": "Task 4", "Category": "Unrelated1"},
                {"Name": "Task 5", "Category": "Unrelated2"},
                {"Name": "Task 6", "Category": "Unrelated3"},
                {"Name": "Task 7", "Category": "Unrelated4"},
                {"Name": "Task 8", "Category": "Unrelated5"},
                {"Name": "Task 9", "Category": "Unrelated6"},
                {"Name": "Task 10", "Category": "Unrelated7"},
            ],
            "Categories abc123abc123abc123abc123abc123cd": [
                {"Name": "Alpha", "Desc": "A"},
                {"Name": "Beta", "Desc": "B"},
                {"Name": "Gamma", "Desc": "C"},
            ],
        },
    )
    result = _run_scan(tmp_path)
    # Only 3/10 match → 30% < 80% threshold
    category_rels = [r for r in result.detected_relations if r.source_column == "Category"]
    assert len(category_rels) == 0


def test_scan_bom_csv(tmp_path):
    """UTF-8 BOM in CSV file is handled correctly."""
    _create_notion_export(
        tmp_path,
        databases={
            "Notes abc123abc123abc123abc123abc123ab": [
                {"Title": "Note 1", "Tags": "important"},
                {"Title": "Note 2", "Tags": "draft"},
            ]
        },
        bom=True,
    )
    result = _run_scan(tmp_path)
    assert len(result.databases) == 1
    db = result.databases[0]
    # BOM should not corrupt the first column name
    assert db.columns[0].name == "Title"
    assert db.row_count == 2


def test_scan_nested_workspace_root(tmp_path):
    """Single top-level dir is detected as workspace root."""
    _create_notion_export(
        tmp_path,
        databases={
            "Tasks abc123abc123abc123abc123abc123ab": [
                {"Name": "Task 1"},
            ]
        },
        workspace_name="Export abc123abc123abc123abc123abc123ab",
        nested=True,
    )
    result = _run_scan(tmp_path)
    assert result.workspace_name == "Export abc123abc123abc123abc123abc123ab"
    assert len(result.databases) == 1


def test_scan_result_round_trip(tmp_path):
    """to_dict() / from_dict() round-trips all fields."""
    _create_notion_export(
        tmp_path,
        databases={
            "Tasks abc123abc123abc123abc123abc123ab": [
                {"Name": "Task 1", "Status": "Done"},
            ]
        },
        standalone_pages={
            "Page aabbccddaabbccddaabbccddaabbccdd.md": "Content.",
        },
    )
    result = _run_scan(tmp_path)

    d = result.to_dict()
    restored = NotionScanResult.from_dict(d)

    assert restored.workspace_name == result.workspace_name
    assert restored.import_id == result.import_id
    assert len(restored.databases) == len(result.databases)
    assert restored.databases[0].name == result.databases[0].name
    assert restored.databases[0].row_count == result.databases[0].row_count
    assert len(restored.standalone_pages) == len(result.standalone_pages)
    assert restored.total_files == result.total_files
    assert restored.csv_files == result.csv_files
    assert restored.markdown_files == result.markdown_files
    assert restored.scan_duration_seconds == result.scan_duration_seconds


def test_scan_warning_malformed_csv(tmp_path):
    """Malformed CSV produces a warning, doesn't crash the scanner."""
    ws = tmp_path / "Workspace abc123abc123abc123abc123abc123ab"
    ws.mkdir()
    db_dir = ws / "Bad abc123abc123abc123abc123abc123ab"
    db_dir.mkdir()
    csv_path = db_dir / "Bad abc123abc123abc123abc123abc123ab.csv"
    # Write binary garbage
    csv_path.write_bytes(b"\x00\x01\x02\xff\xfe")

    result = _run_scan(tmp_path)
    # Should not crash — either parsed with errors or produced a warning
    # The scanner should still complete
    assert result.workspace_name is not None


def test_scan_multiple_databases(tmp_path):
    """Two databases are scanned with correct aggregate stats."""
    _create_notion_export(
        tmp_path,
        databases={
            "Tasks abc123abc123abc123abc123abc123ab": [
                {"Name": "Task 1", "Status": "Done"},
                {"Name": "Task 2", "Status": "Open"},
            ],
            "People abc123abc123abc123abc123abc123cd": [
                {"Name": "Alice", "Role": "Engineer"},
                {"Name": "Bob", "Role": "Designer"},
                {"Name": "Charlie", "Role": "PM"},
            ],
        },
    )
    result = _run_scan(tmp_path)
    assert len(result.databases) == 2
    names = {db.name for db in result.databases}
    assert names == {"Tasks", "People"}
    assert result.csv_files == 2


def test_scan_empty_database(tmp_path):
    """Database with header-only CSV gets a warning but doesn't crash."""
    ws = tmp_path / "WS abc123abc123abc123abc123abc123ab"
    ws.mkdir()
    db_dir = ws / "Empty abc123abc123abc123abc123abc123ab"
    db_dir.mkdir()
    csv_path = db_dir / "Empty abc123abc123abc123abc123abc123ab.csv"
    csv_path.write_text("Name,Status\n", encoding="utf-8")

    result = _run_scan(tmp_path)
    assert len(result.databases) == 1
    assert result.databases[0].row_count == 0
    # Should have a warning about empty database
    empty_warnings = [w for w in result.warnings if w.category == "empty_database"]
    assert len(empty_warnings) == 1


def test_scan_database_folder_not_at_root(tmp_path):
    """Database folder nested inside another folder is still detected."""
    ws = tmp_path / "WS abc123abc123abc123abc123abc123ab"
    ws.mkdir()
    # Nest a database inside a subfolder
    sub = ws / "Area"
    sub.mkdir()
    db_dir = sub / "Tasks abc123abc123abc123abc123abc123ab"
    db_dir.mkdir()
    csv_path = db_dir / "Tasks abc123abc123abc123abc123abc123ab.csv"
    csv_path.write_text("Name,Status\nTask 1,Done\n", encoding="utf-8")

    result = _run_scan(tmp_path)
    assert len(result.databases) == 1
    assert result.databases[0].name == "Tasks"


def test_infer_type_number_with_negatives():
    """Negative numbers and decimals are detected as number."""
    assert _infer_column_type(["-1.5", "0", "3.14", "-100"]) == "number"


def test_infer_type_url_mixed_schemes():
    """Both http and https are detected as url."""
    assert _infer_column_type(["http://a.com", "https://b.org"]) == "url"


def test_scan_broadcast_events(tmp_path):
    """Scanner publishes scan_progress and scan_complete events."""
    _create_notion_export(
        tmp_path,
        databases={
            "Tasks abc123abc123abc123abc123abc123ab": [
                {"Name": "Task 1"},
            ]
        },
    )
    bc = _make_broadcast()
    scanner = NotionScanner(tmp_path, "test-id", bc)
    asyncio.run(scanner.scan())

    events = [call.args[0].event for call in bc.publish.call_args_list]
    assert "scan_progress" in events
    assert "scan_complete" in events


def test_scan_standalone_page_no_body(tmp_path):
    """Standalone page with empty content has has_body=False."""
    _create_notion_export(
        tmp_path,
        standalone_pages={
            "Empty aabbccddaabbccddaabbccddaabbccdd.md": "",
        },
    )
    result = _run_scan(tmp_path)
    assert len(result.standalone_pages) == 1
    assert result.standalone_pages[0].has_body is False


def test_scan_md_inside_db_not_standalone(tmp_path):
    """Markdown files inside a database folder are NOT standalone pages."""
    _create_notion_export(
        tmp_path,
        databases={
            "Tasks abc123abc123abc123abc123abc123ab": [
                {"Name": "Task 1"},
            ]
        },
    )
    result = _run_scan(tmp_path)
    # The .md file created for "Task 1" should not appear as standalone
    standalone_titles = {p.title for p in result.standalone_pages}
    assert "Task 1" not in standalone_titles
