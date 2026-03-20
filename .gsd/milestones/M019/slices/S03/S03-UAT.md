# S03: E2E Tests + User Guide — UAT

**Milestone:** M019
**Written:** 2026-03-19

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: This slice produces a mock server (testable via selftest), a Playwright E2E spec (structurally verifiable via --list), and documentation (verifiable via grep). No live runtime needed for UAT — the mock selftest proves endpoint behavior, and the E2E test structure proves completeness.

## Preconditions

- Python 3.12+ available (for mock server selftest)
- Node.js + npm available (for Playwright test listing)
- Docker Compose available (for config validation)
- Working directory contains the full worktree with all S01/S02/S03 outputs

## Smoke Test

Run `python3 e2e/mock-todoist-api/server.py --selftest` — should print 10 passed, 0 failed and exit 0.

## Test Cases

### 1. Mock server selftest passes all endpoint checks

1. Run `python3 e2e/mock-todoist-api/server.py --selftest`
2. **Expected:** 10 checks pass: health, projects, tasks, labels, auth failure (401), close (204), reopen (204), update, create, project content validation. Exit code 0.

### 2. Mock server rejects unauthenticated requests

1. Run `python3 e2e/mock-todoist-api/server.py --selftest`
2. Observe check 5: "GET /rest/v2/tasks without auth → 401"
3. **Expected:** Mock returns HTTP 401 with `{"error": "Unauthorized"}` body when no Authorization header is present.

### 3. Close/reopen endpoints return 204 empty body

1. Run `python3 e2e/mock-todoist-api/server.py --selftest`
2. Observe checks 6 and 7
3. **Expected:** POST /rest/v2/tasks/{id}/close returns 204, POST /rest/v2/tasks/{id}/reopen returns 204. Both return empty body (matching real Todoist API behavior).

### 4. Env var override does not break existing unit tests

1. Run `./backend/.venv/bin/pytest backend/tests/test_todoist_*.py -v`
2. **Expected:** 239 tests pass. The `os.environ.get("TODOIST_API_URL", ...)` default value preserves production behavior when env var is unset.

### 5. Docker Compose config validates with mock-todoist service

1. Run `docker compose -f docker-compose.test.yml config --quiet`
2. **Expected:** Exits 0 with no output. The mock-todoist service, health check, network, and TODOIST_API_URL env var on api service are all valid.

### 6. E2E test file compiles and is discoverable

1. From `e2e/` directory, run `npx playwright test tests/37-todoist-sync/ --list`
2. **Expected:** Lists 2 tests (chromium + firefox) with title "Todoist Sync › full lifecycle: install → connect → sync → verify → cleanup". No TypeScript compilation errors.

### 7. E2E selectors match template HTML

1. Run `rg "todoist-token|api-key-form|connection-status|project-checkbox|sync-config-form|sync-now-btn|sync-stats" apps/todoist-sync/frontend/templates/`
2. **Expected:** Every selector ID/class from the `todoistSync` block in selectors.ts appears in at least one template file.

### 8. Chapter 37 has complete field mapping tables

1. Run `grep -c "^##" docs/guide/37-todoist-sync.md`
2. **Expected:** At least 12 sections (actual: 37). Sections include Priority Mapping, Status Mapping, Due Dates, Labels, Close/Reopen Pattern, Push Sync, Troubleshooting.

### 9. Documentation cross-references are wired

1. Run `rg "37-todoist" docs/guide/`
2. **Expected:** Hits in README.md (TOC line 37), appendix-d-glossary.md (Todoist Sync entry reference), and 36-google-calendar-sync.md (navigation footer).

### 10. TODOIST_API_URL documented in appendix

1. Run `rg "TODOIST_API_URL" docs/guide/appendix-a-environment-variables.md`
2. **Expected:** Row present with description, default value (`https://api.todoist.com/rest/v2`), and required=No.

### 11. All htmx URLs use proxy prefix

1. Run `rg "hx-(post|get)=" apps/todoist-sync/frontend/templates/ | grep -v "/app/todoist-sync/"`
2. **Expected:** Empty output (exit code 1). All htmx attributes use `/app/todoist-sync/` prefix to route through the app proxy.

## Edge Cases

### Mock server handles unknown task IDs gracefully

1. The mock server uses a fixed set of canned task IDs (200001, 200002, 200003).
2. Close/reopen/update for any task ID returns success (204 or 200) — the mock does not validate task existence.
3. **Expected:** This is intentional — the mock is for happy-path E2E testing, not for exhaustive API simulation.

### E2E test handles collapsed APPS section

1. The test (Phase 3) clicks the APPS section header to expand it before looking for the app settings link.
2. **Expected:** This handles the known workspace explorer behavior where sections start collapsed (per KNOWLEDGE.md).

## Failure Signals

- `python3 e2e/mock-todoist-api/server.py --selftest` prints `[selftest] FAIL:` with non-zero exit — mock server broken
- `pytest backend/tests/test_todoist_*.py` shows failures — env var change broke something
- `docker compose -f docker-compose.test.yml config` prints errors — Docker service definition invalid
- `npx playwright test tests/37-todoist-sync/ --list` shows 0 tests — TypeScript compilation error or test structure issue
- `rg "37-todoist" docs/guide/` returns no hits — cross-references not wired
- `rg "hx-(post|get)=" ... | grep -v "/app/todoist-sync/"` returns matches — htmx URLs bypass proxy

## Requirements Proved By This UAT

- TD-08 (E2E + user guide) — mock server selftest, E2E test structure, Chapter 37 completeness
- Indirectly: TD-01 through TD-07 are proven by the 239 unit tests from S01/S02 and the E2E test's SPARQL verification phases

## Not Proven By This UAT

- Full Docker runtime E2E execution — blocked by pre-existing subprocess startup issue (affects all sync apps M016–M019)
- Actual Todoist API compatibility — would require a real Todoist account and API calls

## Notes for Tester

- The E2E test may fail at Phase 2 (app install) due to the pre-existing subprocess 500 error. This is not a Todoist-specific issue — it's the same blocker that affects M016, M017, and M018 E2E tests.
- The mock server selftest is the fastest way to verify the mock is working — it runs in <1s without Docker.
- Chapter 37's priority inversion table is the most important documentation element — verify that Todoist API `priority: 4` maps to SemPKM `critical` (not `low`).
