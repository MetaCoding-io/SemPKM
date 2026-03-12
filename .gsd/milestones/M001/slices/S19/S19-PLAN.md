# S19: Bug Fixes And E2e Test Hardening

**Goal:** Fix all backend bugs from the CONCERNS.
**Demo:** Fix all backend bugs from the CONCERNS.

## Must-Haves


## Tasks

- [x] **T01: 19-bug-fixes-and-e2e-test-hardening 01** `est:13min`
  - Fix all backend bugs from the CONCERNS.md audit: EventStore DI, label cache invalidation, datetime UTC, CORS misconfiguration, cookie secure env var, debug endpoint auth guard, and IRI validation.

Purpose: These are correctness and security bugs in the backend that affect data integrity (stale labels, wrong timestamps), session security (cookie), API safety (CORS, IRI injection), and access control (debug endpoints). None are new features — all are hardening of existing behavior.
Output: Cleaned `browser/router.py` with DI-injected EventStore, label cache invalidation after every commit, UTC datetimes; `config.py` with CORS_ORIGINS and COOKIE_SECURE env vars; `main.py` with conditional CORS; `auth/router.py` using settings.cookie_secure; `debug/router.py` with require_role("owner"); IRI validation helper applied at all 6 SPARQL interpolation points.
- [x] **T02: 19-bug-fixes-and-e2e-test-hardening 02**
  - Fix all 6 user-discovered UI bugs and add tag pill display and nav tree + graph node tooltip improvements.

Purpose: These are visible, user-facing regressions and missing polish items that affect daily use. Each fix is surgical — targeted to the exact function, template section, or CSS rule causing the issue.
Output: workspace-layout.js with tab active guard and split fix; workspace.js with docs/tutorial/autocomplete/edit-button/tooltip fixes; graph.js with confirmed graph-style node hover tooltip; object_read.html with tag pill rendering in read view; forms/_field.html with tag pill styling in edit view; tree_children.html with hover tooltip; workspace.css with .tag-pill styles and tooltip CSS.
- [x] **T03: 19-bug-fixes-and-e2e-test-hardening 03**
  - Add E2E test coverage for critical Phase 10-18 features (split panes, event log, tutorial launch) and document the known infrastructure constraint on setup wizard tests. Verify the full suite stays at >= 118/123 with no regressions.

Purpose: Phase 19 bug fixes could introduce regressions. This plan adds targeted tests for the Phase 10-18 features that now have bug fixes applied (split panes, docs/tutorials), and verifies the suite is healthy before v2.0 ships.
Output: Three new spec files covering split panes, event log, and tutorial launch. A code comment in setup wizard spec explaining the known infrastructure issue. Full Playwright run confirming >= 118/123.

## Files Likely Touched

- `backend/app/dependencies.py`
- `backend/app/browser/router.py`
- `backend/app/config.py`
- `backend/app/main.py`
- `backend/app/auth/router.py`
- `backend/app/debug/router.py`
- `frontend/static/js/workspace-layout.js`
- `frontend/static/js/workspace.js`
- `frontend/static/js/graph.js`
- `frontend/static/css/workspace.css`
- `backend/app/templates/browser/object_read.html`
- `backend/app/templates/forms/_field.html`
- `backend/app/templates/browser/tree_children.html`
- `backend/app/templates/browser/docs_page.html`
- `e2e/tests/03-navigation/split-panes.spec.ts`
- `e2e/tests/06-settings/event-log.spec.ts`
- `e2e/tests/06-settings/tutorials.spec.ts`
- `e2e/tests/00-setup/01-setup-wizard.spec.ts`
