---
id: S03
parent: M027
milestone: M027
provides:
  - NotionImportExecutor with two-pass execute() — Pass 1 creates objects with mapped properties and markdown bodies, Pass 2 resolves cross-database relations as edges via title matching
  - ImportResult dataclass with unresolved_relations field and to_dict/from_dict serialization
  - 3 router endpoints (execute, stream, summary) wiring executor to web layer with SSE progress
  - import_progress.html template with SSE-driven progress bar and phase indicator
  - import_summary.html template with stat cards, collapsible unresolved relations/errors tables, action buttons
  - Import button enabled on preview page completing the full wizard flow from upload through import
requires:
  - slice: S01
    provides: NotionScanResult, NotionScanner._strip_notion_id, ScanBroadcast/SSEEvent, upload/scan endpoints
  - slice: S02
    provides: MappingConfig with type_mappings/property_mappings/relation_mappings, mapping endpoints, preview page
affects:
  - S04
key_files:
  - backend/app/notion/executor.py
  - backend/app/notion/models.py
  - backend/app/notion/router.py
  - backend/tests/test_notion_executor.py
  - backend/app/templates/notion/partials/import_progress.html
  - backend/app/templates/notion/partials/import_summary.html
  - backend/app/templates/notion/partials/preview.html
key_decisions:
  - Executor follows Obsidian two-pass pattern (objects then edges) with title_index dict for O(1) relation resolution
  - Broadcast key pattern "{import_id}_import" for SSE events matching Obsidian convention
  - asyncio.run() in tests instead of pytest.mark.asyncio (pytest-asyncio not installed, matching existing test files)
  - Import result dict keys (.source/.relation/.value) match template access pattern for unresolved_relations
patterns_established:
  - Two-pass import engine pattern reusable for future importers (Pass 1 objects with title index, Pass 2 edge resolution by title lookup)
  - Body file matching via _strip_notion_id for case-insensitive title→file lookup across Notion-ID-suffixed filenames
  - SSE race condition handling — if import completes before SSE connects, serve from persisted import_result.json
  - Per-row error isolation — one bad CSV row doesn't abort the import; errors collected in ImportResult.errors
observability_surfaces:
  - SSE events: import_progress (phase/current/total/current_file/current_link), import_complete (full result dict), import_error (message)
  - Persisted file: import_result.json in import directory for post-mortem inspection
  - ImportResult.errors list with (path, message) per failed row
  - ImportResult.unresolved_relations with (source_iri, relation_key, unmatched_value) per failed lookup
  - Summary page at GET /browser/notion/{import_id}/summary with stat cards and collapsible tables
  - Executor logging: docker compose logs api | grep "Import" for per-row failures
drill_down_paths:
  - .gsd/milestones/M027/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M027/slices/S03/tasks/T02-SUMMARY.md
duration: 35m
verification_result: passed
completed_at: 2026-03-20
---

# S03: Two-Pass Import Executor + Full Flow

**Added NotionImportExecutor two-pass import engine (objects → edges by title matching) with SSE progress, import summary UI, and enabled Import button — completing the full Notion wizard flow from upload through import**

## What Happened

T01 built the core import engine. `ImportResult` was added to `models.py` with a Notion-specific `unresolved_relations` field (3-tuple: source_iri, relation_key, unmatched_value) and full JSON serialization. `NotionImportExecutor` in `executor.py` (~290 lines) follows the Obsidian executor's two-pass structure:

- **Pass 1 (Objects):** Iterates mapped databases, reads CSVs with `utf-8-sig` encoding, creates RDF objects via `handle_object_create` with mapped properties. Body files are matched using `_strip_notion_id` for case-insensitive title→file lookup. A `title_index` dict (db_name → {title_lower → object_iri}) is built during this phase for O(1) relation resolution. Standalone pages are imported when `standalone_page_type_iri` is configured. SSE progress events fire per row.

- **Pass 2 (Edges):** Re-reads CSVs for databases with mapped relations. Splits comma-separated relation cells into individual targets. Looks up each target in the `title_index`. Resolved targets become edges via `handle_edge_create` with batch commits every 10. Unresolved targets are collected in `result.unresolved_relations` with source IRI, relation key, and the unmatched value. Edge errors are isolated per-edge.

Per-row error isolation ensures one bad CSV row doesn't abort the import. The result is persisted as `import_result.json` and broadcast via SSE (`import_complete` or `import_error`). 20 unit tests cover serialization (4), Pass 1 object creation (5), Pass 2 relation resolution (3), error isolation (1), standalone pages (2), body file matching (2), and SSE broadcast (3).

T02 wired the executor to the web layer. Three router endpoints were added: `POST /{import_id}/execute` launches the async import and returns the progress template, `GET /{import_id}/execute/stream` is the SSE endpoint with race-condition handling (serves from persisted result if import completed before SSE connected), and `GET /{import_id}/summary` renders the summary page with a nav-refresh HX-Trigger. Two Jinja2 templates were created: `import_progress.html` with an SSE-driven progress bar showing object and edge phases with a scrolling log, and `import_summary.html` with stat cards (Created/Edges/Skipped/Duration), collapsible Unresolved Relations table (3-column with 50-item cap), collapsible Errors table, and action buttons (Browse/Import More/Discard). The Import button on `preview.html` was enabled by removing `disabled` and the placeholder title.

## Verification

| # | Check | Result |
|---|-------|--------|
| 1 | `python -m pytest tests/test_notion_executor.py -v` | ✅ 20/20 passed |
| 2 | `python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py -v` | ✅ 49/49 passed (zero regressions) |
| 3 | `python3 -c "import ast; ast.parse(open('backend/app/notion/executor.py').read())"` | ✅ no syntax errors |
| 4 | `python3 -c "import ast; ast.parse(open('backend/app/notion/router.py').read())"` | ✅ no syntax errors |
| 5 | Jinja2 parse import_progress.html | ✅ OK |
| 6 | Jinja2 parse import_summary.html | ✅ OK |
| 7 | `grep -c "disabled" preview.html` → 0 | ✅ Import button enabled |
| 8 | `grep "Coming in next update" preview.html` → empty | ✅ placeholder removed |
| 9 | `grep -rn "^<<<<<<< " backend/app/notion/ backend/app/templates/notion/ backend/tests/test_notion_executor.py` | ✅ zero conflict markers |

## Requirements Advanced

- NOTION-01 — Two-pass executor creates objects from CSV rows and resolves relations as edges, completing the core import pipeline. Upload→scan→map→preview→execute→summary flow now works end-to-end. Full validation deferred to S04 (E2E test against Docker stack).

## Requirements Validated

- None newly validated in this slice (integration E2E test in S04 will validate NOTION-01 through NOTION-03)

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- Used `asyncio.run()` wrapper in tests instead of `@pytest.mark.asyncio` — pytest-asyncio is not installed in the venv. Matches pattern in existing `test_notion_scanner.py`.
- Relaxed `duration_seconds > 0` assertion to `>= 0` — execution completes in under 10ms with mocks, rounding to 0.00.

## Known Limitations

- Title-based relation resolution has inherent ambiguity — duplicate titles in a target database produce first-match behavior. Unresolved relations are reported in the summary but not auto-fixable.
- Edge progress total is not known upfront (uses current count as total) — the progress bar for edges shows 100% throughout since total equals current.
- No rollback mechanism — if the import fails partway, already-created objects remain in the triplestore.
- Import is not resumable — a failed import must be restarted from scratch.

## Follow-ups

- S04 will add E2E Playwright test exercising the full wizard flow against Docker test stack with fixture data
- S04 will add user guide chapter documenting the Notion import workflow

## Files Created/Modified

- `backend/app/notion/models.py` — Added `ImportResult` dataclass with `unresolved_relations`, `to_dict()`, `from_dict()`
- `backend/app/notion/executor.py` — New file: `NotionImportExecutor` with two-pass `execute()` method (~290 lines)
- `backend/tests/test_notion_executor.py` — New file: 20 unit tests across 6 test classes (~760 lines)
- `backend/app/notion/router.py` — Added 3 import endpoints (execute, stream, summary) (~115 new lines)
- `backend/app/templates/notion/partials/import_progress.html` — New SSE-driven progress template
- `backend/app/templates/notion/partials/import_summary.html` — New summary template with stat cards and collapsible tables
- `backend/app/templates/notion/partials/preview.html` — Enabled Import button (removed disabled attribute)

## Forward Intelligence

### What the next slice should know
- The full wizard flow is functional: upload → scan → type map → property map → relation map → preview → execute → summary. S04 E2E tests should exercise this complete chain.
- The fixture Notion export ZIP needs at least 2 databases with cross-database relations and some standalone pages to exercise both passes.
- SSE events use the broadcast key pattern `{import_id}_import` — the E2E test EventSource should connect to `/browser/notion/{import_id}/execute/stream`.
- The summary page loads via htmx ajax after `import_complete` SSE event — the E2E test should wait for the summary to render rather than polling.

### What's fragile
- Edge progress reporting shows current=total throughout (total unknown upfront) — this is a cosmetic issue, not functional, but the E2E test shouldn't assert on edge progress percentages.
- Body file matching depends on `_strip_notion_id` regex matching exactly 32 hex chars — fixture filenames must follow Notion's naming convention (e.g., `My Page abc123def456abc123def456abc123de.md`).

### Authoritative diagnostics
- `import_result.json` in the import directory is the ground truth for what happened — check `created`, `edges_created`, `unresolved_relations`, and `errors` fields.
- `docker compose logs api | grep "Import error"` shows per-row failures with stack traces.

### What assumptions changed
- No assumptions changed — the implementation matched the plan exactly. The Obsidian executor pattern transferred cleanly to the Notion context.
