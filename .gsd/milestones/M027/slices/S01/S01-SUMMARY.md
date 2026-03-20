---
id: S01
parent: M027
milestone: M027
provides:
  - NotionScanner class with CSV parsing, Notion ID stripping, 8-type column inference, cross-DB relation detection
  - 6 dataclasses (NotionScanResult, NotionDatabase, NotionColumn, NotionPage, DetectedRelation, ScanWarning) with to_dict/from_dict serialization
  - FastAPI router at /browser/notion/ with 6 endpoints (import, upload, scan, stream, discard, results)
  - SSE broadcast for real-time scan progress
  - 7-step wizard UI with scan results display (database column summaries, standalone pages, detected relations, warnings)
  - Sidebar "Import Notion" link and command palette "Import > Notion" entry
requires:
  - slice: none
    provides: first slice — no upstream dependencies
affects:
  - S02 (consumes NotionScanResult, router endpoints, wizard step bar)
  - S03 (consumes NotionScanResult, extends router with execute endpoint)
key_files:
  - backend/app/notion/__init__.py
  - backend/app/notion/models.py
  - backend/app/notion/scanner.py
  - backend/app/notion/broadcast.py
  - backend/app/notion/router.py
  - backend/tests/test_notion_scanner.py
  - backend/app/templates/notion/import.html
  - backend/app/templates/notion/partials/scan_results.html
  - backend/app/templates/notion/partials/scan_trigger.html
  - backend/app/templates/notion/partials/upload_form.html
  - backend/app/templates/notion/partials/step_bar.html
  - backend/app/main.py
  - backend/app/templates/components/_sidebar.html
  - frontend/static/js/workspace.js
key_decisions:
  - Notion broadcast.py is a self-contained copy adapted from Obsidian, not a shared import
  - Scanner imports from local notion.broadcast (not obsidian.broadcast) for module self-containment
  - Command palette entry has no icon property — ninja-keys renders icon text literally
  - "Continue to Type Mapping" button rendered as disabled placeholder for S02 to enable
patterns_established:
  - Notion import wizard mirrors Obsidian pattern — parallel module, htmx partial-swap, SSE scan progress
  - Module-level pure functions (_strip_notion_id, _infer_column_type) for easy unit testing
  - scan_trigger uses fetch() + innerHTML + manual script execution for scan results injection
observability_surfaces:
  - SSE events (scan_progress, scan_complete, scan_error) via /browser/notion/scan/{id}/stream
  - scan_result.json persisted at /app/data/imports/notion/{user_id}/{timestamp}/
  - ScanWarning objects in scan results UI for malformed CSV / empty database / parse errors
drill_down_paths:
  - .gsd/milestones/M027/slices/S01/tasks/T01-SUMMARY.md
  - .gsd/milestones/M027/slices/S01/tasks/T02-SUMMARY.md
duration: 70m
verification_result: passed
completed_at: 2026-03-20
---

# S01: Notion ZIP Scanner + Upload UI

**Built Notion ZIP scanner with CSV parsing, 8-type column inference, cross-DB relation detection (31 unit tests), and full upload → scan → results wizard UI at /browser/notion/import**

## What Happened

**T01 — Scanner and models (25m):** Created the `backend/app/notion/` package with 6 dataclasses (NotionScanResult, NotionDatabase, NotionColumn, NotionPage, DetectedRelation, ScanWarning) and the NotionScanner class. The scanner follows the Obsidian VaultScanner async pattern — `scan()` delegates to `asyncio.to_thread(_do_scan)`. The sync logic walks extracted directories, identifies database folders by matching CSV stems to folder names (after stripping Notion IDs), parses CSV with `encoding='utf-8-sig'` for BOM handling, and infers column types across 8 categories (checkbox, url, number, date, multi_select, select, relation, text). Cross-DB relation detection uses >80% title overlap. Two module-level pure functions (`_strip_notion_id`, `_infer_column_type`) keep the logic testable. 31 unit tests cover all behaviors including BOM, nested folders, empty databases, malformed CSV warnings, and broadcast events.

**T02 — Router, templates, and wiring (45m):** Built a FastAPI router with 6 endpoints (import page, upload, scan, stream, discard, results) mirroring the Obsidian pattern at `/browser/notion/` prefix. Created the main import page and 4 partials: upload form (drag-and-drop + file select), scan trigger (SSE progress bar), step bar (7 wizard steps), and scan results (stat cards, database column tables with type badges, standalone pages list, detected relations table, warnings section). Wired the router into main.py, added sidebar link and command palette entry. Fixed a step bar duplication bug where `innerHTML =` doesn't auto-execute `<script>` tags.

## Verification

- `cd backend && python -m pytest tests/test_notion_scanner.py -v` — **31/31 tests pass** (CSV parsing, ID stripping, column type inference, relation detection, standalone page detection, BOM handling, warnings, broadcast events)
- All 11 key files exist and pass syntax checks
- Router wired into main.py (line 32 import, line 594 include)
- Sidebar "Import Notion" link present in `_sidebar.html` (line 114)
- Command palette "Import > Notion" entry in `workspace.js` (line 1461)
- T02 verified full upload → scan → results flow in browser (3 DBs, 2 pages, 1 relation detected)

## Requirements Advanced

- NOTION-01 — Moved from deferred to active. S01 proves the scanner (CSV parsing, ID stripping, type inference, relation detection) and upload/scan/results UI. Full validation requires S02 (mapping) + S03 (import execution).

## Requirements Validated

- None — NOTION-01 requires the complete wizard flow (S01+S02+S03) for validation.

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- Scanner imports from local `notion.broadcast` instead of `obsidian.broadcast` — makes the module self-contained (deviation from T01's initial approach, corrected in T02)
- 31 tests written instead of the planned 22 — additional edge cases for case-insensitive checkbox, multiple spaces in ID stripping, nested folders, empty databases, broadcast events
- Command palette entry has no icon — ninja-keys renders icon text literally, not as Lucide SVG (dropped from plan)
- Added manual inline script execution in scan_trigger.html — plan didn't anticipate that innerHTML doesn't execute `<script>` tags

## Known Limitations

- "Continue to Type Mapping" button is a disabled placeholder — S02 will enable it
- The Obsidian import's scan_trigger has the same `innerHTML` script-execution bug (not fixed — out of scope)
- No scan progress cancellation mechanism
- Relation detection is heuristic (>80% title overlap) — false positives possible for databases with common titles

## Follow-ups

- S02 needs to consume `NotionScanResult` from the persisted `scan_result.json` and wire the type/property/relation mapping UI
- S02 should enable the "Continue to Type Mapping" button in scan_results.html

## Files Created/Modified

- `backend/app/notion/__init__.py` — Package init
- `backend/app/notion/models.py` — 6 dataclasses with serialization (158 lines)
- `backend/app/notion/scanner.py` — NotionScanner + pure functions (323 lines)
- `backend/app/notion/broadcast.py` — SSE broadcast helper (adapted from Obsidian)
- `backend/app/notion/router.py` — FastAPI router with 6 endpoints
- `backend/tests/test_notion_scanner.py` — 31 unit tests (500 lines)
- `backend/app/templates/notion/import.html` — Main import page
- `backend/app/templates/notion/partials/step_bar.html` — 7-step wizard bar
- `backend/app/templates/notion/partials/upload_form.html` — Upload form with drag-and-drop
- `backend/app/templates/notion/partials/scan_trigger.html` — Scan trigger with SSE progress
- `backend/app/templates/notion/partials/scan_results.html` — Scan results display
- `backend/app/main.py` — Added notion router inclusion
- `backend/app/templates/components/_sidebar.html` — Added "Import Notion" link
- `frontend/static/js/workspace.js` — Added "Import > Notion" command palette entry

## Forward Intelligence

### What the next slice should know
- `NotionScanResult` is persisted as `scan_result.json` at `/app/data/imports/notion/{user_id}/{timestamp}/` — load it via `NotionScanResult.from_dict(json.load(...))` for mapping steps
- The step bar has 7 steps (Upload, Scan, Types, Properties, Relations, Preview, Import) — S02 activates steps 3-5
- The `router.py` already has a `_get_import_state()` helper that locates the user's import directory and loads scan results
- The "Continue to Type Mapping" button in scan_results.html needs its `disabled` attribute removed and an `hx-get` target wired

### What's fragile
- `scan_trigger.html` uses raw `fetch()` + `innerHTML` + manual script tag extraction/execution — this pattern is fragile and shared with the Obsidian importer. Any changes to how step bar replacement works need testing in both importers.
- Relation detection depends on exact title string matching — Unicode normalization or trailing whitespace could cause missed matches

### Authoritative diagnostics
- `scan_result.json` is the ground truth for what the scanner found — check it via `docker compose exec api cat /app/data/imports/notion/{user_id}/{timestamp}/scan_result.json`
- `ScanWarning` objects in `scan_result.warnings` list all parsing issues per file

### What assumptions changed
- Originally planned to import `ScanBroadcast` from `obsidian.broadcast` — changed to a local copy in `notion.broadcast` for module isolation (T02 corrected T01's approach)
