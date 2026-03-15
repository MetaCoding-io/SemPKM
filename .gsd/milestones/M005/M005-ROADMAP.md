# M005: Platform Polish & Foundation

**Vision:** Migrate query/view data from SQL to RDF (unifying user and model queries), polish daily-use UX (tags, autocomplete), unblock model iteration (schema refresh), add system observability (operations log), and produce actionable design docs for views, VFS v2, and PROV-O alignment.

## Success Criteria

- Saved queries, shared queries, promoted views, and query history stored as RDF in the triplestore (not SQL)
- Model-shipped named queries appear alongside user queries in the same UI, marked read-only
- Tags with `/` delimiters render as nested tree nodes at arbitrary depth in the By Tag explorer
- Tag input fields in edit forms offer autocomplete with existing tag values from the graph
- A `refresh_artifacts` endpoint updates a model's shapes/views/rules graphs without touching user data or requiring uninstall
- An operations log in admin/debug shows timestamped, structured entries for system activities (model install, inference, validation)
- Operations log entries use PROV-O vocabulary (`prov:Activity`, `prov:wasAssociatedWith`, `prov:startedAtTime`)
- Design doc for PROV-O alignment exists with audit of current predicates, migration plan, and recommendation on user-facing exposure
- Design doc for views rethink exists with concrete data model, UI wireframes, and migration path from current per-type views
- Design doc for VFS v2 exists refined against current codebase state with implementation priorities

## Key Risks / Unknowns

- **Query SQL→RDF migration** — 4 SQL tables, ~65 references in sparql/router.py alone. Must preserve all existing SPARQL console functionality (history, save, share, promote) while changing the storage layer. Data migration for existing saved queries needed. Highest risk in the milestone.
- **Operations log PROV-O modeling** — first real usage of PROV-O in the system; if the vocabulary proves awkward for simple log entries, we may need a lighter wrapper.
- **Tag tree query complexity** — hierarchical grouping by `/` segments in SPARQL may require string manipulation functions. RDF4J supports these but performance with large tag sets is unknown.
- **Views rethink scope** — risk of over-designing. Must stay grounded in "what can we build in one milestone" not "ideal architecture."

## Proof Strategy

- Query SQL→RDF migration → retire in S01 by proving full SPARQL console round-trip (save, load, share, promote, history) works against RDF storage with zero SQL dependency
- Operations log PROV-O modeling → retire in S02 by proving log entries round-trip through triplestore and render in admin UI
- Tag tree query complexity → retire in S03 by proving multi-level nesting works with real imported data (Ideaverse vault has `/`-delimited tags)

## Verification Classes

- Contract verification: backend pytest for query service (RDF), refresh endpoint, tag query parsing, operations log service; browser verification for SPARQL console, tag tree, and autocomplete
- Integration verification: all features exercised against running Docker stack with real Ideaverse data; SPARQL console verified with existing saved queries after migration
- Operational verification: none (local dev)
- UAT / human verification: SPARQL console UX unchanged after migration, tag tree visual review, operations log readability, design doc review

## Milestone Definition of Done

This milestone is complete only when all are true:

- All implementation slices pass their verification (tests + browser)
- SPARQL console works identically after SQL→RDF migration (save, share, promote, history)
- Tag tree, autocomplete, refresh endpoint, and operations log work in the running stack
- Three design docs exist and are reviewed (PROV-O, views, VFS v2)
- E2E test coverage for new user-visible features
- User guide updated for tag tree, autocomplete, operations log, refresh endpoint

## Requirement Coverage

- Covers: QRY-01 (queries in RDF), TAG-01 (hierarchical tree), TAG-02 (autocomplete), MIG-01 (refresh artifacts), LOG-01 (operations log)
- Partially covers: PROV-01 (alignment — design only, implementation deferred)
- Leaves for later: VIEW-01 (views rethink — design only), VFS-01 (v2 — design only)
- Orphan risks: none

## Slices

- [x] **S01: Query Storage SQL→RDF Migration** `risk:high` `depends:[]`
  > After this: SavedSparqlQuery, SharedQueryAccess, PromotedQueryView, and SparqlQueryHistory all stored as RDF in the triplestore; SPARQL console UI works identically; existing saved queries migrated; SQL tables dropped

- [x] **S02: Operations Log & PROV-O Foundation** `risk:high` `depends:[]`
  > After this: admin/debug UI shows timestamped operations log entries using PROV-O vocabulary; model install/inference/validation activities are logged to RDF

- [ ] **S03: Hierarchical Tag Tree** `risk:medium` `depends:[]`
  > After this: By Tag explorer nests tags at arbitrary depth using `/` as delimiter; real Ideaverse tags render as multi-level tree

- [ ] **S04: Tag Autocomplete** `risk:low` `depends:[S03]`
  > After this: tag fields in edit forms suggest existing tag values as user types; new tags can still be entered freely

- [ ] **S05: Model Schema Refresh** `risk:medium` `depends:[]`
  > After this: `POST /admin/models/{name}/refresh-artifacts` updates shapes/views/rules graphs from disk without uninstall; admin UI has a "Refresh" button on installed models

- [ ] **S06: PROV-O Alignment Design** `risk:low` `depends:[S02]`
  > After this: design doc at `.gsd/design/PROV-O-ALIGNMENT.md` audits current event predicates vs PROV-O, proposes migration plan, and recommends what to expose in UI

- [ ] **S07: Views Rethink Design** `risk:low` `depends:[S01]`
  > After this: design doc at `.gsd/design/VIEWS-RETHINK.md` proposes generic views + query binding data model, UI flow, and migration from current per-type views; assumes queries are in RDF

- [ ] **S08: VFS v2 Design Refinement** `risk:low` `depends:[S01]`
  > After this: `.gsd/design/VFS-V2-DESIGN.md` updated with scope/strategy/prefix model, bidirectional path contract, and implementation priorities; assumes queries are in RDF

- [ ] **S09: E2E Tests & Docs** `risk:low` `depends:[S01,S02,S03,S04,S05]`
  > After this: Playwright tests cover query migration, tag tree, autocomplete, refresh endpoint, and operations log; user guide pages updated

## Boundary Map

### S01 (Query SQL→RDF)

Produces:
- `QueryService` backed by RDF (CRUD for saved queries, history, sharing, promotion)
- `urn:sempkm:queries` named graph with `sempkm:SavedQuery` resources
- Per-user query history as RDF (or append to ops-log graph — TBD with S02)
- Model-shipped named queries loadable from model views graphs alongside user queries
- Data migration script for existing SQL saved queries → RDF
- Alembic migration to drop SQL tables

Consumes:
- nothing (first slice)

### S01 → S07, S01 → S08

Produces:
- Queries as RDF resources referenceable by IRI from both views and VFS mounts
- Unified query registry (model + user) that design docs can assume

### S02 (Operations Log)

Produces:
- `OperationsLogService` with `log_activity(message, actor, activity_type, related_resources)` method
- `urn:sempkm:ops-log` named graph with `prov:Activity` entries
- Admin/debug UI endpoint rendering log entries
- PROV-O usage patterns established for S06 to audit

Consumes:
- nothing (independent of S01)

### S02 → S06

Produces:
- Working PROV-O usage in operations log (concrete reference for design doc audit)

### S03 (Tag Tree)

Produces:
- Updated `_handle_by_tag()` returning hierarchical structure with `/` nesting
- Updated `tag_tree.html` template with recursive folder rendering
- Tag children endpoint supporting parent-prefix filtering

Consumes:
- nothing (independent)

### S03 → S04

Produces:
- Tag query infrastructure (existing tag values endpoint) reusable for autocomplete

### S05 (Schema Refresh)

Produces:
- `POST /admin/models/{name}/refresh-artifacts` endpoint
- `ModelService.refresh_artifacts(model_name)` method
- Admin UI "Refresh" button on model detail page

Consumes:
- nothing (independent)

### S01,S02,S03,S04,S05 → S09

Produces:
- All user-visible features working in the stack

Consumes:
- All implementation slices complete
