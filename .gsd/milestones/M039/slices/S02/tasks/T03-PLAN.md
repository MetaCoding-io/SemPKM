---
estimated_steps: 5
estimated_files: 8
skills_used:
  - frontend-design
  - accessibility
  - best-practices
---

# T03: Build import wizard templates, sidebar entry, command palette, and dockview tab

**Slice:** S02 — RDF Data Import Wizard
**Milestone:** M039

## Description

Build the user-facing HTML templates for the 3-step import wizard and wire the feature into the workspace — sidebar navigation, command palette, and dockview tab opening. This follows established patterns from the Obsidian and Notion importers.

## Steps

1. **Create the main import page template** at `backend/app/templates/rdf_import/import.html`:
   - Extend `base.html`. Include `<link rel="stylesheet" href="/css/import.css">` (NOT `/static/css/` — per KNOWLEDGE.md, nginx serves `/css/` not `/static/`).
   - Define a 3-step bar (Input / Preview / Import) using the same `.import-step-bar` CSS classes from the obsidian importer. Reference `backend/app/templates/obsidian/partials/step_bar.html` for the pattern but hardcode the 3 steps inline (no need for a separate partial with only 3 steps).
   - Wrap content in `<div id="import-container">` → `<div id="import-area">` for htmx swap targets.
   - Include the input form partial by default: `{% include "rdf_import/partials/input_form.html" %}`.

2. **Create the input form partial** at `backend/app/templates/rdf_import/partials/input_form.html`:
   - Textarea with id `rdf-paste-area`, placeholder showing example Turtle syntax, large enough (min-height 200px).
   - File upload: `<input type="file" accept=".jsonld,.json,.ttl,.nt,.nq,.rdf,.xml">` styled with `.import-upload-zone` class.
   - Format override `<select>` with options: Auto-detect (default), JSON-LD, Turtle, N-Triples.
   - Submit button "Parse & Preview" that htmx POSTs to `/browser/rdf-import/parse` with `hx-target="#import-area"` and `hx-swap="innerHTML"`. Use `hx-encoding="multipart/form-data"` for file upload support.
   - Include `hx-indicator` for loading state.

3. **Create the preview partial** at `backend/app/templates/rdf_import/partials/preview.html`:
   - Update step bar to show step 2 active.
   - Subject table with columns: checkbox (for selective import), IRI (truncated with tooltip for full IRI), Type(s), Label, Properties (count), SHACL Status (✓ for valid, ⚠ for warnings, ✗ for errors).
   - "Select All" / "Deselect All" toggle at table header.
   - If SHACL validation found issues, show a summary line like "3 subjects have validation warnings".
   - If IRI collisions detected, show warning with list of existing IRIs, checkboxes unchecked by default for those.
   - "Import Selected" button that htmx POSTs to `/browser/rdf-import/execute` with the selected IRIs as form data, targeting `#import-area`.
   - "Back" button to return to input form.
   - If parse errors occurred, show the error messages in a red notice div instead of the table.

4. **Create progress and summary partials**:
   - `backend/app/templates/rdf_import/partials/progress.html`: Update step bar to step 3. Show "Importing..." heading. Progress bar with `.import-progress-bar-track` + `.import-progress-fill`. Phase text div. Counter div. Log div. JavaScript `EventSource` connecting to `/browser/rdf-import/execute/stream`. Handle `import_progress` (update bar, phase, counter, log), `import_complete` (close source, htmx fetch summary), `import_error` (close source, show error). Follow the exact pattern from `backend/app/templates/obsidian/partials/import_progress.html`.
   - `backend/app/templates/rdf_import/partials/summary.html`: Update step bar to step 3 (complete). Stat cards for Created / Skipped / Errors / Duration using `.import-stat-cards` CSS. "Browse Objects" button navigating to `/workspace`. "Import More" button htmx-loading the input form again. Follow pattern from `backend/app/templates/obsidian/partials/import_summary.html`.

5. **Wire into workspace** — three integration points:
   - **Sidebar** (`backend/app/templates/components/_sidebar.html`): Add entry after the "Import Notion" link (after line 117). Use `<a href="/browser/rdf-import" class="nav-link" data-tooltip="Import RDF" hx-boost="false">` with `<i data-lucide="file-code-2" class="nav-icon"></i>` and `<span class="nav-label">Import RDF</span>`.
   - **Command palette** (`frontend/static/js/workspace.js`): Add entry after the `import-notion` entry (after line ~1512): `{id: 'import-rdf', title: 'Import > RDF Data', section: 'Navigation', handler: function() { openRdfImportTab(); }}`.
   - **Dockview tab** (`frontend/static/js/workspace.js`): Add `openRdfImportTab()` function after `openImportTab()` (after line ~980). Follow the exact same pattern: create tab with `id: 'special:rdf-import'`, `component: 'special-panel'`, `params: { specialType: 'rdf-import', isView: false, isSpecial: true }`, `title: 'Import RDF'`. The `special-panel` component already maps `specialType` to URL via `'/browser/' + st`, so `specialType: 'rdf-import'` → URL `/browser/rdf-import`. Expose as `window.openRdfImportTab = openRdfImportTab;`.

## Must-Haves

- [ ] Main import page extends `base.html` and loads `/css/import.css`
- [ ] 3-step wizard bar renders correctly (Input / Preview / Import)
- [ ] Input form supports both paste and file upload with format override
- [ ] Preview table shows subject IRI, types, label, property count, SHACL status
- [ ] Preview handles parse errors gracefully with user-visible message
- [ ] Progress partial connects to SSE stream and shows live progress
- [ ] Summary partial shows stat cards with created/skipped/errors/duration
- [ ] Sidebar "Import RDF" entry appears after "Import Notion"
- [ ] Command palette "Import > RDF Data" entry opens the import tab
- [ ] `openRdfImportTab()` creates a dockview tab loading `/browser/rdf-import`
- [ ] All Lucide icons in flex containers have `flex-shrink: 0` via CSS (use existing `.import-section-title svg` rules)

## Verification

- `test -f backend/app/templates/rdf_import/import.html && test -f backend/app/templates/rdf_import/partials/input_form.html && test -f backend/app/templates/rdf_import/partials/preview.html && test -f backend/app/templates/rdf_import/partials/progress.html && test -f backend/app/templates/rdf_import/partials/summary.html && echo "All templates exist"`
- `grep -n "rdf-import" backend/app/templates/components/_sidebar.html` returns a match
- `grep -n "openRdfImportTab" frontend/static/js/workspace.js` returns matches for both function definition and command palette handler
- `grep -n "import-rdf" frontend/static/js/workspace.js` returns command palette entry
- `grep -c "/static/css/" backend/app/templates/rdf_import/import.html` returns 0 (no wrong paths)

## Inputs

- `backend/app/rdf_import/router.py` — endpoint paths for htmx targets (from T02)
- `backend/app/rdf_import/models.py` — `SubjectInfo`, `RdfParseResult` fields for template rendering (from T01)
- `backend/app/templates/obsidian/partials/step_bar.html` — step bar pattern reference
- `backend/app/templates/obsidian/partials/import_progress.html` — SSE progress pattern reference
- `backend/app/templates/obsidian/partials/import_summary.html` — summary stat cards pattern reference
- `frontend/static/css/import.css` — shared import styling classes
- `frontend/static/js/workspace.js` — `openImportTab()` pattern reference, command palette entries
- `backend/app/templates/components/_sidebar.html` — sidebar navigation entries

## Expected Output

- `backend/app/templates/rdf_import/import.html` — main import page
- `backend/app/templates/rdf_import/partials/input_form.html` — paste/upload form
- `backend/app/templates/rdf_import/partials/preview.html` — subject preview table with SHACL status
- `backend/app/templates/rdf_import/partials/progress.html` — SSE-driven progress bar
- `backend/app/templates/rdf_import/partials/summary.html` — post-import stat cards
- `backend/app/templates/components/_sidebar.html` — modified with "Import RDF" entry
- `frontend/static/js/workspace.js` — modified with `openRdfImportTab()` and command palette entry

## Observability Impact

- **SSE connection:** The progress partial opens an `EventSource` to `/browser/rdf-import/execute/stream`. Agent can verify SSE connectivity by checking browser console for connection events or network logs for the EventSource request.
- **Step bar state:** The wizard step bar visually tracks progress (Input → Preview → Import). Each partial updates the step bar via DOM replacement. Agent can verify step transitions by checking which `.step-active` / `.step-complete` classes are present.
- **Error surface:** Parse errors render in a red notice div via `error.html` partial. SHACL validation issues and IRI collisions are highlighted in the preview table. Agent can inspect these via `browser_find` for `.import-info-notice` elements.
- **Import summary:** Stat cards (Created/Skipped/Errors/Duration) provide at-a-glance import outcome. Agent can verify via `browser_find` for `.import-stat-card` elements.
