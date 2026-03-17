---
id: T01
parent: S01
milestone: M012
provides:
  - ShapesService.get_labels_for_predicates() method
  - ShapesService.get_helptext_for_predicates() method
  - Predicate label/helptext resolution in event_detail() route
  - Human-readable predicate labels in event detail template
key_files:
  - backend/app/services/shapes.py
  - backend/app/browser/events.py
  - backend/app/templates/browser/event_detail.html
  - frontend/static/css/workspace.css
  - backend/tests/test_event_log_labels.py
key_decisions:
  - Used ShapesService (not LabelService) for predicate labels — vocabulary terms live in shapes/ontology graphs, not urn:sempkm:current
patterns_established:
  - SHACL property shape iteration for predicate metadata extraction (reusable for future predicate-level UI enrichment)
observability_surfaces:
  - logger.warning on shapes graph query failure in get_labels_for_predicates() and get_helptext_for_predicates()
  - HTML title attribute on every .diff-pred-label shows helptext or full IRI for debugging
  - Visual indicator: resolved labels use capitalized sh:name (e.g. "Title"), fallback shows lowercase local name (e.g. "title")
duration: 45min
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Wire predicate labels and helptext tooltips into event detail view

**Added SHACL-aware predicate label resolution and helptext tooltips to event detail diff view**

## What Happened

1. Added two new methods to `ShapesService`:
   - `get_labels_for_predicates(iris)` — iterates sh:PropertyShape nodes, matches sh:path to requested IRIs, extracts sh:name → rdfs:label → local name. Returns `{iri: human_label}`.
   - `get_helptext_for_predicates(iris)` — same iteration, extracts sempkm:editHelpText (preferred) → sh:description. Returns `{iri: helptext}`.
   - Both wrapped in try/except with `logger.warning` for graceful degradation.

2. Updated `event_detail()` route in `events.py`:
   - Added `ShapesService` and `LabelService` as FastAPI dependencies
   - Collects all predicate IRIs from `detail.new_values` and `detail.data_triples`
   - Resolves labels and helptext via ShapesService, with LabelService fallback for unresolved predicates
   - Passes `predicate_labels` and `predicate_helptext` dicts to template context

3. Updated `event_detail.html` template:
   - Both property diff table and creation display use `predicate_labels.get(pred_iri, local_name_fallback)`
   - Added `title` attribute showing helptext (if available) or full IRI for transparency
   - Added `has-helptext` CSS class for visual indicator

4. Added CSS in `workspace.css`:
   - `.diff-pred-label[title]` gets `cursor: help`
   - `.diff-pred-label.has-helptext` gets dotted underline via `text-decoration`

## Verification

- **Unit tests:** 14/14 passed in `test_event_log_labels.py` — covers label resolution (sh:name, rdfs:label fallback, unknown predicates, empty input, error graceful degradation, empty shapes graph) and helptext extraction (editHelpText preference, sh:description fallback, no-helptext shapes, error handling, multiple predicates)
- **Existing tests:** No pre-existing shapes-specific tests to regress against; all collected tests pass
- **LSP diagnostics:** No real code errors (only missing-package warnings from absent host venv — all imports resolve correctly in Docker)
- **Browser testing:** Not fully exercised end-to-end due to M012 worktree Docker stack triplestore lock issue (RepositoryLockedException on fresh volume creation). The main stack serves the modified code via volume mounts and the API starts healthy, confirming no import/startup errors from our changes.

## Diagnostics

- Hover any `.diff-pred-label` in event detail view to see helptext or full predicate IRI
- Check backend logs for `"Failed to resolve predicate labels from shapes graph"` or `"Failed to resolve predicate helptext from shapes graph"` warnings to diagnose shapes query failures
- Resolved labels show capitalized names (e.g. "Title") vs fallback lowercase local names (e.g. "title") — visual indicator of resolution status

## Deviations

None — implementation matches the task plan.

## Known Issues

- **M012 Docker stack cannot start fresh:** The triplestore gets a `RepositoryLockedException` on fresh volume creation because the rdf4j-workbench process holds a lock on the repository that the API also needs during setup. This is a pre-existing infrastructure issue, not caused by this task's changes. The main development stack works fine with the code. Browser E2E verification of the event detail diff view should be done in T03 or when the stack issue is resolved.
- Slice verification items `test_event_suggestions.py` and autocomplete UI are for T02/T03, not this task.

## Files Created/Modified

- `backend/app/services/shapes.py` — added `get_labels_for_predicates()` and `get_helptext_for_predicates()` methods (~102 lines)
- `backend/app/browser/events.py` — added shapes/label resolution to `event_detail()` route, new imports for ShapesService
- `backend/app/templates/browser/event_detail.html` — uses `predicate_labels` and `predicate_helptext` dicts, adds title attributes and has-helptext class
- `frontend/static/css/workspace.css` — added `.diff-pred-label[title]` and `.diff-pred-label.has-helptext` styling
- `backend/tests/test_event_log_labels.py` — new test file with 14 tests for label/helptext resolution
- `.gsd/milestones/M012/slices/S01/tasks/T01-PLAN.md` — added Observability Impact section
