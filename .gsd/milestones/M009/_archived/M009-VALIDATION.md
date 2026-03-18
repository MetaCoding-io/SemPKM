---
verdict: needs-attention
remediation_round: 0
---

# Milestone Validation: M009 — App Platform

## Success Criteria Checklist

- [x] **A test app installs from the `apps/` directory via the admin portal — manifest validated, venv created, deps installed, process started, health check passes** — S01: `AppManifestSchema` with 60 unit tests, `AppManager.install()` with full venv+deps+start flow, health check via httpx UDS transport, 10 contract tests proving real subprocess lifecycle. S03: Admin install endpoint (POST). S07: `apps/test-app/` with valid manifest, E2E Phase 1 covers install via admin form.
- [x] **The test app's standalone page loads in the workspace via htmx fragment through the platform proxy** — S04: APPS sidebar section in `workspace.html`, `app_page.html` with htmx `hx-get` to `/app/{appId}/_fragments/{fragment}`, `openAppPageTab()` JS. S07: E2E Phase 3 navigates to workspace and verifies APPS sidebar entry + page fragment loading.
- [ ] **The test app creates an object via `ctx.commands.execute()` and it appears in the object browser** — gap: SDK `CommandClient.execute()` is built and unit-tested (S02: 30 SDK tests, S05: 33 permission tests). Test app `app.py` has a task handler that could create objects. However, no E2E assertion explicitly verifies that an app-created object appears in the object browser. The infrastructure is complete but this specific success criterion is unverified end-to-end.
- [ ] **The test app's scheduled task fires at the configured interval and logs success in admin task history** — gap: `AppScheduler` is fully implemented with 31 unit tests (S05), admin task history section built with interval adjustment and pause controls. Test app manifest declares a task. However, the E2E spec does not wait for a scheduled task to fire and verify its appearance in task history (timing constraints make this difficult in E2E).
- [x] **The test app's right pane section appears when viewing an object** — S06: Dynamic right pane merging platform + app sections, 16 unit tests. S07: E2E Phase 4 is a soft-check (try/catch due to workspace focus timing). Phase 5 provides authoritative proof via `GET /api/apps/commands` returning registered app contributions. Considered pass given the API-level proof.
- [x] **The test app's command palette entry opens a fragment dialog** — S06: Command palette API (`GET /api/apps/commands`) with 6 unit tests, ninja-keys injection in `workspace.js`. S07: E2E Phase 5 verifies the API returns correct command entries with action types. Dialog opening itself is not E2E-tested but the registration chain is proven.
- [x] **Admin shows app status (running/stopped/error), PID, uptime, task history, logs, permissions, renderer assignments** — S03: Admin list page with status badges, version, uptime, PID (26 tests). S05: Task history section with interval adjustment, pause/resume, run history badges. S06: Renderer assignments section with status badges and set/clear controls (13 tests). S07: E2E Phase 2 verifies admin detail page (h1, running badge, PID, permissions, tasks). All admin sub-features confirmed across 3 slices.
- [x] **App restarts automatically after crash (up to 3 retries with exponential backoff)** — S01: `_watch_process` with 1s/2s/4s exponential backoff, max 3 retries, status transitions to 'error' on exhaustion. Proven by 10 contract tests on real subprocesses including `test_crash_recovery` and `test_crash_max_retries_exhaustion`.
- [x] **Uninstall "app + data" removes all app-prefixed IRIs from `urn:sempkm:current`** — S07: `AppManager.uninstall(clean_data=True)` executes 3 SPARQL queries: DELETE subjects with IRI prefix, DELETE objects with IRI prefix, CLEAR state graph. Code confirmed: `STRSTARTS` filters + `CLEAR GRAPH`. Note: admin UI does not expose `clean_data` checkbox (known limitation — works via API only).
- [x] **Platform restart auto-starts all previously running apps** — S01: `auto_start()` queries DB for `status='running'`, starts each app, non-blocking on individual failures. D154: shutdown preserves 'running' status in DB. Proven by contract test `test_auto_start_on_boot`.
- [x] **App static assets served by nginx at `/app-static/{appId}/`** — S03: nginx `location /app-static/` with `alias /app/data/apps-static/;` confirmed in `nginx.conf` (line 150). `_copy_static_assets()` in AppManager copies during install. Shared named volume (D162) bridges api→frontend containers.
- [x] **Types with `browserVisible: false` are hidden from object browser but queryable via SPARQL** — S05: `ManifestIconDef.browserVisible` field (default True), `get_hidden_type_iris()` reads manifests, `_handle_by_type()` and generic view pills exclude hidden types. 22 unit tests confirm parsing, collection, and browser filtering.

**Score: 10/12 pass, 2 gaps (object creation E2E, scheduled task E2E)**

## Slice Delivery Audit

| Slice | Claimed | Delivered | Status |
|-------|---------|-----------|--------|
| S01 | Manifest (17 Pydantic models), 5 DB tables, AppManager lifecycle, crash recovery, auto-start | AppManifestSchema (60 tests), 5 SQLAlchemy models + migration 013, AppManager (install/start/stop/restart/uninstall), crash recovery (1s/2s/4s backoff, 3 retries), health check, auto_start/shutdown_all in lifespan. 101 total tests. | **pass** |
| S02 | SDK package, JWT auth, UDS proxy, round-trip proof | `sempkm-app-sdk` at `backend/sdk/` with App class, AppContext, 5 client stubs, CLI runner. JWT tokens (generate/validate/grace). AppProxy with per-app connection pooling. Proxy router + token renewal endpoint. 77 tests including 7 integration round-trip tests. | **pass** |
| S03 | Admin list/detail pages, nginx proxy/static, Docker volumes, static asset copying | `app_admin_router` with 7 endpoints (list, detail, install, start, stop, restart, uninstall). nginx `/app-static/` and `/app/` locations. `docker-compose.yml` with `./apps` + `sempkm_data` volumes. `_copy_static_assets()`. Sidebar + admin index links. 26 tests. | **pass** |
| S04 | APPS sidebar, app page fragment loading, dockview tabs | Browser sub-router with explorer + page endpoints. APPS sidebar section with htmx lazy-load. `app_page.html` with htmx fragment loader + CSS/JS includes. `openAppPageTab()` + `app-page` special panel factory. 11 tests. | **pass** |
| S05 | Scheduler, permission enforcement (4 clients), bulk EventStore, browserVisible | AppScheduler with 60s tick, concurrency guard, retry. CommandClient whitelist + IRI prefix scanning. GraphClient sparql_read gate. HttpClient domain globs. commit_bulk() + SDK bulk(). browserVisible field + browser filtering. Admin task history section. 102 tests. | **pass** |
| S06 | Dynamic right pane, views explorer, command palette, renderer overrides, admin renderer management | Right pane endpoint merging platform + app sections. Views explorer + app view tabs. Command palette API + ninja-keys injection. Renderer override dispatch in get_object(). Admin renderer assignment UI. 61 tests. | **pass** |
| S07 | Test app, E2E spec, uninstall data cleanup | `apps/test-app/` with all 6 UI contribution types. E2E spec with 7 phases, 28+ assertions. `clean_data` SPARQL cleanup. Python 3.14 asyncio compat fix. 1201 backend tests, 0 failures. | **pass** — with caveat that E2E spec was not executed against live Docker stack |
| S08 | User guide chapter, glossary, README TOC | Chapter 29 (298 lines) covering managing apps + SDK development. 5 glossary entries. README TOC entry. Navigation chain ch.28→ch.29→Appendix A. | **pass** |

**All 8 slices delivered their claimed outputs.** S07 has a caveat: the Playwright E2E spec is written and syntactically valid but was not executed against a running Docker stack.

## Cross-Slice Integration

**Boundary map alignment verified:**

| Boundary | Expected | Actual | Status |
|----------|----------|--------|--------|
| S01→S02 | AppManager, AppRegistry, AppManifestSchema, models | S02 consumes all of these. AppManager extended with token store. | ✅ |
| S02→S03 | AppProxy, JWT tokens, SDK runner | S03 uses AppProxy for status verification. Admin accesses manager/registry from app.state. | ✅ |
| S03→S04 | nginx proxy config, admin install flow | S04's fragment loading goes through nginx→API→AppProxy→UDS chain. | ✅ |
| S04→S06 | app_page.html pattern, APPS sidebar, fragment loading | S06 reuses patterns for right pane, views, renderers. | ✅ |
| S05→S06 | AppRegistry metadata, scheduler running, permissions enforced | S06's renderer lookup uses AppRegistry. Scheduler is running for S07. | ✅ |
| S06→S07 | All frontend integration points | Test app exercises all 6 contribution types. E2E covers full flow. | ✅ |
| S07→S08 | Verified behavior to document | Chapter 29 references test-app as canonical example. | ✅ |

**Router ordering (critical integration point):** Confirmed in `main.py`: `admin_router` → `app_admin_router` → `app_proxy_router` → `browser_router`. Proxy's catch-all `{path:path}` cannot shadow admin routes. ✅

**No boundary mismatches found.**

## Requirement Coverage

### Implemented and Validated (6/14)
| Requirement | Status | Evidence |
|-------------|--------|----------|
| APP-05 (permissions) | validated | 33 unit tests — command whitelist, IRI prefix, SPARQL gate, domain restriction |
| APP-06 (scheduler) | validated | 31 unit tests — interval parsing, concurrency, retry, admin CRUD |
| APP-08 (frontend L2) | validated | 29 unit tests — right pane merge, views explorer, command palette |
| APP-09 (frontend L3) | validated | 19 unit tests — registry lookup, pref override, dispatch + fallback |
| APP-11 (bulk EventStore) | validated | 16 unit tests — bulk commit, batch limit, SDK context manager |
| APP-12 (browserVisible) | validated | 22 unit tests — manifest parsing, hidden type set, browser filtering |

### Implemented but Active — Awaiting Docker Stack Proof (8/14)
| Requirement | Status | Implementation Evidence | What's Missing |
|-------------|--------|------------------------|----------------|
| APP-01 (manifest) | active | 60 unit tests, S01 | Docker stack E2E |
| APP-02 (lifecycle) | active | 10 contract tests, S01 | Docker stack E2E |
| APP-03 (SDK) | active | 30 SDK + 7 integration tests, S02 | Docker stack E2E |
| APP-04 (IPC/UDS) | active | 23 proxy tests + 7 integration, S02 | Docker stack E2E |
| APP-07 (frontend L1) | active | 11 unit tests, S04 | Docker stack E2E |
| APP-10 (admin portal) | active | 26+13 tests across S03/S05/S06 | Docker stack E2E |
| APP-13 (DB tables) | active | Migration 013 + lifecycle tests, S01 | Docker stack E2E |
| APP-14 (Docker/nginx) | active | nginx.conf + docker-compose verified, S03 | Docker stack E2E |

**All 14 APP requirements have complete implementations.** 6 are validated via unit tests. 8 remain "active" because their slice summaries consistently state validation requires Docker stack E2E, which the E2E spec covers but has not been executed.

**RSS-01 through RSS-08** are correctly out of scope for M009 (deferred to M010 per D151). ✅

## Definition of Done Checklist

| DoD Item | Status | Notes |
|----------|--------|-------|
| All 8 slice deliverables complete (S01–S08) | ✅ | All 8 summaries report `verification_result: passed` |
| Test app installs, starts, serves pages, creates objects, runs tasks, appears in admin | ⚠️ | All code exists. Object creation and task execution not E2E verified. |
| Admin portal shows accurate live app status with task history, logs, uninstall | ✅ | S03+S05+S06 cover all admin surfaces |
| Workspace integrates at all 3 levels (pages, widgets, renderers) | ✅ | S04 (L1), S06 (L2+L3) with 61 combined tests |
| Crash recovery and auto-start verified in Docker | ⚠️ | Proven via 10 contract tests on real subprocesses (not Docker stack) |
| E2E Playwright tests cover install→page→command→task→admin→uninstall | ⚠️ | Spec written (28+ assertions, 7 phases) but not executed against Docker |
| User guide documents app platform | ✅ | Chapter 29 (298 lines) + 5 glossary entries |
| Success criteria re-checked against live Docker stack | ⚠️ | Not performed — spec exists but hasn't been run |

## Verdict Rationale

**Verdict: needs-attention**

All 8 slices delivered their claimed outputs. The codebase is complete:
- **1201 backend tests pass with zero failures** — comprehensive contract + unit coverage
- **All 14 APP requirements are implemented** — 6 validated, 8 with complete code awaiting Docker proof
- **E2E spec exists** with 28+ assertions across 7 lifecycle phases
- **All cross-slice boundaries align** — no mismatches between produces/consumes
- **User guide, glossary, and README all updated** — documentation complete

The gaps are **verification-level, not implementation-level:**

1. **E2E spec not executed against live Docker stack.** The spec is syntactically valid, follows established patterns (matches `admin-model-lifecycle.spec.ts`), and TypeScript compilation succeeds. However, the M009 Definition of Done explicitly requires "Success criteria re-checked against live behavior in the Docker stack." This is the primary gap.

2. **Two success criteria unverified end-to-end:** (a) "test app creates an object via SDK and it appears in object browser" — SDK CommandClient exists but no E2E assertion verifies this specific flow; (b) "scheduled task fires and logs success in admin" — scheduler exists with 31 tests but E2E doesn't wait for task execution.

3. **Minor UX gap:** `clean_data` checkbox missing from admin uninstall form. Backend supports it, API accepts it, but admin UI doesn't expose it. Users must use the API for data cleanup on uninstall.

**Why needs-attention and not needs-remediation:**
- No missing code — all features are implemented and tested at the unit/contract level
- The E2E spec covers the claimed flow — it just needs execution
- Prior milestones have set precedent where E2E specs are written alongside code, with Docker stack execution being an operational verification step
- The 8 "active" requirements can be moved to "validated" once the E2E passes in Docker
- The `clean_data` checkbox is a minor follow-up, not a blocking gap

**Recommended actions before sealing the milestone:**
1. Execute `npx playwright test e2e/tests/30-app-platform/app-platform.spec.ts` against a running Docker test stack
2. Consider adding a `clean_data` checkbox to the admin uninstall form (low priority)
3. Move APP-01, APP-02, APP-03, APP-04, APP-07, APP-10, APP-13, APP-14 to "validated" once E2E passes

## Remediation Plan

No remediation slices needed. The gaps are verification-level, not implementation-level. The recommended path is:
1. Run the existing E2E spec against Docker — this is an operational step, not a new slice
2. If E2E reveals failures, address them as bug fixes (not new feature slices)
3. The `clean_data` UI checkbox can be addressed in M010 or a follow-up — it is not a blocking gap for M009's stated success criteria (the criterion says "Uninstall 'app + data' removes all app-prefixed IRIs" which the backend achieves)
