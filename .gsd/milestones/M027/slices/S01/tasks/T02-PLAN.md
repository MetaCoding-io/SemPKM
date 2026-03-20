---
estimated_steps: 9
estimated_files: 11
---

# T02: Router, templates, broadcast, and wiring

**Slice:** S01 — Notion ZIP Scanner + Upload UI
**Milestone:** M027

## Description

Connect the Notion scanner to the web UI. This task builds the FastAPI router with upload, scan, and results endpoints, the HTML templates for the wizard UI, and wires everything into the app's main router, sidebar navigation, and command palette.

The router follows the Obsidian import router pattern (`backend/app/obsidian/router.py`): htmx-driven step-by-step wizard with SSE progress streaming during scan. The key structural difference is the Notion wizard has 7 steps (Upload → Scan → Types → Properties → Relations → Preview → Import) vs Obsidian's 6 (no Relations step), because Notion imports need an explicit relation mapping step.

This task only builds the S01 endpoints (upload, scan, results, discard). The mapping, preview, and execute endpoints are added in S02 and S03.

## Steps

1. **Copy and adapt broadcast.py** — `backend/app/notion/broadcast.py`. This is a direct copy of `backend/app/obsidian/broadcast.py` (per D258). The only change is updating the module docstring. The `ScanBroadcast` class, `SSEEvent` dataclass, and `stream_sse` async generator are identical.

2. **Build the router** — `backend/app/notion/router.py`:
   - `APIRouter(prefix="/browser/notion", tags=["notion-import"])`
   - `GET /browser/notion/import` — serve the import page (full page or htmx partial). Check for existing in-progress import and render appropriate state.
   - `POST /browser/notion/upload` — accept ZIP file, extract via `zipfile.ZipFile`, return scan trigger partial. Validate it's a ZIP. Use same user-scoped directory pattern as Obsidian: `/app/data/imports/notion/{user_id}/{timestamp}/`.
   - `POST /browser/notion/scan/{import_id}` — trigger scan, return results partial. Instantiate NotionScanner, await scan, persist `scan_result.json`.
   - `GET /browser/notion/scan/{import_id}/stream` — SSE stream for scan progress. Same fan-out pattern as Obsidian.
   - `POST /browser/notion/{import_id}/discard` — remove import directory, return upload form.
   - `GET /browser/notion/{import_id}/results` — return persisted scan results (for page refresh).
   - Helper functions: `_user_imports_dir()`, `_find_existing_import()`, `_get_import_dir()`, `_load_scan_result()` — same pattern as Obsidian but using `NotionScanResult` model.

3. **Create the main import page template** — `backend/app/templates/notion/import.html`:
   - Extends `base.html`, includes `import.css` (shared with Obsidian)
   - Contains `#import-container` with step bar and `#import-content` div
   - Conditionally renders scan results, scan trigger, or upload form based on state
   - Same structure as `backend/app/templates/obsidian/import.html`

4. **Create the step bar partial** — `backend/app/templates/notion/partials/step_bar.html`:
   - 7 steps: Upload, Scan, Types, Properties, Relations, Preview, Import
   - Same CSS classes as Obsidian step bar (`.import-step-bar`, `.step-item`, `.step-active`, etc.)
   - Uses Lucide `check` icon for completed steps

5. **Create the upload form partial** — `backend/app/templates/notion/partials/upload_form.html`:
   - File input accepting `.zip` files
   - htmx `hx-post="/browser/notion/upload"` with `hx-encoding="multipart/form-data"`
   - `hx-target="#import-content"` for response swap
   - Brief instructions: "Export your Notion workspace as a ZIP file (Settings → Export all workspace content → Markdown & CSV format)"

6. **Create the scan trigger partial** — `backend/app/templates/notion/partials/scan_trigger.html`:
   - Shows "workspace uploaded" message
   - "Scan Now" button with `hx-post="/browser/notion/scan/{import_id}"` targeting `#import-content`
   - "Discard" button with `hx-post="/browser/notion/{import_id}/discard"` targeting `#import-content`
   - SSE event source for progress during scan (same pattern as Obsidian)

7. **Create the scan results partial** — `backend/app/templates/notion/partials/scan_results.html`:
   - This is the main deliverable of S01's UI
   - **Databases section**: For each database, show: cleaned name (ID stripped), row count, table of columns with name, inferred type (as badge), sample values
   - **Standalone Pages section**: List of standalone page titles with file paths
   - **Detected Relations section**: Table showing source DB → source column → target DB → match ratio
   - **Warnings section**: Collapsible list of scan warnings (if any)
   - "Continue to Type Mapping" button (links to S02's step, disabled/placeholder for now with `hx-get="/browser/notion/{import_id}/step/type-mapping"` targeting `#import-content`)
   - "Discard & Start Over" button

8. **Wire router into main.py** — Add `from app.notion.router import router as notion_router` and `app.include_router(notion_router)` in `backend/app/main.py`, following the same pattern as the obsidian router.

9. **Add navigation entries**:
   - **Sidebar**: In `backend/app/templates/components/_sidebar.html`, add an "Import Notion" link below the existing "Import Vault" link, pointing to `/browser/notion/import` with a Lucide `file-down` icon.
   - **Command palette**: In `frontend/static/js/workspace.js`, add a `{ id: 'import-notion', title: 'Import > Notion', icon: 'file-down', handler: () => { window.location.href = '/browser/notion/import'; } }` entry in the ninja-keys commands array, near the existing "Import Vault" entry.

## Must-Haves

- [ ] Upload endpoint accepts ZIP, extracts, returns scan trigger
- [ ] Scan endpoint triggers NotionScanner, persists scan_result.json, returns results partial
- [ ] SSE stream delivers scan_progress and scan_complete events
- [ ] Scan results show databases with column summaries (name, type badge, samples)
- [ ] Scan results show standalone pages list
- [ ] Scan results show detected relations table
- [ ] Discard endpoint cleans up import directory
- [ ] Router wired into main.py and accessible at /browser/notion/import
- [ ] Sidebar has "Import Notion" link
- [ ] Command palette has "Import > Notion" entry

## Verification

- Docker stack: navigate to `/browser/notion/import` — see upload form
- Upload a test ZIP (create a small synthetic one manually or use the T01 test helper pattern to build one) — see scan results
- Check SSE events in browser Network tab during scan
- Verify sidebar shows "Import Notion" link
- Verify command palette (Ctrl+K) shows "Import > Notion"
- `cd /home/james/Code/SemPKM/backend && python -m pytest tests/test_notion_scanner.py -v` — still passes (no regressions)

## Inputs

- `backend/app/notion/models.py` — NotionScanResult and related dataclasses (from T01)
- `backend/app/notion/scanner.py` — NotionScanner class (from T01)
- `backend/app/obsidian/router.py` — reference implementation for upload/scan/stream/discard endpoints
- `backend/app/obsidian/broadcast.py` — copy source for SSE broadcast
- `backend/app/templates/obsidian/` — reference templates for wizard UI structure
- `frontend/static/css/import.css` — shared import wizard CSS (already exists)

## Expected Output

- `backend/app/notion/broadcast.py` — SSE broadcast helper (adapted copy)
- `backend/app/notion/router.py` — FastAPI router with 6 endpoints
- `backend/app/templates/notion/import.html` — main import page
- `backend/app/templates/notion/partials/upload_form.html` — upload form partial
- `backend/app/templates/notion/partials/scan_trigger.html` — scan trigger partial
- `backend/app/templates/notion/partials/scan_results.html` — scan results display
- `backend/app/templates/notion/partials/step_bar.html` — 7-step wizard bar
- `backend/app/main.py` — modified to include notion router
- `backend/app/templates/components/_sidebar.html` — modified with "Import Notion" link
- `frontend/static/js/workspace.js` — modified with command palette entry
