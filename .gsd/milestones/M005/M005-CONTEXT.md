# M005: Platform Polish & Foundation — Context

**Gathered:** 2026-03-14  
**Status:** Ready for planning

## Project Description

SemPKM is a semantics-native PKM platform. After M004 completed the type system (full CRUD for classes, properties, shapes), the system is functionally rich but has accumulated UX rough edges and architectural gaps that will compound if left unaddressed. This milestone polishes daily-use UX, adds the minimum viable schema migration path, introduces an operations log, and produces research designs for three larger features.

## Why This Milestone

**UX gaps erode trust.** The tag tree only nests one level despite users having multi-segment tags (`garden/cultivate/roses`). Tag fields are plain text with no autocomplete. These are small fixes with outsized impact on the feel of the product.

**Schema iteration is blocked.** Model authors cannot update shapes, views, or ontology after a model is in use — there's no upgrade path. We hit this directly when `editHelpText` additions couldn't reach the triplestore. The minimum viable fix (`refresh_artifacts`) is small and high-value.

**Observability is developer-only.** Model installs, inference runs, and validation passes log to Docker stdout. Users and model authors have no visibility into what the system did and when. An RDF-native operations log closes this gap and provides a natural place to review PROV-O alignment.

**Design debt on views and VFS.** The views system duplicates entries per type, and VFS v2 has a design doc that needs refinement against current state. Both need research before implementation, and doing that research now prevents building on shaky assumptions later.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Navigate multi-level tag hierarchies in the By Tag explorer (e.g. `#garden` → `cultivate` → `roses`)
- Get tag suggestions while typing in tag fields on edit forms
- See an operations log in the admin/debug section showing model installs, inference runs, and other system activities with timestamps and actor info
- Update a Mental Model's shapes/views/rules without uninstalling (refresh endpoint)

### Research outcomes:

- Design doc: PROV-O alignment plan for events and operations log
- Design doc: Generic views with query binding (views rethink)
- Design doc: VFS v2 refinement against current codebase

### Entry point / environment

- Entry point: `http://localhost:3000/browser/` (workspace), `http://localhost:3000/admin/` (admin)
- Environment: local dev (Docker Compose)
- Live dependencies: triplestore (RDF4J)

## Completion Class

- Contract complete means: tag tree nests N levels, autocomplete returns existing tags, refresh endpoint updates shapes graph, operations log entries appear in admin UI
- Integration complete means: all features work in the running Docker stack with real data
- Operational complete means: none (local dev only)

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- A multi-segment tag like `garden/cultivate/roses` renders as a 3-level nested tree in the explorer
- Tag autocomplete in edit forms suggests existing tags from the graph
- `POST /admin/models/{name}/refresh-artifacts` updates shapes graph with new `sh:description` values without touching user data
- Operations log shows timestamped entries for model operations in admin/debug UI
- Three design docs exist with concrete proposals for PROV-O alignment, views rethink, and VFS v2

## Risks and Unknowns

- **Tag tree performance** — deep nesting with many tags could produce expensive SPARQL queries. Likely manageable with existing data volumes but worth monitoring.
- **PROV-O alignment scope** — could spiral into a large vocabulary migration. Must be bounded to "design doc with migration plan" not "rewrite all events."
- **Operations log storage** — storing in the triplestore alongside user data could affect query performance if log volume grows. May need a separate named graph with retention policy.
- **Views rethink scope** — easy to over-design. Must produce a concrete, implementable proposal not an abstract framework.

## Existing Codebase / Prior Art

- `backend/app/browser/workspace.py` — `_handle_by_tag()` at line 150, flat tag query
- `backend/app/templates/browser/tag_tree.html` — flat folder rendering
- `backend/app/services/models.py` — `install()` / `remove()` lifecycle, no refresh path
- `backend/app/events/store.py` — `EventStore.append()` with `sempkm:performedBy` provenance
- `backend/app/rdf/namespaces.py` — `PROV` namespace registered but unused
- `.gsd/design/VFS-V2-DESIGN.md` — existing VFS v2 design draft

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- New requirements to be created for this milestone (tag hierarchy, autocomplete, refresh endpoint, operations log)
- Research outputs feed future milestones (views, VFS, PROV-O migration)

## Scope

### In Scope

- Hierarchical tag tree with full `/` delimiter nesting
- Tag autocomplete endpoint and edit form integration
- `refresh_artifacts` API endpoint for model shapes/views/rules
- RDF operations log with PROV-O metadata, admin/debug UI
- PROV-O alignment design doc (audit current vs standard, migration plan)
- Views rethink design doc (generic views + query binding)
- VFS v2 design refinement against current codebase

### Out of Scope / Non-Goals

- Implementing the views rethink (future milestone)
- Implementing VFS v2 changes (future milestone)
- Migrating existing events to PROV-O predicates (future milestone, per design doc)
- Full versioned migration framework (only refresh_artifacts MVP)
- Tag management UI (create/rename/merge tags)

## Technical Constraints

- Backend: Python + FastAPI, all data in RDF4J triplestore
- Frontend: htmx + vanilla JS (no frameworks)
- Operations log must be RDF in the triplestore (not SQL, not flat files)
- PROV-O usage should be standard-compliant where adopted

## Integration Points

- Triplestore — operations log stored as RDF, tag queries, shapes refresh
- Docker Compose — API restart for template changes
- Admin UI — operations log display
- Workspace explorer — tag tree rendering
- Edit forms — tag autocomplete

## Open Questions

- **Operations log graph IRI** — `urn:sempkm:ops-log` as a dedicated named graph? Or per-entry named graphs like events?
- **Log retention** — should old entries be pruned, or is triplestore volume manageable long-term?
- **PROV-O depth** — how much of the PROV-O vocabulary is useful vs overhead? `prov:Activity` + `prov:wasAssociatedWith` + `prov:startedAtTime` covers 90% of the value.
- **Tag autocomplete UX** — dropdown on focus, or type-ahead after 2+ chars? How to handle creating new tags vs selecting existing?
