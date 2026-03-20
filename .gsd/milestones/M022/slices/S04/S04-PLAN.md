# S04: E2E tests + mock server + user guide

**Goal:** Mock Asana REST API server passes selftest, Playwright E2E test exercises full install → configure → sync → verify → cleanup lifecycle, Chapter 40 user guide documents Asana setup with field mapping walkthrough, README/glossary/appendix/nav-chain updated.
**Demo:** `python e2e/mock-asana-api/server.py --selftest` reports all checks passing. E2E spec structurally complete with all phases. Chapter 40 linked in README TOC and navigation chain.

## Must-Haves

- Mock Asana REST API server with ~12 endpoints, Bearer auth, `{"data":..., "next_page":null}` envelope, canned tasks with custom_fields + memberships, selftest
- `docker-compose.test.yml` wired with `mock-asana` service and `ASANA_API_URL` + `ASANA_TOKEN_URL` env vars
- `e2e/helpers/selectors.ts` has `asanaSync` selector block
- Playwright E2E spec at `e2e/tests/40-asana-sync/asana-sync.spec.ts` with phases 0–6 (cleanup, model install, app install, PAT connect, field mapping config, sync + verify, admin + cleanup)
- Chapter 40 user guide at `docs/guide/40-asana-sync.md` with prerequisites, OAuth + PAT auth, project selection, 3 status modes, priority mapping, story points, field mapping tables, troubleshooting
- README TOC line 40, glossary "Asana Sync" entry, appendix A env vars (ASANA_API_URL, ASANA_TOKEN_URL), nav chain Ch 39 → Ch 40 → Appendix A

## Proof Level

- This slice proves: final-assembly
- Real runtime required: no (selftest and structural verification; E2E runs against Docker stack when deployed)
- Human/UAT required: no

## Verification

- `cd e2e/mock-asana-api && python server.py --selftest` — all checks pass (target: ~12 checks)
- `docker compose -f docker-compose.test.yml config --quiet` — no errors
- `grep -c "asanaSync" e2e/helpers/selectors.ts` — ≥1
- E2E spec exists at `e2e/tests/40-asana-sync/asana-sync.spec.ts` with phases 0–6
- `docs/guide/40-asana-sync.md` exists with field mapping tables and 3 status modes
- `grep "40-asana-sync" docs/guide/README.md` — present
- `grep "Asana Sync" docs/guide/appendix-d-glossary.md` — present
- `grep "ASANA_API_URL" docs/guide/appendix-a-environment-variables.md` — present
- Ch 39 "Next" points to Ch 40; Ch 40 "Next" points to Appendix A

## Observability / Diagnostics

- **Runtime signals:** Mock server logs every request as `[mock-asana] METHOD /path → STATUS` to stderr. Health endpoint at `GET /health` returns `{"status": "ok"}` for Docker healthcheck and readiness probing.
- **Inspection surfaces:** `--selftest` mode exercises all endpoints and reports pass/fail per check. Docker healthcheck auto-probes `/health`. E2E test phases report per-phase pass/fail.
- **Failure visibility:** Auth failures return `401 {"errors": [{"message": "Not Authorized"}]}`. Unknown routes return 404 with JSON body. Server startup failure is visible via Docker container exit code and logs.
- **Redaction constraints:** The mock token `test-asana-pat-token-abc123` is a test-only value — no real secrets involved.

## Integration Closure

- Upstream surfaces consumed: S01 auth/client/manifest, S02 field mapper/sync engine, S03 push sync/settings UI — all consumed indirectly via the running app inside Docker
- New wiring introduced in this slice: mock-asana Docker service + env var routing
- What remains before the milestone is truly usable end-to-end: nothing — this is the final slice

## Tasks

- [x] **T01: Build mock Asana REST API server with selftest** `est:1h`
  - Why: E2E test and docker-compose depend on a mock server returning canned Asana API responses with correct envelope format
  - Files: `e2e/mock-asana-api/server.py`
  - Do: Python stdlib HTTP server with Bearer auth, `{"data":..., "next_page":null}` envelope on all responses. Endpoints: /health, /api/1.0/users/me, /api/1.0/workspaces, /api/1.0/workspaces/{gid}/projects, /api/1.0/projects/{gid} (with custom_field_settings), /api/1.0/projects/{gid}/sections, /api/1.0/projects/{gid}/tasks (with custom_fields + memberships), /api/1.0/tasks/{gid}/subtasks, PATCH /api/1.0/tasks/{gid}, POST /api/1.0/sections/{gid}/addTask. Selftest with ~12 checks covering all endpoints + auth rejection.
  - Verify: `python e2e/mock-asana-api/server.py --selftest` — all checks pass
  - Done when: selftest reports 12+ passing checks, server starts on port 8080

- [x] **T02: Wire Docker compose, add selectors, write Playwright E2E spec** `est:1h30m`
  - Why: Proves the full Asana Sync lifecycle against the mock server in Docker — the integration-level validation for the entire milestone
  - Files: `docker-compose.test.yml`, `e2e/helpers/selectors.ts`, `e2e/tests/40-asana-sync/asana-sync.spec.ts`
  - Do: Add mock-asana service to docker-compose.test.yml (python:3.12-slim, volume, healthcheck, network). Add ASANA_API_URL and ASANA_TOKEN_URL env vars to api service. Add depends_on mock-asana. Add asanaSync selector block to selectors.ts. Write E2E spec following CalDAV pattern: Phase 0 cleanup, Phase 1 install basic-pkm, Phase 2 install asana-sync + wait Running, Phase 3 PAT connect via api-key-form, Phase 4 select projects → discover fields → configure section-based status mapping + priority mapping → save, Phase 5 Sync Now + verify tasks via SPARQL, Phase 6 admin detail + uninstall cleanup.
  - Verify: `docker compose -f docker-compose.test.yml config --quiet` passes, E2E spec has all 7 phases, selectors.ts has asanaSync block
  - Done when: docker-compose validates, spec structurally complete with all phases

- [x] **T03: Write Chapter 40 user guide and update README/glossary/appendix/nav-chain** `est:45m`
  - Why: Completes the milestone's documentation deliverable — user guide, discoverability, and navigation
  - Files: `docs/guide/40-asana-sync.md`, `docs/guide/README.md`, `docs/guide/appendix-d-glossary.md`, `docs/guide/appendix-a-environment-variables.md`, `docs/guide/39-caldav-calendar-sync.md`
  - Do: Write Chapter 40 (~400 lines) following CalDAV/Outlook pattern. Sections: prerequisites, installing, connecting (OAuth + PAT), workspace/project selection, discovering custom fields, configuring status mapping (3 modes: completed_only, custom_field, section), configuring priority mapping, story points, sync configuration, manual sync, field mapping reference tables (core properties + status modes + priority), troubleshooting, see also. Add line 40 to README TOC. Add "Asana Sync" glossary entry. Add ASANA_API_URL and ASANA_TOKEN_URL rows to appendix A. Update Ch 39 nav: Next → Chapter 40. Set Ch 40 nav: Previous Ch 39, Next Appendix A.
  - Verify: All 5 files modified, Ch 40 has 3 status modes, nav chain Ch 39 → Ch 40 → Appendix A
  - Done when: Chapter 40 exists with field mapping walkthrough, README/glossary/appendix updated, nav chain correct

## Files Likely Touched

- `e2e/mock-asana-api/server.py`
- `docker-compose.test.yml`
- `e2e/helpers/selectors.ts`
- `e2e/tests/40-asana-sync/asana-sync.spec.ts`
- `docs/guide/40-asana-sync.md`
- `docs/guide/README.md`
- `docs/guide/appendix-d-glossary.md`
- `docs/guide/appendix-a-environment-variables.md`
- `docs/guide/39-caldav-calendar-sync.md`
