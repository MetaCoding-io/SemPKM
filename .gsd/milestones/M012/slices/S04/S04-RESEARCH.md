# S04: E2E Tests & User Guide — Research

**Date:** 2026-03-17
**Status:** Complete

## Summary

S04 is trailing coverage for the three feature slices (S01, S02, S03). It has two deliverables: (1) Playwright E2E tests covering event log labels/helptext/autocomplete, body.diff rendering, and persona CRUD/switch, and (2) user guide documentation — updating the existing Chapter 15 (Event Log) and creating a new Chapter 30 (Personas). All the code to test is already implemented across `milestone/M012` branch (S01, S02) and `main` (S03). This is straightforward work using well-established E2E test patterns and documentation conventions.

The E2E test infrastructure is mature: `e2e/fixtures/auth.ts` provides `ownerPage`, `ownerRequest`, and `memberPage` fixtures with session-cookie authentication. `e2e/helpers/wait-for.ts` has htmx-specific wait helpers. Test files at `e2e/tests/06-settings/event-log.spec.ts` and `event-undo.spec.ts` already test the event log UI, providing clear patterns to extend. The user guide has 29 chapters + 6 appendices following consistent markdown formatting with navigation chains.

**Critical note:** S01 and S02 code lives on the `milestone/M012` branch, not `main`. S03 is on `main`. The Docker test stack must have all three slices' code merged before E2E tests can pass. The planner must ensure the test environment builds from code that includes all three feature branches.

## Recommendation

Split into three tasks:

1. **E2E Playwright tests** — One spec file per feature area: `event-log-polish.spec.ts` (S01 features), `body-diff.spec.ts` (S02 features), `personas.spec.ts` (S03 features). Each follows the established pattern: API-level data arrangement → browser assertions. Keep tests sequential (shared Docker state).

2. **User guide updates** — Update `docs/guide/15-event-log.md` with three new sections (predicate labels, helptext tooltips, autocomplete filters, body.diff). Create `docs/guide/30-personas.md` covering persona creation, switching, management. Update `docs/guide/README.md` TOC. Update navigation chains on adjacent chapters. Add glossary entries for "Persona" and "Body Diff" to `appendix-d-glossary.md`.

3. **Requirement validation** — Mark EVTLOG-01/02/03, BDIFF-01/02/03 as validated after E2E tests pass. PERSONA-01-05 are already validated from S03 but benefit from E2E coverage.

## Implementation Landscape

### Key Files

**E2E test infrastructure (read-only — follow patterns, don't modify):**
- `e2e/fixtures/auth.ts` — `ownerPage` (authenticated browser), `ownerRequest` (API context), `memberPage`. Pattern: fixtures auto-handle setup + login.
- `e2e/helpers/wait-for.ts` — `waitForWorkspace()`, `waitForIdle()`, `waitForHtmxSettle()`. Required for htmx-driven UI assertions.
- `e2e/helpers/dockview.ts` — `openObjectTab()`, `getTabCount()`, `getTabTitles()`. Needed for persona layout verification.
- `e2e/fixtures/seed-data.ts` — `SEED` and `TYPES` constants for basic-pkm seed data IRIs.
- `e2e/helpers/selectors.ts` — Shared CSS selectors. Add new selectors for event log autocomplete and persona UI here.

**Existing event log E2E tests (extend, don't duplicate):**
- `e2e/tests/06-settings/event-log.spec.ts` — Tests Alt+J panel open, event row loading. 2 tests.
- `e2e/tests/06-settings/event-undo.spec.ts` — Tests undo API, event detail API, event log UI with diff button expansion. 3 tests (one has broken duplicate code at end — `ownerRequest` used outside fixture scope).

**Backend endpoints to test (code on `milestone/M012` branch for S01/S02, `main` for S03):**
- `GET /browser/events/suggest-types` — returns HTML fragment with operation type suggestions
- `GET /browser/events/suggest-predicates?q=` — returns predicate suggestions with SHACL labels
- `GET /browser/events/suggest-objects?q=` — returns object suggestions with resolved labels
- `GET /browser/events/{event_iri}/detail` — returns event detail HTML with predicate labels and helptext
- `POST /api/commands` with `body.set` — sets body for first time
- `PUT /browser/objects/{iri}/body` — saves body (triggers body.diff if body exists)
- `GET /api/personas` — list personas
- `POST /api/personas` — create persona
- `POST /api/personas/{id}/activate` — activate persona
- `POST /api/personas/{id}/save-state` — save workspace state
- `PUT /api/personas/{id}` — rename persona
- `DELETE /api/personas/{id}` — delete persona
- `GET /browser/personas/selector` — persona selector htmx partial

**User guide files to modify:**
- `docs/guide/15-event-log.md` (226 lines) — needs 3 new sections for S01 features (labels, helptext, autocomplete) + 1 section for S02 feature (body.diff). Currently documents `body.set` events but not `body.diff`. Operation types table needs `body.diff` added.
- `docs/guide/README.md` — add Chapter 30 to TOC under a new section or Part VIII
- `docs/guide/appendix-d-glossary.md` — add Persona and Body Diff entries
- `docs/guide/29-mental-model-catalog.md` — update nav chain (Next → Chapter 30)

**New files to create:**
- `e2e/tests/27-event-log-polish/event-log-polish.spec.ts` — E2E tests for S01 features
- `e2e/tests/28-body-diff/body-diff.spec.ts` — E2E tests for S02 features
- `e2e/tests/29-personas/personas.spec.ts` — E2E tests for S03 features
- `docs/guide/30-personas.md` — new guide chapter

### Build Order

**Task 1: E2E Tests** — Write all three spec files. Tests can be written against the existing API and template structure documented in S01/S02/S03 summaries. The tests will exercise:
- Event log labels: open event log → expand event detail → verify predicate labels are human-readable (e.g. "Title" not raw IRI) and have title attributes (helptext)
- Event log autocomplete: focus on operation type filter → verify suggestion dropdown appears → click suggestion → verify filter applied
- Body.diff: create object → set body → edit body → open event log → expand latest event → verify diff rendering shows green/red lines
- Persona CRUD: API-level create persona → list → verify it exists → activate → rename → delete
- Persona UI: load workspace → verify default persona auto-created → create new persona → switch → verify layout change

**Task 2: User Guide Docs** — Update Chapter 15 and create Chapter 30. Low risk, no code changes. Can be done in parallel with E2E tests.

**Task 3: Navigation chain and glossary updates** — Wire Chapter 30 into README TOC and chapter navigation chain.

### Verification Approach

- **E2E tests pass:** `cd e2e && npx playwright test tests/27-event-log-polish tests/28-body-diff tests/29-personas --project=chromium` (requires Docker test stack with merged S01+S02+S03 code)
- **Existing tests don't regress:** `cd e2e && npx playwright test --project=chromium` (full suite)
- **Docs render correctly:** Manual inspection of markdown formatting, link validity
- **Navigation chain integrity:** Verify each chapter's Previous/Next links form a connected chain through Chapter 30

## Constraints

- **Docker test stack must include all 3 branches' code.** S01/S02 code is on `milestone/M012`, S03 on `main`. The `docker-compose.test.yml` mounts `./backend/app:/app/app` — so the code in the working directory must include all changes. The planner must ensure code from `milestone/M012` and `main` is merged before running E2E tests.
- **Tests are sequential, single-worker.** Playwright config enforces `fullyParallel: false` and `workers: 1` — the Docker stack is stateful. New test files must fit this constraint.
- **Test directory numbering.** Existing directories go up to `26-mental-models`. New tests should use `27-`, `28-`, `29-` to maintain ordering.
- **Event undo spec has a bug.** `event-undo.spec.ts` references `ownerRequest` and `createEventIri` outside their fixture/test scope in duplicate code blocks at the bottom. This doesn't affect S04 but is worth noting — don't follow that pattern.

## Common Pitfalls

- **Body.diff E2E requires two saves.** The body.diff code path only triggers when a body already exists. The test must: (1) create an object, (2) set body for the first time (produces `body.set`), (3) edit the body (produces `body.diff`), (4) check event log. The save_body endpoint is `PUT /browser/objects/{encoded_iri}/body` with `text/plain` content.
- **Autocomplete dropdowns close on outside click.** The event log JS has a `document.addEventListener('click')` that closes suggestion dropdowns when clicking outside. Tests must interact with the dropdown before it closes — use `page.locator('.event-autocomplete-target .suggestion-item').first().click()` promptly after triggering the dropdown.
- **Persona auto-creation on first load.** `initPersonas()` creates a "Default" persona on first workspace load. Tests that need to verify persona creation from scratch should delete all existing personas first via the API.
- **htmx swap timing.** Event log content loads via htmx lazy-load. Always use `waitForIdle(ownerPage)` after clicking the Event Log tab and before asserting on content.

## Sources

- E2E test patterns: `e2e/tests/06-settings/event-log.spec.ts`, `e2e/tests/03-navigation/named-layouts.spec.ts`
- Auth fixture pattern: `e2e/fixtures/auth.ts`
- User guide format: `docs/guide/15-event-log.md`, `docs/guide/28-dashboards-and-workflows.md`
- S01 Forward Intelligence: ShapesService label/helptext methods, htmx autocomplete pattern, suggestion template fragment
- S02 Forward Intelligence: body.diff operation stored as `sempkm:bodyDiff` data triple, three-way save_body branching
- S03 Forward Intelligence: persona API at `/api/personas`, selector partial at `/browser/personas/selector`, `switchPersona()` / `createNewPersona()` / `saveCurrentPersonaState()` JS functions
