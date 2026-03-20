# S04: E2E tests + mock server + user guide — Research

**Date:** 2026-03-19

## Summary

This is the standard "E2E + docs" closing slice, executed 6 times before (Linear, GitHub, Google Calendar, Todoist, Outlook, CalDAV). All three deliverables follow established patterns with well-understood file structures: a mock REST API server (`e2e/mock-asana-api/server.py`), a Playwright E2E spec (`e2e/tests/40-asana-sync/asana-sync.spec.ts`), and a user guide chapter (`docs/guide/40-asana-sync.md`). Plus README TOC, glossary, appendix A env vars, and navigation chain updates.

The only novelty compared to prior sync app E2E slices is the **field mapping configuration step** in the E2E test — the test must discover custom fields, configure status/priority mapping via the UI, and verify that synced tasks have the correct mapped status/priority values. This is new UX that prior E2E tests didn't exercise, but the mechanics are straightforward (form submission via htmx POST).

## Recommendation

Follow the established pattern exactly. Build in this order: (1) mock server with selftest, (2) E2E test, (3) user guide + README/glossary/appendix updates. The mock server must be built first because the E2E test depends on it, and the user guide can be written independently.

## Implementation Landscape

### Key Files

**Files to create:**

- `e2e/mock-asana-api/server.py` — Mock Asana REST API (~500-600 lines). Pattern: `e2e/mock-todoist-api/server.py` (383 lines, REST API, `{"data":...}` envelope isn't in Todoist but is in Asana). Needs `{"data": ..., "next_page": null}` wrapping on all responses. Endpoints:
  - `GET /health` — no auth, returns `{"status":"ok"}`
  - `GET /api/1.0/users/me` — returns user identity (name, email) for PAT verification
  - `GET /api/1.0/workspaces` — returns 1 workspace
  - `GET /api/1.0/workspaces/{gid}/projects` — returns 2 projects
  - `GET /api/1.0/projects/{gid}/sections` — returns 3 sections per project (To Do, In Progress, Done)
  - `GET /api/1.0/projects/{gid}` — returns project detail with `custom_field_settings` containing enum fields (Status, Priority) and a number field (Story Points)
  - `GET /api/1.0/projects/{gid}/tasks` — returns 2-3 canned tasks with custom_fields, memberships (section), tags, assignee
  - `GET /api/1.0/tasks/{gid}/subtasks` — returns 1 subtask for one of the tasks
  - `PATCH /api/1.0/tasks/{gid}` — echo-back with merged fields (for push sync)
  - `POST /api/1.0/sections/{gid}/addTask` — accept and return success (for section-based push)
  - Bearer token auth check on all endpoints except /health
  - Selftest with ~12 checks

- `e2e/tests/40-asana-sync/asana-sync.spec.ts` — Playwright E2E test (~350-400 lines). Pattern: `e2e/tests/39-caldav-calendar/caldav-calendar-sync.spec.ts` (304 lines). Phases:
  - Phase 0: Cleanup (remove asana-sync if installed from prior run)
  - Phase 1: Install basic-pkm model
  - Phase 2: Install asana-sync app, wait for Running
  - Phase 3: Enter PAT via api-key-form (simpler than OAuth — same as Todoist/Linear)
  - Phase 4: Select projects → Discover Fields → Configure status mapping (section-based) + priority mapping → Save
  - Phase 5: Sync Now → verify pull stats
  - Phase 5b: Verify tasks via SPARQL (check labels + status/priority values)
  - Phase 6: Admin detail + cleanup (uninstall)

- `docs/guide/40-asana-sync.md` — Chapter 40 user guide (~400-450 lines). Pattern: `docs/guide/39-caldav-calendar-sync.md` (368 lines). Sections: prerequisites, installing, connecting (OAuth + PAT), selecting workspaces/projects, discovering custom fields, configuring status mapping (3 modes), configuring priority mapping, story points, sync configuration, manual sync, field mapping reference tables, troubleshooting.

**Files to modify:**

- `e2e/helpers/selectors.ts` — Add `asanaSync` selector block (PAT input `#asana-pat`, connect btn `.api-key-form button[type="submit"]`, connect status `.connection-status`, project checkbox `.project-checkbox-item input[type="checkbox"]`, save projects `.projects-section button[type="submit"]`, discover fields `.discover-section button[type="submit"]`, status source radio, save mapping `.field-mapping-form button[type="submit"]`, sync direction, save config, sync now `#sync-now-btn`, sync stats `.sync-stats`)
- `docker-compose.test.yml` — Add `mock-asana` service (python:3.12-slim, volume `./e2e/mock-asana-api:/app:ro`, healthcheck on port 8080) and env vars `ASANA_API_URL: http://mock-asana:8080/api/1.0` + `ASANA_TOKEN_URL: http://mock-asana:8080/-/oauth_token` on the api service, plus `depends_on mock-asana`
- `docs/guide/README.md` — Add line `40. [Asana Sync](40-asana-sync.md)` after CalDAV entry
- `docs/guide/appendix-a-environment-variables.md` — Add `ASANA_API_URL` and `ASANA_TOKEN_URL` rows
- `docs/guide/appendix-d-glossary.md` — Add "Asana Sync" entry
- `docs/guide/39-caldav-calendar-sync.md` — Update navigation: Next → Chapter 40
- `docs/guide/40-asana-sync.md` — Navigation: Previous Ch 39, Next Appendix A

### Build Order

1. **Mock Asana REST API server** — Must exist first because docker-compose.test.yml references it and the E2E test runs against it. Self-contained, can be built and selftest-verified independently. Key detail: all responses must use the `{"data": [...], "next_page": null}` Asana envelope pattern. Auth via `Bearer {VALID_TOKEN}` matching the PAT entered in the E2E test.

2. **Docker compose + selectors** — Wire the mock into docker-compose.test.yml (service definition, env vars, depends_on). Add asanaSync selectors to helpers/selectors.ts.

3. **Playwright E2E test** — Exercises the full lifecycle. The novel phase is Phase 4 (field mapping configuration): after project selection, the test clicks "Discover Fields" which triggers the app to call the mock's custom_field_settings endpoint, then the test selects status source "section", saves the mapping, and proceeds to sync.

4. **User guide Chapter 40** — Can be written independently. The field mapping walkthrough is the distinctive content — explain all 3 status modes, priority mapping, story points. Include field mapping reference tables.

5. **README + glossary + appendix + nav chain** — Small updates to 5 existing files.

### Verification Approach

1. **Mock server selftest:** `python e2e/mock-asana-api/server.py --selftest` — must report all checks passing (target: ~12 checks covering all endpoints + auth rejection)
2. **Docker compose syntax:** `docker compose -f docker-compose.test.yml config --quiet` — must not error
3. **E2E test structure:** Verify the spec file has all phases (0-6), uses the correct selectors, and follows the established pattern
4. **User guide:** Verify chapter has prerequisites, installation, all 3 status modes, priority mapping, field mapping tables, troubleshooting, navigation chain
5. **Navigation chain:** Ch 39 → Ch 40 → Appendix A (verify Previous/Next links in both ch 39 and ch 40)
6. **README TOC:** Line 40 entry exists
7. **Glossary:** "Asana Sync" entry exists with cross-reference to Chapter 40

## Constraints

- Mock server must use only Python stdlib (`http.server`, `json`, `re`) — no external dependencies. Runs in `python:3.12-slim` Docker image.
- Asana API responses use `{"data": ..., "next_page": null}` envelope — every mock response must wrap data this way. The client's `_raw_request` extracts `next_page` for pagination.
- PAT token for E2E test: use `test-asana-pat-token-abc123` (matching convention from other mock servers).
- ASANA_API_URL env var points to `http://mock-asana:8080/api/1.0` — the client prepends this to resource paths like `/workspaces`.
- ASANA_TOKEN_URL env var points to `http://mock-asana:8080/-/oauth_token` — needed even for PAT flow because auth.py reads it at module level.
- Custom fields in mock responses must include `gid`, `name`, `resource_subtype` (enum/number), and for enums: `enum_options` with `[{gid, name}]`. The app's discover_fields route extracts these from `custom_field_settings`.
- Mock task data must include `custom_fields` array with matching GIDs so the field mapper can extract status/priority values.
- All htmx URLs in templates use `/app/asana-sync/` prefix — the E2E test routes through the app proxy, so this works naturally.

## Common Pitfalls

- **custom_field_settings vs custom_fields** — The discover route calls `get_custom_fields(project_gid)` which hits `GET /projects/{gid}?opt_fields=custom_field_settings...`. The response must return custom field metadata in `custom_field_settings` array (project-level), not in `custom_fields` (task-level). These are different structures.
- **E2E test field mapping step** — After clicking "Discover Fields", the connect_status template re-renders with discovered fields. The test must wait for the htmx swap before interacting with status/priority mapping controls. Use `waitForIdle` + timeout.
- **Section-based mapping in E2E** — Easier to test than custom field mapping because section names are rendered as a static table (no JS-driven dynamic rendering). Choose section-based status mapping in the E2E test for simplicity.
- **Mock task memberships** — Tasks must include `memberships: [{section: {gid, name}}]` for section-based status extraction by the field mapper.

---
