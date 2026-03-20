---
estimated_steps: 6
estimated_files: 4
---

# T02: Router endpoints + templates + enable Import button

**Slice:** S03 — Two-Pass Import Executor + Full Flow
**Milestone:** M027

## Description

Wire the `NotionImportExecutor` from T01 into the web layer. Add 3 router endpoints (execute, stream, summary) adapted from the Obsidian importer, create 2 Jinja2 templates (import_progress, import_summary), and enable the disabled Import button on the preview page. This completes the full wizard flow from upload through import summary.

The Obsidian router endpoints at `backend/app/obsidian/router.py` lines 530–654 are the direct reference. The Notion versions change URL paths from `/browser/import/` to `/browser/notion/`, use `current_step = 7` instead of 6, add an "Unresolved Relations" section to the summary template, and point action buttons to Notion-specific URLs.

## Steps

1. **Add execute endpoint to `backend/app/notion/router.py`:**
   - Add import at top: `from .executor import NotionImportExecutor` and `from .models import ImportResult`
   - Add `@router.post("/{import_id}/execute")` endpoint adapted from Obsidian's `import_execute` (router.py line 530):
     - Get `import_dir`, load `scan_result` and `mapping_config`
     - Get `extract_path = Path(scan_result.extract_path)`
     - Get `event_store` and `triplestore_client` from `request.app.state`
     - Create `ScanBroadcast()`, store in `_broadcasts` with key `f"{import_id}_import"`
     - Create `NotionImportExecutor(scan_result, mapping_config, extract_path, event_store, triplestore_client, user, broadcast, import_dir)`
     - Launch `asyncio.create_task(_run_import())` where `_run_import` awaits `executor.execute()` and cleans up broadcast in `finally`
     - Return `import_progress.html` template with `import_id` and `current_step=7`

2. **Add stream endpoint:**
   - Add `@router.get("/{import_id}/execute/stream")` adapted from Obsidian (router.py line 578):
     - Validate ownership via `_get_import_dir` pattern
     - Look up broadcast with key `f"{import_id}_import"`
     - If no broadcast found, check for completed import (race condition): look for `import_result.json`, send single `import_complete` SSE event if found, otherwise `import_error`
     - Otherwise subscribe to broadcast and stream SSE with `terminal_events={"import_complete", "import_error"}`
     - Set headers: `Cache-Control: no-cache`, `Connection: keep-alive`, `X-Accel-Buffering: no`

3. **Add summary endpoint:**
   - Add `@router.get("/{import_id}/summary")` adapted from Obsidian (router.py line 624):
     - Load `import_result.json` from import directory, 404 if missing
     - Load `scan_result` for context
     - Render `notion/partials/import_summary.html` with `import_result` and `scan_result`
     - Set `HX-Trigger: sempkm:nav-refresh` header on response

4. **Create `backend/app/templates/notion/partials/import_progress.html`:**
   - Adapt from `backend/app/templates/obsidian/partials/import_progress.html`
   - Change `{% set current_step = 6 %}` → `{% set current_step = 7 %}`
   - Change step bar include from `obsidian/partials/step_bar.html` → `notion/partials/step_bar.html`
   - Change SSE URL from `'/browser/import/' + importId + '/execute/stream'` → `'/browser/notion/' + importId + '/execute/stream'`
   - Change summary fetch URL from `'/browser/import/' + importId + '/summary'` → `'/browser/notion/' + importId + '/summary'`
   - Keep the same progress bar structure, phase text, counter, and scrolling log
   - Keep the same SSE event listeners (`import_progress`, `import_complete`, `import_error`)

5. **Create `backend/app/templates/notion/partials/import_summary.html`:**
   - Adapt from `backend/app/templates/obsidian/partials/import_summary.html`
   - Change `{% set current_step = 6 %}` → `{% set current_step = 7 %}`
   - Change step bar include from `obsidian/partials/step_bar.html` → `notion/partials/step_bar.html`
   - Stat cards: Created, Edges, Skipped (use `import_result.skipped`), Duration
   - **Add "Unresolved Relations" section** (new, not in Obsidian):
     - Similar pattern to "Unresolved Links" — collapsible `<details>` with table
     - Table columns: Source Object, Relation, Target (not found)
     - Iterate `import_result.unresolved_relations` (each has `.source`, `.relation`, `.value`)
     - Show first 50, with "... and N more" for overflow
   - Keep "Errors" collapsible section (same as Obsidian)
   - Action buttons:
     - "Browse Imported Objects" → navigate to `/browser/` (workspace) with nav-refresh dispatch
     - "Import More" → `hx-get="/browser/notion/import"` targeting `#import-area`
     - "Discard Files" → `hx-post="/browser/notion/{{ import_id }}/discard"` with confirmation

6. **Enable Import button in `backend/app/templates/notion/partials/preview.html`:**
   - Find the Import button (currently has `disabled` attribute and `title="Coming in next update"`)
   - Remove the `disabled` attribute
   - Remove the `title="Coming in next update"` attribute
   - The button already has `hx-post="/browser/notion/{{ import_id }}/execute"` and `hx-target="#import-content"` and `hx-swap="innerHTML"` — verify these are correct
   - Keep the button text "Import" and icon `<i data-lucide="download"></i>`

## Must-Haves

- [ ] `POST /{import_id}/execute` endpoint creates executor, launches async task, returns progress template
- [ ] `GET /{import_id}/execute/stream` endpoint streams SSE events with race-condition handling for fast imports
- [ ] `GET /{import_id}/summary` endpoint loads result JSON and renders summary template with nav-refresh trigger
- [ ] `import_progress.html` has SSE-driven progress bar with object and edge phases, correct Notion URLs
- [ ] `import_summary.html` has stat cards, unresolved relations section, errors section, and action buttons
- [ ] Import button in `preview.html` is enabled (no `disabled` attribute, no placeholder title)

## Verification

- `python3 -c "import ast; ast.parse(open('backend/app/notion/router.py').read())"` — no syntax errors
- `python3 -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('backend/app/templates')); env.parse(env.loader.get_source(env, 'notion/partials/import_progress.html')[0])"` — template parses
- `python3 -c "from jinja2 import Environment, FileSystemLoader; env = Environment(loader=FileSystemLoader('backend/app/templates')); env.parse(env.loader.get_source(env, 'notion/partials/import_summary.html')[0])"` — template parses
- `grep -c "disabled" backend/app/templates/notion/partials/preview.html` — returns 0 for the import button line (no `disabled` on that button)
- `grep "Coming in next update" backend/app/templates/notion/partials/preview.html` — returns nothing (title removed)
- `grep -rn "^<<<<<<< " backend/app/notion/ backend/app/templates/notion/` — zero conflict markers

## Inputs

- `backend/app/notion/executor.py` — `NotionImportExecutor` class from T01
- `backend/app/notion/models.py` — `ImportResult` dataclass from T01
- `backend/app/notion/router.py` — existing router with 6+4 endpoints from S01+S02
- `backend/app/notion/broadcast.py` — `ScanBroadcast`, `SSEEvent`, `stream_sse` from S01
- `backend/app/obsidian/router.py` lines 530–654 — reference execute/stream/summary endpoints
- `backend/app/templates/obsidian/partials/import_progress.html` — reference progress template
- `backend/app/templates/obsidian/partials/import_summary.html` — reference summary template
- `backend/app/templates/notion/partials/preview.html` — current preview with disabled Import button

## Observability Impact

- **New SSE stream endpoint** `GET /browser/notion/{import_id}/execute/stream` — agent or user connects to observe real-time import progress; events: `import_progress` (phase/current/total), `import_complete` (full result dict), `import_error` (message).
- **Summary endpoint** `GET /browser/notion/{import_id}/summary` — renders persisted import_result.json as HTML; sets `HX-Trigger: sempkm:nav-refresh` to update explorer tree after import.
- **Failure inspection:** Per-row errors visible in summary template's collapsible Errors section. Unresolved relations (new Notion-specific section) visible in summary with source/relation/value columns. `import_error` SSE event on catastrophic failure.
- **Diagnostic path:** `cat /app/data/imports/notion/{user_id}/{timestamp}/import_result.json` for raw result; `docker compose logs api | grep "Import"` for executor logging.

## Expected Output

- `backend/app/notion/router.py` — Extended with 3 new endpoints (execute, stream, summary), ~80 new lines
- `backend/app/templates/notion/partials/import_progress.html` — New file, ~100 lines, SSE progress UI
- `backend/app/templates/notion/partials/import_summary.html` — New file, ~130 lines, summary with stat cards + unresolved relations
- `backend/app/templates/notion/partials/preview.html` — Modified, Import button enabled (2 attributes removed)
