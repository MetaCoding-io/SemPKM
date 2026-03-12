# S37: Global Lint Data Model Api

**Goal:** Build the lint data model, storage layer, and REST API endpoints for querying structured SHACL validation results.
**Demo:** Build the lint data model, storage layer, and REST API endpoints for querying structured SHACL validation results.

## Must-Haves


## Tasks

- [x] **T01: 37-global-lint-data-model-api 01** `est:5min`
  - Build the lint data model, storage layer, and REST API endpoints for querying structured SHACL validation results.

Purpose: Transform raw pyshacl report graphs into individually queryable structured result triples stored in per-run named graphs. Provide paginated, filterable REST endpoints that Phase 38's dashboard UI will consume.

Output: New `backend/app/lint/` package with models, service, and router. Extended ValidationReport with structured triple generation. Working `/api/lint/results`, `/api/lint/status`, and `/api/lint/diff` endpoints.
- [x] **T02: 37-global-lint-data-model-api 02** `est:5min`
  - Add SSE real-time push, migrate the per-object lint panel to use structured results, and remove the old validation API.

Purpose: Replace 10s polling with instant SSE-driven updates. Migrate the lint panel from querying raw pyshacl report graphs to querying structured result triples (single source of truth). Remove deprecated `/api/validation/*` endpoints.

Output: SSE broadcast manager, `/api/lint/stream` endpoint, migrated lint panel template, nginx SSE config, old validation router removed.

## Files Likely Touched

- `backend/app/lint/__init__.py`
- `backend/app/lint/models.py`
- `backend/app/lint/service.py`
- `backend/app/lint/router.py`
- `backend/app/validation/report.py`
- `backend/app/services/validation.py`
- `backend/app/dependencies.py`
- `backend/app/main.py`
- `backend/app/lint/broadcast.py`
- `backend/app/lint/router.py`
- `backend/app/validation/queue.py`
- `backend/app/main.py`
- `backend/app/dependencies.py`
- `backend/app/browser/router.py`
- `backend/app/templates/browser/lint_panel.html`
- `frontend/nginx.conf`
- `backend/app/validation/router.py`
- `e2e/tests/04-validation/lint-panel.spec.ts`
