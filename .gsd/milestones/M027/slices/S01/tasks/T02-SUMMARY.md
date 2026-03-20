---
id: T02
parent: S01
milestone: M027
provides:
  - FastAPI router at /browser/notion/ with 6 endpoints (import page, upload, scan, stream, discard, results)
  - SSE broadcast for real-time scan progress streaming
  - 7-step wizard UI (Upload, Scan, Types, Properties, Relations, Preview, Import)
  - Scan results display showing databases with column summaries, standalone pages, detected relations, and warnings
  - Sidebar "Import Notion" navigation entry
  - Command palette "Import > Notion" entry
key_files:
  - backend/app/notion/router.py
  - backend/app/notion/broadcast.py
  - backend/app/templates/notion/import.html
  - backend/app/templates/notion/partials/scan_results.html
  - backend/app/templates/notion/partials/scan_trigger.html
  - backend/app/templates/notion/partials/upload_form.html
  - backend/app/templates/notion/partials/step_bar.html
key_decisions:
  - Updated scanner import from obsidian.broadcast to notion.broadcast for module self-containment
  - Fixed scan_trigger to execute inline scripts after innerHTML set (OOB step bar replacement)
  - Removed icon property from command palette entry (ninja-keys renders icon text literally, not as Lucide SVG)
  - "Continue to Type Mapping" button rendered as disabled placeholder — S02 will enable it
patterns_established:
  - Notion import wizard reuses shared import.css and follows same htmx partial-swap pattern as Obsidian
  - scan_trigger uses fetch() + innerHTML + manual script execution for scan results, matching Obsidian flow
observability_surfaces:
  - SSE events (scan_progress, scan_complete, scan_error) via /browser/notion/scan/{id}/stream
  - scan_result.json persisted at /app/data/imports/notion/{user_id}/{timestamp}/
  - HTTP request logs for all notion endpoints visible in docker compose logs
  - ScanWarning objects rendered in scan results UI for parse errors
duration: 45m
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T02: Router, templates, broadcast, and wiring

**Built Notion import wizard UI with upload → scan → results flow, SSE progress streaming, sidebar link, and command palette entry at /browser/notion/import**

## What Happened

Copied and adapted the Obsidian SSE broadcast module for the Notion import package. Built a FastAPI router with 6 endpoints following the Obsidian pattern but at `/browser/notion/` prefix and using `NotionScanResult` models.

Created the main import page template and 4 partials: upload form (drag-and-drop + file select), scan trigger (progress bar + SSE), step bar (7 steps vs Obsidian's 6), and scan results (stat cards, database column tables, standalone pages list, detected relations table, warnings section).

The scan results partial is the main S01 deliverable — it shows each database's columns with inferred type badges, non-empty counts, and sample values. Detected cross-database relations display source → column → target with match ratio.

Wired the router into main.py, added "Import Notion" to the sidebar and "Import > Notion" to the command palette.

Fixed a step bar duplication bug: the scan_trigger template uses raw `fetch()` + `innerHTML` to inject scan results, which doesn't auto-execute inline `<script>` tags. Added manual script execution to make the OOB step bar replacement work correctly.

Updated the scanner to import from the local `notion.broadcast` module instead of `obsidian.broadcast`, making the notion package self-contained.

## Verification

- **Upload form visible:** Navigated to `/browser/notion/import` — upload form with 7-step wizard bar renders correctly
- **Upload + scan flow:** Uploaded synthetic Notion ZIP with 3 databases, 2 standalone pages, 1 cross-DB relation — scan results showed all correctly
- **Stat cards:** 3 Databases, 2 Pages, 1 Relations, 3 CSV Files
- **Database columns:** Expanded People database — Name (select), Email (select), Role (select) with sample values
- **Detected relations:** Projects → Lead → People at 100% match ratio
- **Discard flow:** Clicked "Discard Import" — returned to upload form
- **Sidebar:** "Import Notion" link visible below "Import Vault"
- **Command palette:** Ctrl+K, type "Notion" → "Import > Notion" appears under Navigation section
- **Scanner tests:** 31/31 tests pass (no regressions from broadcast import change)
- **SSE stream:** GET /browser/notion/scan/{id}/stream returned 200 (visible in API logs)
- **Persisted state:** scan_result.json found at expected path in container

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `docker compose exec -T api python -m pytest tests/test_notion_scanner.py -v` | 0 | ✅ pass | 3.4s |
| 2 | `curl -s -o /dev/null -w "%{http_code}" http://localhost:3000/browser/notion/import` | 0 (200) | ✅ pass | <1s |
| 3 | Browser: upload synthetic ZIP → scan results with 3 DBs, 2 pages, 1 relation | — | ✅ pass | — |
| 4 | Browser: sidebar shows "Import Notion" link | — | ✅ pass | — |
| 5 | Browser: command palette shows "Import > Notion" | — | ✅ pass | — |
| 6 | Browser: discard returns to upload form | — | ✅ pass | — |
| 7 | `browser_assert`: 7/7 text visibility checks passed | — | ✅ pass | — |

## Diagnostics

- **Import state:** `GET /browser/notion/import` shows current state (upload form, scan trigger, or results based on persisted state)
- **Scan results JSON:** `docker compose exec api cat /app/data/imports/notion/{user_id}/{timestamp}/scan_result.json`
- **API logs:** `docker compose logs api | grep notion` shows all endpoint hits
- **Active scans:** Check `_broadcasts` dict in `backend/app/notion/router.py` for active SSE streams
- **Scan warnings:** Visible in the "Warnings" section of scan results UI, also in `scan_result.json` `warnings` array

## Deviations

- Updated `scanner.py` import from `..obsidian.broadcast` to `.broadcast` — makes notion module self-contained (not in plan but good hygiene)
- Added manual inline script execution in `scan_trigger.html` — the plan didn't anticipate that `innerHTML =` doesn't execute `<script>` tags, causing duplicate step bars
- Removed `icon: 'file-down'` from command palette entry — ninja-keys renders it as literal text prefix, not as an icon

## Known Issues

- The Obsidian import's scan_trigger has the same duplicate step bar bug (scripts don't execute when set via innerHTML). Not fixed in this task since it's outside scope.

## Files Created/Modified

- `backend/app/notion/broadcast.py` — SSE broadcast helper (adapted copy from Obsidian)
- `backend/app/notion/router.py` — FastAPI router with 6 endpoints for upload/scan/stream/discard/results
- `backend/app/notion/scanner.py` — Updated import from local broadcast module
- `backend/app/templates/notion/import.html` — Main import page template
- `backend/app/templates/notion/partials/step_bar.html` — 7-step wizard bar
- `backend/app/templates/notion/partials/upload_form.html` — Upload form with drag-and-drop
- `backend/app/templates/notion/partials/scan_trigger.html` — Scan trigger with SSE progress and script execution fix
- `backend/app/templates/notion/partials/scan_results.html` — Scan results display (databases, pages, relations, warnings)
- `backend/app/main.py` — Added notion router import and inclusion
- `backend/app/templates/components/_sidebar.html` — Added "Import Notion" nav link
- `frontend/static/js/workspace.js` — Added "Import > Notion" command palette entry
