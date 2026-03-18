# S04: E2E Tests & User Guide — UAT

**Milestone:** M012
**Written:** 2026-03-17

## UAT Type

- UAT mode: mixed (artifact-driven for docs, live-runtime for E2E tests)
- Why this mode is sufficient: E2E tests exercise the real Docker stack through Playwright browser automation. Documentation is verifiable by file inspection. Together they cover both runtime behavior and user-facing guidance.

## Preconditions

- Docker test stack running on port 3901: `curl -s http://localhost:3901/api/health` returns 200
- E2E dependencies installed: `cd e2e && npm install` completed
- All M012 feature code merged to main (T01 merge complete)
- Backend test suite passing: `backend/.venv/bin/python -m pytest backend/tests/ --tb=short -q` shows 946+ passed

## Smoke Test

Run all 12 M012 E2E tests in one command:
```bash
cd e2e && npx playwright test tests/27-event-log-polish tests/28-body-diff tests/29-personas --project=chromium
```
**Expected:** 12 tests pass. If any fail, check Docker stack health and Playwright traces in `e2e/playwright-report/`.

## Test Cases

### 1. Event log predicate labels show human-readable text

1. Open workspace at `http://localhost:3901/browser/workspace`
2. Create a new object (any type) and set a title
3. Open the bottom panel (Ctrl+J) and click the EVENT LOG tab
4. Expand the latest event detail row
5. **Expected:** Predicate column shows "Title" (not "dcterms:title" or the raw IRI `http://purl.org/dc/terms/title`)

### 2. Predicate helptext tooltips appear on hover

1. With event detail expanded (from test 1)
2. Hover over a predicate label (e.g. "Title")
3. **Expected:** A dotted underline indicates the label has a tooltip. The `title` attribute shows helptext text from the SHACL shape's `sh:description` or `sempkm:editHelpText` annotation.

### 3. Autocomplete appears in event log operation type filter

1. Open the event log (bottom panel → EVENT LOG tab)
2. Click/focus the operation type filter input field
3. **Expected:** An autocomplete dropdown appears showing available operation types (e.g. "object.create", "object.patch", "body.set", "body.diff", "edge.create")

### 4. Predicate autocomplete filters on typed input

1. In the event log, click/focus the predicate filter input
2. Type "tit"
3. **Expected:** The autocomplete dropdown shows filtered suggestions including "Title" (the human-readable label for dcterms:title)

### 5. Body.diff event appears after editing existing body

1. Create a new object and save a body (e.g. "Original content")
2. Edit the body to different content (e.g. "Modified content")
3. Open the event log
4. **Expected:** The latest event shows operation type `body.diff` (not `body.set`)

### 6. Body.diff detail shows green/red diff highlighting

1. With the body.diff event from test 5, expand the event detail
2. Click the "Diff" button
3. **Expected:** The diff view shows removed lines in red and added lines in green, showing only the changed content

### 7. First body set creates body.set event

1. Create a brand new object (no existing body)
2. Set the body for the first time
3. Check the event log
4. **Expected:** The event shows operation type `body.set` (not `body.diff`), since there's no prior body to diff against

### 8. Persona CRUD via API

1. Create a persona: `POST /api/personas` with `{"name": "Test Persona"}`
2. **Expected:** 201 response with persona ID
3. List personas: `GET /api/personas`
4. **Expected:** Response includes "Test Persona"
5. Rename: `PUT /api/personas/{id}` with `{"name": "Renamed Persona"}`
6. **Expected:** 200 response
7. Delete: `DELETE /api/personas/{id}`
8. **Expected:** 204 response, persona gone from list

### 9. Default persona auto-created on first workspace load

1. Navigate to workspace (ensure user has no pre-existing personas, or use a fresh session)
2. After workspace loads, check `GET /api/personas`
3. **Expected:** At least one persona exists with `is_active: true`. This is the "Default" persona created by `initPersonas()`.

### 10. Persona selector visible in sidebar

1. In the workspace, click the user avatar/button at the bottom of the sidebar to open the user popover
2. Wait for the popover to fully load (it uses hx-get for lazy loading)
3. **Expected:** A "Personas" section appears in the popover with the active persona shown, a "Save" button, and a "New" button

### 11. Command palette has persona commands

1. Press Alt+K (or Ctrl+K) to open the command palette
2. Type "Persona"
3. **Expected:** Three persona commands appear: "Persona: Switch To...", "Persona: Save Current", "Persona: Create New..."

### 12. Persona activation switching

1. Create a second persona via API: `POST /api/personas` with `{"name": "Second Persona"}`
2. Note: the new persona should be auto-activated
3. Verify: `GET /api/personas` shows "Second Persona" as active
4. Activate the original persona: `POST /api/personas/{original_id}/activate`
5. **Expected:** Original persona is now active, second persona is inactive

## Edge Cases

### Body.set for empty-to-content transition

1. Create an object without setting a body
2. Set the body for the first time with content
3. **Expected:** Event log shows `body.set`, not `body.diff`. The body.diff path only triggers when prior body content exists.

### Persona delete of active persona

1. Create two personas (A and B), activate A
2. Delete persona A
3. **Expected:** Another persona (B or Default) becomes the active persona automatically. The system never has zero active personas for a user.

### Event log with both body.set and body.diff events

1. Create an object, set body (creates body.set event), then edit body (creates body.diff event)
2. Open event log and browse both events
3. **Expected:** body.set event shows full text in detail. body.diff event shows unified diff with green/red highlighting. Both render correctly in the same event log view.

## Failure Signals

- E2E tests fail with auth errors → check RATE_LIMIT_ENABLED is "false" in docker-compose.test.yml
- E2E tests fail with 404/500 → Docker test stack not serving all features; verify merge was complete
- Event log shows raw IRIs instead of labels → LabelService or ShapesService not wired into event endpoints
- Autocomplete dropdown doesn't appear → suggest-types/suggest-predicates/suggest-objects endpoints missing
- Body.diff events not appearing → body_diff.py handler not registered or body save endpoint not detecting prior body
- Persona selector missing from popover → _persona_selector.html partial not included in sidebar template
- Command palette missing persona commands → workspace.js persona palette registration not running
- Glossary grep returns < 2 → entries not added to appendix-d-glossary.md
- Chapter 30 missing from TOC → README.md not updated
- Navigation chain broken → Chapter 29 or 30 footer links not updated

## Requirements Proved By This UAT

- EVTLOG-01 — Tests 1 proves predicate labels resolve to human-readable text
- EVTLOG-02 — Test 2 proves helptext tooltips appear from SHACL annotations
- EVTLOG-03 — Tests 3-4 prove autocomplete works for operation type and predicate filters
- BDIFF-01 — Test 5 proves body changes store as body.diff when prior body exists
- BDIFF-02 — Test 6 proves body.diff events render with diff highlighting
- BDIFF-03 — Test 7 proves body.set backward compatibility (first body set)
- PERSONA-01 — Test 8 proves persona CRUD works
- PERSONA-02 — Test 12 proves persona activation switching
- PERSONA-03 — Test 10 proves persona selector in sidebar
- PERSONA-04 — Test 11 proves command palette entries
- PERSONA-05 — Test 9 proves default persona auto-creation

## Not Proven By This UAT

- **Persona layout restore fidelity** — UAT tests API activation but doesn't verify that dockview panel arrangement actually changes visually. This was verified manually during S03 development.
- **Persona persistence across Docker restarts** — Would require stopping and restarting the Docker stack mid-test. Verified by design (SQLite storage via Alembic migration).
- **Autocomplete for object filter** — The object filter autocomplete endpoint exists but isn't covered by a dedicated E2E test. The operation type and predicate autocomplete tests establish the pattern.
- **Full E2E suite regression** — ~15-20 older spec files have pre-existing syntax errors from earlier merges. Only the M012 test directories (27/28/29) are validated.

## Notes for Tester

- Run targeted tests only: `cd e2e && npx playwright test tests/27-event-log-polish tests/28-body-diff tests/29-personas --project=chromium`. The full suite has pre-existing issues in older test files.
- Auth rate limiting is disabled in the test stack (`RATE_LIMIT_ENABLED=false`). If you test manually against the dev stack (port 3000), rate limiting is still active — space out magic-link requests.
- The persona E2E tests use try/finally cleanup. If a test fails mid-run, orphan test personas may remain — they're harmless but visible in `GET /api/personas`.
- Chapter 30 navigation: verify the chain goes Ch 29 → Ch 30 → Appendix A (both directions).
