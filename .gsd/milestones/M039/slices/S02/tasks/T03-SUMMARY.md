---
id: T03
parent: S02
milestone: M039
provides:
  - 3-step RDF import wizard templates (input, preview, progress, summary, error)
  - Sidebar "Import RDF" entry in Apps section
  - Command palette "Import > RDF Data" entry
  - Dockview tab opener function openRdfImportTab()
key_files:
  - backend/app/templates/rdf_import/import.html
  - backend/app/templates/rdf_import/partials/input_form.html
  - backend/app/templates/rdf_import/partials/preview.html
  - backend/app/templates/rdf_import/partials/progress.html
  - backend/app/templates/rdf_import/partials/summary.html
  - backend/app/templates/rdf_import/partials/error.html
  - backend/app/templates/components/_sidebar.html
  - frontend/static/js/workspace.js
key_decisions: []
patterns_established:
  - RDF import wizard reuses shared import CSS classes (import-step-bar, import-stat-cards, import-progress-*, import-section-title) from the obsidian importer — no duplicate CSS
  - Step bar is inlined in import.html (3 steps only) rather than a separate partial, with OOB replacement pattern for step transitions in htmx partials
  - Error partial renders as a styled notice div with Back button, same target swap pattern as other partials
observability_surfaces:
  - SSE EventSource in progress.html connects to /browser/rdf-import/execute/stream for live import progress
  - Step bar class transitions (step-active → step-complete) track wizard state visually
  - Error notices in .import-info-notice elements surface parse errors, SHACL issues, and IRI collisions
  - Summary stat cards (.import-stat-card) show created/skipped/errors/duration
duration: 12m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T03: Build import wizard templates, sidebar entry, command palette, and dockview tab

**Built 6 RDF import wizard templates (main page, input form, preview table, progress bar, summary cards, error notice), added sidebar entry, command palette command, and dockview tab opener.**

## What Happened

Created the full frontend for the RDF import wizard:

1. **import.html** — Main page extending `base.html`, loads `/css/import.css` (correct path per KNOWLEDGE.md), inlines a 3-step bar (Input / Preview / Import), and includes the input form partial by default.

2. **input_form.html** — Textarea for pasting RDF content with Turtle syntax placeholder, file upload input (accepts .jsonld, .json, .ttl, .nt, .nq, .rdf, .xml) with drag-and-drop support, format override select (Auto-detect / JSON-LD / Turtle / N-Triples), and "Parse & Preview" button posting to `/browser/rdf-import/parse` with htmx multipart encoding.

3. **preview.html** — Step 2 active. Subject table with checkbox selection, truncated IRI with tooltip, type badges, label, property count, and SHACL status icons (✓/⚠/✗). Collision warnings for existing IRIs (unchecked by default). SHACL issue summary notice. Select All toggle via header checkbox. "Import Selected" button posting selected IRIs to `/browser/rdf-import/execute`.

4. **progress.html** — Step 3 active. Progress bar with phase text, counter, and scrolling log. EventSource connects to `/browser/rdf-import/execute/stream`. Handles `import_progress`, `import_complete` (fetches summary), and `import_error` events. Follows the obsidian import_progress pattern.

5. **summary.html** — Step 3 complete. Stat cards for Created/Skipped/Errors/Duration using shared `.import-stat-cards` CSS. Error details in collapsible table. "Browse Objects" and "Import More" action buttons.

6. **error.html** — Error state partial (not in original plan but required by router from T02). Red notice with error message and "Try Again" back button.

Workspace integration:
- **Sidebar**: Added "Import RDF" entry with `file-code-2` icon after "Import Notion" in the Apps group.
- **Command palette**: Added `import-rdf` entry with title "Import > RDF Data" calling `openRdfImportTab()`.
- **Dockview tab**: Added `openRdfImportTab()` function creating a `special-panel` with `specialType: 'rdf-import'`, exposed as `window.openRdfImportTab`.

## Verification

All task-level and slice-level verification checks pass:
- All 6 template files exist (5 planned + error partial)
- Sidebar entry grep returns match at line 119
- `openRdfImportTab` appears at lines 984 (definition), 1002 (window expose), 1538 (command palette handler)
- `import-rdf` command palette entry at line 1534
- Zero `/static/css/` occurrences in import.html (correct path used)
- 29/29 parser unit tests pass (no regressions)
- Router registered in main.py at lines 34, 658
- Sidebar and workspace.js grep checks for Import RDF all return matches

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `test -f backend/app/templates/rdf_import/import.html && ... && echo "All templates exist"` | 0 | ✅ pass | <1s |
| 2 | `grep -n "rdf-import" backend/app/templates/components/_sidebar.html` | 0 | ✅ pass | <1s |
| 3 | `grep -n "openRdfImportTab" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 4 | `grep -n "import-rdf" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 5 | `grep -c "/static/css/" backend/app/templates/rdf_import/import.html` returns 0 | 0* | ✅ pass | <1s |
| 6 | `cd backend && .venv/bin/python -m pytest tests/test_rdf_import_parser.py -v` | 0 | ✅ pass | 0.09s |
| 7 | `grep -n "rdf_import_router" backend/app/main.py` | 0 | ✅ pass | <1s |
| 8 | `grep -n "import-rdf\|Import RDF\|Import.*RDF" frontend/static/js/workspace.js` | 0 | ✅ pass | <1s |
| 9 | `grep -n "rdf-import\|Import RDF" backend/app/templates/components/_sidebar.html` | 0 | ✅ pass | <1s |

*grep -c returns exit code 1 when count is 0, which is the desired outcome (no wrong paths)

## Diagnostics

- **Template existence:** `ls backend/app/templates/rdf_import/partials/`
- **Sidebar entry:** `grep -n "rdf-import" backend/app/templates/components/_sidebar.html`
- **JS function:** `grep -n "openRdfImportTab" frontend/static/js/workspace.js`
- **Command palette:** `grep -n "import-rdf" frontend/static/js/workspace.js`
- **Path correctness:** `grep -c "/static/css/" backend/app/templates/rdf_import/import.html` — should return 0

## Deviations

- Created `error.html` partial — not in the original task plan but required by the router from T02, which references `rdf_import/partials/error.html` for parse errors and empty input. Without this file, the wizard would crash on error states.
- Used `hx-select="#import-area"` on Back buttons to extract just the inner content from the full page response, rather than using a separate htmx endpoint for the input form partial.

## Known Issues

- None.

## Files Created/Modified

- `backend/app/templates/rdf_import/import.html` — Main import wizard page, extends base.html with 3-step bar
- `backend/app/templates/rdf_import/partials/input_form.html` — Paste/upload form with drag-and-drop and format override
- `backend/app/templates/rdf_import/partials/preview.html` — Subject preview table with SHACL status, collision warnings, selective import
- `backend/app/templates/rdf_import/partials/progress.html` — SSE-driven progress bar with live log
- `backend/app/templates/rdf_import/partials/summary.html` — Post-import stat cards with error details
- `backend/app/templates/rdf_import/partials/error.html` — Parse error notice with retry action
- `backend/app/templates/components/_sidebar.html` — Added "Import RDF" entry after "Import Notion"
- `frontend/static/js/workspace.js` — Added openRdfImportTab() function and "Import > RDF Data" command palette entry
- `.gsd/milestones/M039/slices/S02/tasks/T03-PLAN.md` — Added Observability Impact section
