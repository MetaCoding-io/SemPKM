# T02: 37-global-lint-data-model-api 02

**Slice:** S37 — **Milestone:** M001

## Description

Add SSE real-time push, migrate the per-object lint panel to use structured results, and remove the old validation API.

Purpose: Replace 10s polling with instant SSE-driven updates. Migrate the lint panel from querying raw pyshacl report graphs to querying structured result triples (single source of truth). Remove deprecated `/api/validation/*` endpoints.

Output: SSE broadcast manager, `/api/lint/stream` endpoint, migrated lint panel template, nginx SSE config, old validation router removed.

## Must-Haves

- [ ] "Lint panel updates instantly when validation completes (no 10s polling delay)"
- [ ] "SSE stream at /api/lint/stream broadcasts validation_complete events"
- [ ] "Per-object lint panel queries structured results instead of raw report graphs"
- [ ] "Old /api/validation/* endpoints are removed"
- [ ] "Multiple browser tabs can subscribe to the same SSE stream"

## Files

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
