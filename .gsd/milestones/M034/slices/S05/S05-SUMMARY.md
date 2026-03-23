---
id: S05
parent: M034
milestone: M034
provides:
  - TaskTemplateService with RDF CRUD against urn:sempkm:task-templates named graph
  - REST API endpoints for template CRUD + batch instantiation via @slot: references
  - 4 PPV review workflow seeds (Weekly/Monthly/Quarterly/Yearly) with per-name idempotency
  - Command palette "Create from Template" parent with dynamic API-driven children
  - 4 review workflow launcher commands in command palette
  - Template picker htmx partial
  - 21 unit tests for template CRUD and instantiation
  - 10 seed idempotency tests
requires:
  - slice: S01
    provides: Task type with scheduling properties for template target class
affects: []
key_files:
  - backend/app/task_templates/__init__.py
  - backend/app/task_templates/service.py
  - backend/app/task_templates/router.py
  - backend/app/dashboard/seed.py
  - frontend/static/js/workspace.js
  - backend/tests/test_task_templates.py
  - backend/tests/test_seed_data.py
key_decisions:
  - Instantiate endpoint dispatches through dispatch() + EventStore.commit() pipeline — no internal HTTP call, reuses slot_map resolution directly
  - Template IRI format is urn:sempkm:task-template:{uuid4} in urn:sempkm:task-templates named graph
  - Per-name idempotency for workflow seeding — iterate definitions, skip if name in existing set
  - Template children populated via API fetch, same pattern as persona palette items
  - Review workflow launchers use name-based lookup, resilient to ID changes across reinstalls
patterns_established:
  - RDF-backed service with dedicated named graph and SPARQL CRUD for templates
  - Internal batch command dispatch for features that create objects via templates
  - _sparql_bindings() test helper for building mock RDF4J JSON responses
observability_surfaces:
  - TaskTemplateService structured logs for create/update/delete/instantiate operations
  - GET /api/task-templates lists all templates
  - GET /api/workflow lists all workflows including seeded reviews
  - 21 unit tests in test_task_templates.py
  - 10 seed tests in test_seed_data.py
drill_down_paths:
  - .gsd/milestones/M034/slices/S05/tasks/T01-SUMMARY.md
  - .gsd/milestones/M034/slices/S05/tasks/T02-SUMMARY.md
  - .gsd/milestones/M034/slices/S05/tasks/T03-SUMMARY.md
  - .gsd/milestones/M034/slices/S05/tasks/T04-SUMMARY.md
duration: 5h
verification_result: passed
completed_at: 2026-03-22
---

# S05: Task Templates & Review Workflows

**Built RDF-backed task template CRUD with batch instantiation, seeded 4 PPV review workflows with per-name idempotency, and wired both into the command palette**

## What Happened

T01 created the TaskTemplateService with full CRUD against a dedicated RDF named graph, REST/htmx endpoints, and a batch instantiation pipeline using @slot: references through the command dispatch system. T02 added 4 PPV review workflow seed definitions (Weekly/Monthly/Quarterly/Yearly) with per-name idempotency so existing user workflows are never affected. T03 wired "Create from Template" as a parent command with dynamic API children and 4 review workflow launcher commands into the ninja-keys command palette. T04 added 21 unit tests covering all CRUD operations, instantiation with and without subtasks, @slot: reference generation, user overrides, error paths, and JSON parse safety.

## Verification

- 21 template CRUD tests pass
- 10 seed idempotency tests pass
- All 8 slice-level verification checks pass (named graph usage, command palette entries, syntax validity, structured logging, error responses)

## Requirements Advanced

- PLAN-06 — Task templates creatable, listable, usable from command palette
- PLAN-07 — PPV review workflows seeded and launchable from palette

## Requirements Validated

- PLAN-06 — Template CRUD proven by 21 unit tests; command palette integration verified by grep
- PLAN-07 — 4 review workflows seeded with correct step configurations proven by seed tests; palette entries verified

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

- T04 exceeded planned 8 tests to 21 for better edge case coverage (escaping, malformed JSON, multi-field update, custom predicates)

## Known Limitations

- Template picker htmx partial exists but command palette uses API-driven JS flow — picker useful for future modal-based template selection
- No UI for template CRUD management (create/edit/delete) — currently API-only

## Follow-ups

None.

## Files Created/Modified

- `backend/app/task_templates/__init__.py` — package init
- `backend/app/task_templates/service.py` — TaskTemplateService with SPARQL CRUD
- `backend/app/task_templates/router.py` — REST API and htmx routes
- `backend/app/main.py` — template service wiring and router mounting
- `backend/app/templates/browser/template_picker.html` — htmx partial
- `backend/app/dashboard/seed.py` — 4 review workflow definitions with per-name idempotency
- `frontend/static/js/workspace.js` — command palette template and workflow entries
- `backend/tests/test_task_templates.py` — 21 unit tests
- `backend/tests/test_seed_data.py` — 10 seed idempotency tests

## Forward Intelligence

### What the next slice should know
- TaskTemplateService is available on app.state.template_service
- Instantiation uses the same dispatch() + EventStore.commit() pipeline as POST /api/commands
- SEED_WORKFLOWS constant in seed.py is importable for downstream references

### What's fragile
- Template instantiation assumes command schemas haven't changed — if ObjectCreateParams or EdgeCreateParams gain required fields, instantiate() will break
- Review workflow launchers find workflows by name string match — name changes in seed data require palette code update

### Authoritative diagnostics
- GET /api/task-templates returns all stored templates as JSON
- TaskTemplateService logs at INFO for all CRUD operations with template IRI
- pytest tests/test_task_templates.py -v shows per-test pass/fail

### What assumptions changed
- Originally planned separate templates_service.py and templates_router.py at top level — placed in task_templates/ package for better organization
