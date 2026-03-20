---
id: T01
parent: S01
milestone: M027
provides:
  - NotionScanner class with CSV parsing, ID stripping, type inference, and relation detection
  - 6 dataclasses (NotionScanResult, NotionDatabase, NotionColumn, NotionPage, DetectedRelation, ScanWarning)
  - 31 unit tests covering all scanner behaviors
key_files:
  - backend/app/notion/__init__.py
  - backend/app/notion/models.py
  - backend/app/notion/scanner.py
  - backend/tests/test_notion_scanner.py
key_decisions:
  - Reuse Obsidian ScanBroadcast directly rather than copying — import from app.obsidian.broadcast
  - Store transient _all_column_values on NotionDatabase during scan for full relation detection (not serialized)
patterns_established:
  - Notion scanner follows VaultScanner async pattern: scan() → asyncio.to_thread(_do_scan)
  - Module-level pure functions (_strip_notion_id, _infer_column_type) for testability
observability_surfaces:
  - ScanWarning objects capture malformed CSV, empty database, and parse errors with file paths
  - SSE events (scan_progress, scan_complete) broadcast during scan for real-time UI
  - NotionScanResult.to_dict() serializes full scan output for persistence as scan_result.json
duration: 25min
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T01: Notion data models, scanner, and unit tests

**Implement NotionScanner with CSV parsing, Notion ID stripping, 8-type column inference, cross-DB relation detection, and 31 passing unit tests**

## What Happened

Built the `backend/app/notion/` package with three files: package init, data models, and scanner.

**Models (models.py):** Six dataclasses — `NotionColumn`, `NotionDatabase`, `NotionPage`, `DetectedRelation`, `ScanWarning`, and `NotionScanResult` with full `to_dict()`/`from_dict()` serialization.

**Scanner (scanner.py):** `NotionScanner` follows the Obsidian VaultScanner pattern — `scan()` delegates to `asyncio.to_thread(_do_scan)`. The sync logic walks the extracted directory, identifies database folders by matching CSV stems to folder names (after stripping Notion IDs), parses CSV files with `encoding='utf-8-sig'`, infers column types across 8 categories, detects standalone markdown pages, and runs cross-DB relation detection using >80% title overlap.

Two module-level pure functions: `_strip_notion_id()` uses regex `\s+[0-9a-f]{32}$` to strip exactly 32-char hex IDs. `_infer_column_type()` checks values in precedence order: checkbox → url → number → date → multi_select → select → text.

The scanner reuses `ScanBroadcast` from `app.obsidian.broadcast` directly rather than copying it — the broadcast module is generic enough to share.

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_notion_scanner.py -v` — 31/31 tests pass
- Syntax check via `ast.parse()` on both models.py and scanner.py — clean
- Import verification — all 6 model classes and scanner class import without errors

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_notion_scanner.py -v` | 0 | ✅ pass | 0.07s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_notion_scanner.py -v --tb=short 2>&1 \| tail -5` | 0 | ✅ pass | 0.07s |
| 3 | `python -c "import ast; ast.parse(...)"` on models.py and scanner.py | 0 | ✅ pass | <1s |

Slice-level verification (partial — T01 is intermediate):
- ✅ `cd backend && python -m pytest tests/test_notion_scanner.py -v` — all scanner unit tests pass
- ⬜ Docker stack upload at `/browser/notion/import` — not yet (requires T02 router/templates)

## Diagnostics

- **Test helpers in isolation:** `from app.notion.scanner import _infer_column_type, _strip_notion_id` — both are pure functions callable directly
- **Scan result inspection:** Call `result.to_dict()` on any `NotionScanResult` to get a JSON-serializable dict. Check `result.warnings` for parse/CSV issues.
- **Broadcast events:** Mock `ScanBroadcast.publish()` and inspect `call_args_list` for event names and data payloads
- **Relation detection:** `result.detected_relations` lists each detected cross-DB relation with source/target DB names, column name, and match ratio

## Deviations

- Added 10 extra tests beyond the 22 specified in the plan (31 total), including edge cases for case-insensitive checkbox, multiple spaces in ID stripping, nested database folders, empty databases, and broadcast event verification
- Used `asyncio.run()` instead of deprecated `asyncio.get_event_loop().run_until_complete()` for Python 3.14 compatibility
- Imported `ScanBroadcast` from `app.obsidian.broadcast` instead of copying it — lower risk, DRY

## Known Issues

None.

## Files Created/Modified

- `backend/app/notion/__init__.py` — package init with one-line comment
- `backend/app/notion/models.py` — 6 dataclasses with to_dict/from_dict serialization (158 lines)
- `backend/app/notion/scanner.py` — NotionScanner class + _strip_notion_id + _infer_column_type (323 lines)
- `backend/tests/test_notion_scanner.py` — 31 unit tests with synthetic fixture helper (500 lines)
- `.gsd/milestones/M027/slices/S01/S01-PLAN.md` — added diagnostic verification step (pre-flight fix)
- `.gsd/milestones/M027/slices/S01/tasks/T01-PLAN.md` — added Observability Impact section (pre-flight fix)
