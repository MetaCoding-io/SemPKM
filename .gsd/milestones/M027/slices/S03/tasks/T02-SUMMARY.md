---
id: T02
parent: S03
milestone: M027
provides:
  - 3 router endpoints (execute, stream, summary) wiring NotionImportExecutor to the web layer
  - import_progress.html template with SSE-driven progress bar and scrolling log
  - import_summary.html template with stat cards, unresolved relations section, errors section, and action buttons
  - Import button enabled on preview page completing the full wizard flow
key_files:
  - backend/app/notion/router.py
  - backend/app/templates/notion/partials/import_progress.html
  - backend/app/templates/notion/partials/import_summary.html
  - backend/app/templates/notion/partials/preview.html
key_decisions:
  - Import result dict keys accessed in templates match ImportResult.to_dict() JSON shape (e.g. import_result.unresolved_relations is a list of dicts with .source/.relation/.value)
patterns_established:
  - Notion import endpoints follow identical structure to Obsidian (execute/stream/summary) with broadcast key pattern "{import_id}_import"
observability_surfaces:
  - SSE stream at GET /browser/notion/{import_id}/execute/stream for real-time progress
  - Summary page at GET /browser/notion/{import_id}/summary with stat cards and collapsible error/unresolved-relations tables
  - import_result.json persisted in import directory for post-mortem inspection
duration: 15m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Router endpoints + templates + enable Import button

**Wired NotionImportExecutor to web layer with execute/stream/summary endpoints, SSE progress template, import summary with unresolved-relations section, and enabled Import button**

## What Happened

Added 3 router endpoints to `backend/app/notion/router.py` adapted from the Obsidian importer:

1. `POST /{import_id}/execute` — creates `NotionImportExecutor`, launches async import task via `asyncio.create_task`, returns `import_progress.html` with `current_step=7`.
2. `GET /{import_id}/execute/stream` — SSE stream with race-condition handling: if the import completed before SSE connected, sends a single `import_complete` event from the persisted `import_result.json`.
3. `GET /{import_id}/summary` — loads `import_result.json`, renders `import_summary.html` with nav-refresh HX-Trigger.

Created two Jinja2 templates:
- `import_progress.html` — SSE-driven progress bar with object and edge phases, scrolling log, error display. EventSource connects to `/browser/notion/{importId}/execute/stream`.
- `import_summary.html` — stat cards (Created/Edges/Skipped/Duration), collapsible Unresolved Relations table (3-column: Source Object, Relation, Target with 50-item cap), collapsible Errors table, and action buttons (Browse Imported Objects, Import More, Discard Files).

Enabled the Import button in `preview.html` by removing `disabled` and `title="Coming in next update"` attributes.

## Verification

- Router syntax check: pass
- Progress template Jinja2 parse: pass
- Summary template Jinja2 parse: pass
- `grep -c "disabled" preview.html` returns 0: pass
- `grep "Coming in next update" preview.html` returns nothing: pass
- Zero conflict markers: pass
- All 20 executor tests pass
- All 49 scanner+mapping tests pass (zero regressions)

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 -c "import ast; ast.parse(open('backend/app/notion/router.py').read())"` | 0 | ✅ pass | 3.8s |
| 2 | `backend/.venv/bin/python -c "...env.parse(...'notion/partials/import_progress.html'...)"` | 0 | ✅ pass | 3.3s |
| 3 | `backend/.venv/bin/python -c "...env.parse(...'notion/partials/import_summary.html'...)"` | 0 | ✅ pass | 3.3s |
| 4 | `grep -c "disabled" backend/app/templates/notion/partials/preview.html` → 0 | 0 | ✅ pass | <1s |
| 5 | `grep "Coming in next update" backend/app/templates/notion/partials/preview.html` → empty | 1 | ✅ pass | <1s |
| 6 | `grep -rn "^<<<<<<< " backend/app/notion/ backend/app/templates/notion/` → empty | 1 | ✅ pass | <1s |
| 7 | `cd backend && python -m pytest tests/test_notion_executor.py -v` — 20 passed | 0 | ✅ pass | 0.35s |
| 8 | `cd backend && python -m pytest tests/test_notion_scanner.py tests/test_notion_mapping.py -v` — 49 passed | 0 | ✅ pass | 0.10s |
| 9 | `python3 -c "import ast; ast.parse(open('backend/app/notion/executor.py').read())"` | 0 | ✅ pass | 3.5s |
| 10 | `grep -rn "^<<<<<<< " ...backend/tests/test_notion_executor.py` → empty | 1 | ✅ pass | <1s |

## Diagnostics

- **SSE progress stream:** Connect to `GET /browser/notion/{import_id}/execute/stream` — events: `import_progress` (phase/current/total/current_file/current_link), `import_complete` (full result dict), `import_error` (message)
- **Persisted result:** `cat /app/data/imports/notion/{user_id}/{timestamp}/import_result.json` — contains created/skipped/edges_created/unresolved_relations/errors/duration_seconds
- **Summary page:** `GET /browser/notion/{import_id}/summary` renders collapsible tables for errors and unresolved relations
- **Executor logging:** `docker compose logs api | grep "Import"` for per-row failures and edge creation errors

## Deviations

None — implementation followed the plan exactly.

## Known Issues

None.

## Files Created/Modified

- `backend/app/notion/router.py` — Added 3 import endpoints (execute, stream, summary) and imports for NotionImportExecutor/ImportResult (~115 new lines)
- `backend/app/templates/notion/partials/import_progress.html` — New SSE-driven progress template with phase indicator, progress bar, counter, and scrolling log
- `backend/app/templates/notion/partials/import_summary.html` — New summary template with stat cards, unresolved relations table, errors table, and action buttons
- `backend/app/templates/notion/partials/preview.html` — Enabled Import button (removed disabled attribute and placeholder title)
- `.gsd/milestones/M027/slices/S03/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
