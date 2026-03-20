# S03: Two-Pass Import Executor + Full Flow

**Goal:** User clicks Import on the preview page → objects are created from CSV rows + standalone pages (Pass 1) → relations resolved as edges by title matching (Pass 2) → SSE progress throughout → import summary with stats and unresolvable relations
**Demo:** Upload Notion ZIP → scan → map types/properties/relations → preview → click Import → SSE progress bar shows objects then edges → summary page with created/edges/skipped counts and any unresolved relations

## Must-Haves

- `NotionImportExecutor` class with two-pass import (objects + body in Pass 1, relations as edges in Pass 2)
- `ImportResult` dataclass with `unresolved_relations` field for Notion-specific ambiguity reporting
- CSV re-reading from `extract_path` with `utf-8-sig` encoding for full row iteration
- Title→IRI lookup dict populated during Pass 1 for O(1) relation resolution in Pass 2
- Body file matching via `_strip_notion_id` from scanner — case-insensitive
- Multi-value relation cells split on comma with independent lookup per value
- Per-row error isolation (one bad row doesn't abort the import)
- SSE progress events for both phases (objects and edges)
- Import result persisted as `import_result.json`
- Import button on preview page enabled with `hx-post` to execute endpoint
- Import progress template with SSE-driven progress bar and scrolling log
- Import summary template with stat cards, unresolved relations section, and action buttons
- Standalone page import when `standalone_page_type_iri` is set

## Proof Level

- This slice proves: integration (executor creates real objects via command handlers, resolves relations, reports results via SSE and summary UI)
- Real runtime required: yes (unit tests use mocks; full flow requires Docker stack)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_notion_executor.py -v` — all tests pass
- `cd backend && python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py -v` — zero regressions (49 existing tests)
- `python3 -c "import ast; ast.parse(open('backend/app/notion/executor.py').read())"` — no syntax errors
- `python3 -c "import ast; ast.parse(open('backend/app/notion/router.py').read())"` — no syntax errors
- All new Jinja2 templates parse without errors
- `grep -rn "^<<<<<<< " backend/app/notion/ backend/app/templates/notion/ backend/tests/test_notion_executor.py` — zero conflict markers

## Observability / Diagnostics

- Runtime signals: SSE events (`import_progress` with phase/current/total, `import_complete` with result dict, `import_error` with message)
- Inspection surfaces: `import_result.json` persisted in import directory; `docker compose logs api | grep "Import"` for executor logging; summary page shows all stats
- Failure visibility: per-row errors collected in `ImportResult.errors` list with path+message; unresolved relations in `ImportResult.unresolved_relations` with source_iri+relation_key+value; `import_error` SSE event on catastrophic failure
- Redaction constraints: none

## Integration Closure

- Upstream surfaces consumed: `NotionScanResult` from S01 (scan_result.json), `MappingConfig` from S02 (mapping_config.json), `_strip_notion_id` from `notion.scanner`, `ScanBroadcast`/`SSEEvent` from `notion.broadcast`, command handlers (`handle_object_create`, `handle_body_set`, `handle_edge_create`), `EventStore`, `TriplestoreClient`
- New wiring introduced in this slice: 3 router endpoints (execute, stream, summary) in `notion/router.py`, Import button activation in `preview.html`, `import_progress.html` and `import_summary.html` templates
- What remains before the milestone is truly usable end-to-end: S04 (E2E tests + user guide)

## Tasks

- [x] **T01: ImportResult model + NotionImportExecutor + unit tests** `est:45m`
  - Why: The core import engine — creates objects from CSV data, reads markdown bodies, resolves relations as edges by title matching, reports results. This is the entire backend logic for the slice.
  - Files: `backend/app/notion/models.py`, `backend/app/notion/executor.py`, `backend/tests/test_notion_executor.py`
  - Do: Add `ImportResult` dataclass to models.py with Notion-specific `unresolved_relations` field. Create `executor.py` with `NotionImportExecutor` class following the Obsidian pattern — Pass 1 iterates CSV rows per database, creates objects with mapped properties, reads body files by matching stripped filenames, builds title→IRI index. Pass 2 iterates relation columns, splits comma-separated values, looks up targets in the index, creates edges. Write comprehensive unit tests with mock EventStore and TriplestoreClient.
  - Verify: `cd backend && python -m pytest tests/test_notion_executor.py tests/test_notion_scanner.py tests/test_notion_mapping.py -v` — all pass, zero regressions
  - Done when: `NotionImportExecutor.execute()` creates objects from CSV rows, reads body files, resolves relations as edges, handles standalone pages, reports unresolved relations, and all tests pass

- [x] **T02: Router endpoints + templates + enable Import button** `est:30m`
  - Why: Wires the executor into the web layer so users can trigger import from the wizard, see SSE progress, and view the summary. Completes the full wizard flow from upload to import summary.
  - Files: `backend/app/notion/router.py`, `backend/app/templates/notion/partials/import_progress.html`, `backend/app/templates/notion/partials/import_summary.html`, `backend/app/templates/notion/partials/preview.html`
  - Do: Add 3 router endpoints adapted from Obsidian: `POST /{import_id}/execute` (creates executor, launches async task, returns progress partial), `GET /{import_id}/execute/stream` (SSE stream with race-condition handling), `GET /{import_id}/summary` (loads import_result.json, renders summary with nav-refresh trigger). Create `import_progress.html` adapted from Obsidian (SSE URL points to `/browser/notion/`, step 7 active). Create `import_summary.html` with stat cards, unresolved relations section alongside unresolved links, action buttons pointing to Notion-specific URLs. Enable Import button in `preview.html` by removing `disabled` attribute and `title`, keeping `hx-post`.
  - Verify: `python3 -c "import ast; ast.parse(open('backend/app/notion/router.py').read())"` — no syntax errors; all templates parse; `grep -c "disabled" backend/app/templates/notion/partials/preview.html` returns 0 for the import button
  - Done when: Router has execute/stream/summary endpoints, both templates exist and render correctly, Import button is active on preview page

## Files Likely Touched

- `backend/app/notion/models.py`
- `backend/app/notion/executor.py`
- `backend/app/notion/router.py`
- `backend/tests/test_notion_executor.py`
- `backend/app/templates/notion/partials/preview.html`
- `backend/app/templates/notion/partials/import_progress.html`
- `backend/app/templates/notion/partials/import_summary.html`
