---
estimated_steps: 8
estimated_files: 4
---

# T01: Notion data models, scanner, and unit tests

**Slice:** S01 — Notion ZIP Scanner + Upload UI
**Milestone:** M027

## Description

Build the Notion scanner — the core parsing engine that extracts structured data from a Notion workspace ZIP export. This is the novel, riskiest code in the slice: CSV parsing with BOM handling, Notion ID stripping from filenames, column type inference across 8 types, and cross-database relation detection via title matching.

The scanner follows the Obsidian VaultScanner pattern (`backend/app/obsidian/scanner.py`): a class that accepts an extract path and broadcast instance, runs sync logic on a background thread via `asyncio.to_thread`, and returns a structured result dataclass.

Key differences from Obsidian scanner:
- Parses CSV files (not frontmatter) for database schema + rows
- Strips 32-hex-char Notion IDs from filenames/folders
- Infers column types from CSV values (Select, Multi-select, Date, Checkbox, URL, Number, Relation, Text)
- Detects cross-DB relations by checking if column values overlap >80% with another DB's row titles
- Identifies standalone `.md` pages (not in a database folder)

## Steps

1. **Create the `notion` package** — `backend/app/notion/__init__.py` with a one-line comment.

2. **Define data models** in `backend/app/notion/models.py`:
   - `NotionColumn(name, inferred_type, sample_values, non_empty_count)` — represents a CSV column with its inferred type
   - `NotionDatabase(name, folder_path, csv_path, columns, row_count, row_titles, sample_rows)` — a database folder with its CSV schema. `row_titles` is the list of all row title values (first CSV column) for relation detection. `sample_rows` holds up to 5 sample dicts.
   - `NotionPage(title, file_path, has_body)` — a standalone markdown page
   - `DetectedRelation(source_db_name, source_column, target_db_name, match_ratio)` — a detected cross-DB relation candidate
   - `ScanWarning(severity, category, message, file_path)` — same pattern as Obsidian
   - `NotionScanResult(workspace_name, import_id, extract_path, databases, standalone_pages, detected_relations, warnings, total_files, csv_files, markdown_files, scan_duration_seconds)` — with `to_dict()` and `from_dict()` methods

3. **Implement NotionScanner** in `backend/app/notion/scanner.py`:
   - Constructor: `__init__(self, extract_path: Path, import_id: str, broadcast: ScanBroadcast)`
   - `async scan() -> NotionScanResult` — delegates to `asyncio.to_thread(self._do_scan)`
   - `_do_scan()` — synchronous scan logic:
     a. Auto-detect workspace root (single top-level dir → use as root)
     b. Walk directory tree, identify database folders (folders containing a `.csv` file with the same stem as the folder after stripping Notion IDs)
     c. For each database folder:
        - Read the CSV with `csv.DictReader`, `encoding='utf-8-sig'`
        - Strip Notion ID from folder name using regex `r'\s+[0-9a-f]{32}$'`
        - Collect row titles (first column values)
        - Collect sample values per column
        - Infer column types via `_infer_column_type(values)` helper
        - Broadcast `scan_progress` SSE events periodically
     d. Identify standalone pages: `.md` files NOT inside any database folder
     e. Cross-DB relation detection: for each column with type "text" in each DB, check if >80% of non-empty values appear in another DB's row_titles set (case-insensitive). If so, mark as `DetectedRelation` and update column type to "relation".
     f. Broadcast `scan_complete`
   - `_detect_workspace_root(self) -> Path` — same pattern as Obsidian vault root detection
   - `_strip_notion_id(name: str) -> str` — regex strip of ` [0-9a-f]{32}` from end of name (module-level helper)
   - `_infer_column_type(values: list[str]) -> str` — type inference logic:
     - All empty → "text"
     - All "Yes"/"No" → "checkbox"
     - All match URL pattern (starts with `http://` or `https://`) → "url"
     - All parseable as float → "number"
     - All parseable via `dateutil.parser.parse()` → "date"
     - ≤20 unique non-empty values → "select"
     - Contains comma-separated components where unique component count is small relative to unique cell count → "multi_select"
     - Default → "text"

4. **Write comprehensive unit tests** in `backend/tests/test_notion_scanner.py`:
   - Use `tmp_path` fixture to create synthetic Notion export directories
   - Helper `_create_notion_export(tmp_path, databases, standalone_pages)` that builds the directory structure with CSV files and markdown files
   - Tests (≥20):
     - `test_strip_notion_id_32_hex` — strips exactly 32 hex chars
     - `test_strip_notion_id_short_hex_preserved` — doesn't strip 20 hex chars
     - `test_strip_notion_id_no_space_prefix` — doesn't strip if no space before hex
     - `test_strip_notion_id_no_hex` — returns name unchanged
     - `test_infer_type_checkbox` — "Yes"/"No" values → "checkbox"
     - `test_infer_type_url` — http/https values → "url"
     - `test_infer_type_number` — numeric strings → "number"
     - `test_infer_type_date` — ISO date strings → "date"
     - `test_infer_type_select` — ≤20 unique values → "select"
     - `test_infer_type_multi_select` — comma-separated with few components → "multi_select"
     - `test_infer_type_text_default` — varied content → "text"
     - `test_infer_type_empty_values` — all empty → "text"
     - `test_infer_type_mixed_empty` — mostly empty with some values → infers from non-empty
     - `test_scan_single_database` — one CSV database with 3 rows, correct column types
     - `test_scan_standalone_pages` — markdown files outside database folders detected
     - `test_scan_cross_db_relation` — column values matching another DB's titles → DetectedRelation
     - `test_scan_relation_below_threshold` — <80% match → not detected as relation
     - `test_scan_bom_csv` — UTF-8 BOM in CSV file handled correctly
     - `test_scan_nested_workspace_root` — single top-level dir detected as workspace root
     - `test_scan_result_round_trip` — to_dict()/from_dict() preserves all fields
     - `test_scan_warning_malformed_csv` — malformed CSV produces warning, doesn't crash
     - `test_scan_multiple_databases` — two databases scanned with correct stats

## Must-Haves

- [ ] `NotionScanResult`, `NotionDatabase`, `NotionColumn`, `NotionPage`, `DetectedRelation`, `ScanWarning` dataclasses defined with `to_dict()`/`from_dict()` serialization
- [ ] `NotionScanner` parses CSV files with `encoding='utf-8-sig'`
- [ ] Notion ID stripping regex matches exactly 32 hex chars preceded by a space
- [ ] Column type inference correctly classifies all 8 types (text, select, multi_select, date, checkbox, url, number, relation)
- [ ] Cross-DB relation detection uses >80% title overlap threshold
- [ ] Standalone pages are `.md` files not inside database folders
- [ ] `_infer_column_type` handles empty values gracefully (doesn't crash, returns "text")
- [ ] ≥20 unit tests pass covering all scanner behaviors

## Verification

- `cd /home/james/Code/SemPKM/backend && python -m pytest tests/test_notion_scanner.py -v` — all tests pass
- `cd /home/james/Code/SemPKM/backend && python -m pytest tests/test_notion_scanner.py -v --tb=short 2>&1 | tail -5` shows `passed` with 0 failures
- Check LSP diagnostics on models.py and scanner.py — no type errors

## Inputs

- `backend/app/obsidian/scanner.py` — reference pattern for async scan with broadcast
- `backend/app/obsidian/models.py` — reference pattern for dataclass structure and serialization
- M027-RESEARCH.md — scanner design details (Notion ZIP structure, type inference logic, relation detection)

## Expected Output

- `backend/app/notion/__init__.py` — package init
- `backend/app/notion/models.py` — 6 dataclasses with serialization
- `backend/app/notion/scanner.py` — NotionScanner class + helper functions
- `backend/tests/test_notion_scanner.py` — ≥20 unit tests all passing
