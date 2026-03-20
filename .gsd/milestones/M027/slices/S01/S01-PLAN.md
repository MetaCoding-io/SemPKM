# S01: Notion ZIP Scanner + Upload UI

**Goal:** Build the Notion ZIP scanner (CSV parsing, ID stripping, column type inference, cross-database relation detection) and the upload/scan results UI, following the Obsidian import wizard pattern.
**Demo:** User navigates to Admin > Import > Notion, uploads a Notion workspace ZIP export, and sees scan results showing detected databases with column summaries (column names, inferred types, row counts), standalone markdown pages, and cross-database relation candidates.

## Must-Haves

- NotionScanner parses CSV files from Notion ZIP exports with `encoding='utf-8-sig'` for BOM handling
- Notion ID stripping regex matches exactly 32 hex chars preceded by a space (`r'\s+[0-9a-f]{32}$'`)
- Column type inference: Select, Multi-select, Date, Checkbox, URL, Number, Relation, Text
- Cross-database relation detection: column values that are >80% subset of another DB's row titles
- Standalone page detection: `.md` files not inside a database folder
- Upload endpoint accepts ZIP, extracts, and stores per-user
- Scan results UI shows databases with column summaries, standalone pages, and detected relations
- SSE progress events during scan
- Entry point at `/browser/notion/import` (separate from Obsidian import at `/browser/import`)

## Proof Level

- This slice proves: contract (scanner logic) + integration (upload → scan → results UI)
- Real runtime required: yes (Docker stack for upload/scan verification)
- Human/UAT required: no

## Verification

- `cd backend && python -m pytest tests/test_notion_scanner.py -v` — all scanner unit tests pass (CSV parsing, ID stripping, column type inference, relation detection, standalone page detection, empty cells, BOM handling)
- Docker stack: upload a synthetic Notion ZIP at `/browser/notion/import`, see scan results with database summaries, standalone pages, and detected relations

## Observability / Diagnostics

- Runtime signals: SSE events (`scan_progress`, `scan_complete`, `scan_error`) with scanned/total counts and current file
- Inspection surfaces: `scan_result.json` persisted in `/app/data/imports/{user_id}/{timestamp}/` after scan completes
- Failure visibility: `ScanWarning` objects in scan result (malformed CSV, empty database, parse errors per file)
- Redaction constraints: none (no secrets in Notion exports)

## Integration Closure

- Upstream surfaces consumed: `backend/app/obsidian/broadcast.py` (copy-and-adapt), `frontend/static/css/import.css` (shared styling), `backend/app/templates/obsidian/partials/step_bar.html` (adapted copy), `backend/app/main.py` (router inclusion)
- New wiring introduced: `backend/app/notion/` module with router included in main.py, sidebar link, command palette entry
- What remains before the milestone is truly usable end-to-end: S02 (type/property/relation mapping + preview), S03 (two-pass executor), S04 (E2E tests + docs)

## Tasks

- [ ] **T01: Notion data models, scanner, and unit tests** `est:2h`
  - Why: The scanner is the novel, riskiest code in this slice — CSV parsing, Notion ID stripping, column type inference, and cross-database relation detection must be proven correct before building any UI on top
  - Files: `backend/app/notion/__init__.py`, `backend/app/notion/models.py`, `backend/app/notion/scanner.py`, `backend/tests/test_notion_scanner.py`
  - Do: Create the `notion` package. Define dataclasses in models.py (NotionScanResult, NotionDatabase, NotionColumn, NotionPage, DetectedRelation, ScanWarning). Implement NotionScanner with `scan(zip_path)` using asyncio.to_thread wrapping sync logic. Build comprehensive unit tests with synthetic fixture data covering: BOM-encoded CSV, column type inference for all 8 types, Notion ID stripping (32 hex chars only), cross-DB relation detection (>80% title overlap), standalone page detection, empty cells, nested folders, warnings for malformed CSVs.
  - Verify: `cd backend && python -m pytest tests/test_notion_scanner.py -v` — all tests pass
  - Done when: ≥20 unit tests covering all scanner behaviors pass. NotionScanResult.to_dict()/from_dict() round-trips correctly.

- [ ] **T02: Router, templates, broadcast, and wiring** `est:2h`
  - Why: Connects the scanner to the web UI — upload page, scan trigger, scan results display, SSE progress, sidebar nav entry, and command palette entry. Without this, the scanner is a library with no user-facing surface.
  - Files: `backend/app/notion/router.py`, `backend/app/notion/broadcast.py`, `backend/app/main.py`, `backend/app/templates/notion/import.html`, `backend/app/templates/notion/partials/upload_form.html`, `backend/app/templates/notion/partials/scan_trigger.html`, `backend/app/templates/notion/partials/scan_results.html`, `backend/app/templates/notion/partials/step_bar.html`, `backend/app/templates/components/_sidebar.html`, `frontend/static/js/workspace.js`
  - Do: Copy and adapt broadcast.py from Obsidian. Build router with upload, scan, scan-stream, discard, and results endpoints mirroring Obsidian pattern but at `/browser/notion/` prefix. Create import.html page and partials (upload form, scan trigger, scan results showing database tables with column summaries, standalone pages list, detected relations section). Adapt step bar for Notion wizard steps (Upload → Scan → Types → Properties → Relations → Preview → Import). Wire router into main.py. Add "Import Notion" sidebar link. Add "Import > Notion" command palette entry. Reuse existing `import.css` for shared styling.
  - Verify: Docker stack: navigate to `/browser/notion/import`, see upload form. Upload a test ZIP, see scan results with database summaries and relation candidates. SSE progress events visible in browser dev tools during scan.
  - Done when: Full upload → scan → results flow works in browser. Sidebar has "Import Notion" link. Command palette has "Import > Notion" entry.

## Files Likely Touched

- `backend/app/notion/__init__.py`
- `backend/app/notion/models.py`
- `backend/app/notion/scanner.py`
- `backend/app/notion/broadcast.py`
- `backend/app/notion/router.py`
- `backend/tests/test_notion_scanner.py`
- `backend/app/main.py`
- `backend/app/templates/notion/import.html`
- `backend/app/templates/notion/partials/upload_form.html`
- `backend/app/templates/notion/partials/scan_trigger.html`
- `backend/app/templates/notion/partials/scan_results.html`
- `backend/app/templates/notion/partials/step_bar.html`
- `backend/app/templates/components/_sidebar.html`
- `frontend/static/js/workspace.js`
