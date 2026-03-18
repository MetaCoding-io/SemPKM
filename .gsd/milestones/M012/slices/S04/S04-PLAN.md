# S04: E2E Tests & User Guide

**Goal:** All M012 features (event log labels/helptext/autocomplete, body.diff, personas) have Playwright E2E test coverage and user guide documentation.
**Demo:** Running `cd e2e && npx playwright test tests/27-event-log-polish tests/28-body-diff tests/29-personas --project=chromium` passes all tests. User guide has updated Chapter 15 (event log improvements) and new Chapter 30 (personas) with working navigation chain.

## Must-Haves

- S01/S02 code from `milestone/M012` branch merged to `main` so all features exist in one codebase
- `e2e/tests/27-event-log-polish/event-log-polish.spec.ts` — tests predicate labels, helptext tooltips, autocomplete filters
- `e2e/tests/28-body-diff/body-diff.spec.ts` — tests body.diff rendering in event log (create body → edit body → verify diff view)
- `e2e/tests/29-personas/personas.spec.ts` — tests persona CRUD via API, default auto-creation, persona switching
- `docs/guide/15-event-log.md` updated with sections on predicate labels, helptext tooltips, autocomplete, and body.diff
- `docs/guide/30-personas.md` created with persona creation, switching, management guide
- `docs/guide/README.md` TOC updated with Chapter 30
- Navigation chain wired: Chapter 29 → Chapter 30 → Appendix A
- Glossary entries added for "Persona" and "Body Diff"

## Proof Level

- This slice proves: final-assembly (E2E integration + documentation completeness)
- Real runtime required: yes (Docker test stack for E2E)
- Human/UAT required: no

## Verification

- `cd e2e && npx playwright test tests/27-event-log-polish tests/28-body-diff tests/29-personas --project=chromium` — all tests pass (requires Docker test stack on port 3901)
- `cd e2e && npx playwright test --project=chromium` — full suite passes, no regressions
- `python -m pytest backend/tests/ -v --tb=short` — backend tests pass after merge (no regressions)
- `grep -c "Persona\|Body Diff" docs/guide/appendix-d-glossary.md` — returns ≥2
- Navigation chain: `tail -3 docs/guide/29-mental-model-catalog.md` shows `Next → Chapter 30`
- Navigation chain: `tail -3 docs/guide/30-personas.md` shows `Previous → Chapter 29` and `Next → Appendix A`
- `grep "30-personas" docs/guide/README.md` — Chapter 30 in TOC

## Integration Closure

- Upstream surfaces consumed: S01 event log polish endpoints (suggest-types, suggest-predicates, suggest-objects, event detail with labels/helptext), S02 body.diff (PUT /browser/objects/{iri}/body triggers body.diff, event detail renders diff), S03 persona API (/api/personas CRUD, /browser/personas/selector, switchPersona/createNewPersona JS functions)
- New wiring introduced in this slice: none (E2E tests and docs are additive, no code changes to the application)
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice

## Tasks

- [x] **T01: Merge S01/S02 branch code into main** `est:15m`
  - Why: S01 (event log labels/helptext/autocomplete) and S02 (body.diff) code lives only on the `milestone/M012` branch. S03 (personas) is already on `main`. All three feature sets must be in the same codebase for E2E tests to work and for the Docker test stack (which mounts from the working directory) to serve all features.
  - Files: all S01/S02 files from the branch merge
  - Do: `git merge milestone/M012` on main. Resolve any conflicts (expected: clean merge since S01/S02 and S03 touch disjoint files). Verify key files exist: `backend/app/commands/handlers/body_diff.py`, `backend/tests/test_event_log_labels.py`, `backend/tests/test_event_suggestions.py`, `backend/tests/test_body_diff.py`. Verify persona code still intact: `backend/app/persona/service.py`. Run `python -m pytest backend/tests/ --tb=short` to confirm no regressions.
  - Verify: `python -m pytest backend/tests/ --tb=short` passes with 940+ tests
  - Done when: main branch contains all S01/S02/S03 code, backend test suite passes

- [ ] **T02: E2E Playwright tests for event log polish and body.diff** `est:1h`
  - Why: Validates EVTLOG-01/02/03 and BDIFF-01/02/03 requirements with browser-level tests. Event log predicate labels, helptext tooltips, autocomplete filters, and body.diff rendering must work in the real Docker stack.
  - Files: `e2e/tests/27-event-log-polish/event-log-polish.spec.ts`, `e2e/tests/28-body-diff/body-diff.spec.ts`
  - Do: Write two spec files following established patterns from `event-log.spec.ts` and `event-undo.spec.ts`. Event log polish spec tests: (1) expand event detail → verify predicate labels show human-readable text (e.g. "Title" not raw IRI), (2) verify helptext title attributes exist on predicate labels, (3) focus operation type filter → verify autocomplete dropdown appears, (4) type in predicate filter → verify filtered suggestions appear. Body diff spec tests: (1) create object with body via API, (2) edit body to different content via API, (3) open event log → expand latest event → verify body.diff renders with green/red highlighting. Use `ownerPage`, `ownerRequest`, `waitForWorkspace`, `waitForIdle` from fixtures/helpers.
  - Verify: `cd e2e && npx playwright test tests/27-event-log-polish tests/28-body-diff --project=chromium` (requires Docker test stack)
  - Done when: Both spec files exist with ≥3 tests each covering the documented feature surfaces

- [ ] **T03: E2E Playwright tests for personas** `est:45m`
  - Why: Provides E2E browser coverage for persona CRUD, auto-creation, and switching (PERSONA-01 through PERSONA-05). While already validated via unit tests and curl, E2E tests exercise the full browser flow.
  - Files: `e2e/tests/29-personas/personas.spec.ts`
  - Do: Write spec file following patterns from `named-layouts.spec.ts` (similar concept — save/restore workspace state). Tests: (1) API-level CRUD — create persona, list, rename, delete via ownerRequest, (2) default persona auto-creation — navigate to workspace, verify GET /api/personas returns at least one persona, (3) persona selector visible in sidebar — open user popover, verify persona selector UI appears, (4) command palette entries — open palette with Alt+K, verify persona commands exist, (5) persona switch — create second persona via API, call switchPersona() in browser, verify active persona changes.
  - Verify: `cd e2e && npx playwright test tests/29-personas --project=chromium` (requires Docker test stack)
  - Done when: Spec file exists with ≥4 tests covering persona CRUD, auto-creation, UI presence, and switching

- [ ] **T04: User guide documentation for event log improvements and personas** `est:1h`
  - Why: Closes the documentation gap for all M012 features. Users need guidance on the new event log capabilities and the persona system.
  - Files: `docs/guide/15-event-log.md`, `docs/guide/30-personas.md`, `docs/guide/README.md`, `docs/guide/29-mental-model-catalog.md`, `docs/guide/appendix-d-glossary.md`
  - Do: (1) Update Chapter 15 — add sections for predicate labels, helptext tooltips, autocomplete filters, body.diff operation type (add to operation types table), and diff rendering. (2) Create Chapter 30 — cover persona concepts, creating a persona, saving persona state, switching personas (sidebar + command palette), renaming and deleting personas, default persona behavior. (3) Update README.md TOC — add Chapter 30 under Part VIII. (4) Update navigation chain — Chapter 29 Next → Chapter 30, Chapter 30 Previous → Chapter 29 / Next → Appendix A. (5) Add glossary entries for "Persona" (named workspace configuration) and "Body Diff" (incremental body change).
  - Verify: `grep "30-personas" docs/guide/README.md`, `tail -3 docs/guide/29-mental-model-catalog.md` shows Next → Chapter 30, `grep -c "Persona\|Body Diff" docs/guide/appendix-d-glossary.md` ≥ 2
  - Done when: All docs files pass verification checks, Chapter 30 exists with full content, Chapter 15 has 4 new sections

## Observability / Diagnostics

**Runtime signals:**
- Backend test suite count and pass/fail (`python -m pytest backend/tests/ --tb=short` — expect 940+ tests, 0 failures)
- E2E test suite results (`cd e2e && npx playwright test --project=chromium` — full suite pass/fail)
- Docker test stack health: `curl -s http://localhost:3901/api/health` returns 200

**Inspection surfaces:**
- Conflict marker scan: `grep -rn "^<<<<<<< " backend/ frontend/ --include="*.py" --include="*.html" --include="*.js" --include="*.css"` — must return empty
- Feature file presence: `test -f backend/app/commands/handlers/body_diff.py`, `test -f backend/app/persona/service.py`, `grep -c "suggest-types" backend/app/browser/events.py`
- Documentation completeness: `grep "30-personas" docs/guide/README.md`, `grep -c "Persona\|Body Diff" docs/guide/appendix-d-glossary.md`

**Failure visibility:**
- Merge conflicts surface as non-zero exit from `git merge` and are visible via `git diff --check`
- Test regressions surface as pytest failures with `--tb=short` tracebacks
- E2E failures produce Playwright HTML reports in `e2e/playwright-report/`
- Missing navigation chain links detected by `tail -3` checks on chapter files

**Redaction constraints:** None — this slice has no secrets or PII.

## Files Likely Touched

- `e2e/tests/27-event-log-polish/event-log-polish.spec.ts` (new)
- `e2e/tests/28-body-diff/body-diff.spec.ts` (new)
- `e2e/tests/29-personas/personas.spec.ts` (new)
- `docs/guide/15-event-log.md` (updated)
- `docs/guide/30-personas.md` (new)
- `docs/guide/README.md` (updated)
- `docs/guide/29-mental-model-catalog.md` (nav chain)
- `docs/guide/appendix-d-glossary.md` (new entries)
