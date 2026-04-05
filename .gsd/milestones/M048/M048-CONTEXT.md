---
depends_on: []
---

# M048: Critical Bug Fixes

**Gathered:** 2026-04-05
**Status:** Ready for planning

## Project Description

Fix the showstopper bugs found during the SemPKM feature tour that make core features non-functional. These are the highest-priority items — broken functionality that blocks normal use of the app.

## Why This Milestone

Multiple core features are broken or missing: object deletion doesn't exist, the save operation pollutes the event store with phantom changes, views don't render, new objects lack creation timestamps, and models may not fully install. These issues undermine trust in the platform and block meaningful testing of other features.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Delete objects from the UI (header button, explorer hover action, command palette)
- Save an object and see only the actually-changed fields in the event log (no phantom body.set, no false "(new)" markers)
- Open Table View and Cards View and see their objects listed
- Create any object and see a correct `dcterms:created` timestamp in table views
- Install business-planning model and get all 33 SHACL shapes loaded into the triplestore
- Run `docker compose up --build` on a fresh volume without SQLite permission errors or nginx setgid crashes

### Entry point / environment

- Entry point: http://localhost:4000 (browser)
- Environment: Docker Compose dev stack
- Live dependencies involved: RDF4J triplestore, SQLite

## Completion Class

- Contract complete means: unit tests for object.delete command handler, diff-based save logic, dcterms:created injection; E2E tests for delete flow, table/cards rendering
- Integration complete means: full CRUD cycle (create → edit → delete) works end-to-end through the browser
- Operational complete means: docker compose up --build succeeds on fresh and existing volumes

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- Create an object, edit it (change one field), verify event log shows only the changed field
- Delete that object, verify it's gone from explorer, views, and SPARQL
- Open Table View with "All Types" → see objects listed
- Open Cards View → cards render
- Install business-planning model on a clean triplestore → verify all 33 NodeShapes are in the shapes graph
- `docker compose down && docker compose up --build -d` succeeds with all services healthy

## Risks and Unknowns

- **Model loading (#4a)** — may be stale data from an older installer version, not a code bug. First task should be diagnostic: uninstall/reinstall on current codebase before investigating the pipeline. If reinstall loads all shapes, the fix is just documentation.
- **Object deletion design** — event-sourced soft delete vs hard delete is a design decision. Soft delete (tombstone triple) preserves history but complicates queries. Hard delete (remove from current graph) is simpler but loses provenance.
- **Save diffing** — the form submit goes through htmx, and the body save through fetch. Both need to diff against original values, which means tracking original state on page load.
- **Table/Cards view bugs** — may be a SPARQL query issue or a template rendering issue. Need to diagnose before fixing.

## Existing Codebase / Prior Art

- `backend/app/commands/handlers/` — existing command handlers (object_create, object_patch, body_set, edge_create, edge_patch). No object_delete handler exists.
- `backend/app/commands/schemas.py` — command type union. Needs object.delete added.
- `frontend/static/js/workspace.js:1177` — `saveCurrentObject()` always POSTs body without diffing against `editor._sempkmSavedContent`. Verified.
- `frontend/static/js/editor.js:127` — `saveBody()` sends body unconditionally.
- `backend/app/models/loader.py:50` — `load_jsonld_file()` uses rdflib Graph.parse(format="json-ld"). Verified.
- `backend/app/services/models.py:281` — `_build_insert_data_sparql()` serializes all triples. Pipeline looks mechanically correct.
- `backend/app/services/models.py:350` — `install()` pipeline. Verified 12-step process.
- `docker-compose.yml` — security_opt already removed from frontend (fixed during tour). Need permanent fix in Dockerfile entrypoint for volume permissions.

## Relevant Requirements

- No specific requirement IDs — these are regressions/gaps in validated features

## Scope

### In Scope

- **#4a** Diagnose model loading — uninstall/reinstall business-planning model first; investigate pipeline only if shapes still don't load
- **#29** Implement object.delete command (backend handler + event store operation + materialization delete)
- **#29** Object delete UI (button on object header bar, explorer hover action, command palette entry, confirmation dialog)
- **#30** Diff-based save — track original field values on page load, only send changed fields in object.patch, skip body.set when body unchanged
- **#36** Fix Generic Table View "No objects found" bug
- **#41** Fix Cards View broken rendering
- **#63** Auto-set dcterms:created on object.create command handler
- **#1, #2** Permanent Docker fix — entrypoint script that chowns /app/data to sempkm user on container start

### Out of Scope / Non-Goals

- UI polish (colors, spacing, styling) — that's M052 (Design System)
- View toolbar rework (pills, variants) — that's M050 (View System)
- New features (marketplace, composable explorer) — later milestones
- E2E test suite remediation (existing queue item) — separate from functional fixes

## Technical Constraints

- Object deletion must be event-sourced (produce an immutable event, then remove from current graph)
- Save diffing must not break the htmx form submission pattern — may need a hidden field or JS interception
- Docker entrypoint must be idempotent (safe to run on every container start)

## Integration Points

- `backend/app/commands/` — new handler registration in dispatcher
- `backend/app/events/store.py` — EventStore.commit() for delete operations
- `frontend/static/js/workspace.js` — save diffing, delete button wiring
- `frontend/static/js/editor.js` — body save diffing
- `backend/Dockerfile` — entrypoint script for permissions

## Open Questions

- Soft delete vs hard delete — leaning toward hard delete (remove triples from current graph) with the event preserving what was deleted for audit. User can undo via compensating event.
- Should object.delete cascade to edges? Probably yes — delete edges where the object is subject or object.
