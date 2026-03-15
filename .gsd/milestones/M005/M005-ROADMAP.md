# M005: Platform Polish & Foundation

**Vision:** Polish daily-use UX (tags, autocomplete), unblock model iteration (schema refresh), add system observability (operations log), and produce actionable design docs for views, VFS v2, and PROV-O alignment.

## Success Criteria

- Tags with `/` delimiters render as nested tree nodes at arbitrary depth in the By Tag explorer
- Tag input fields in edit forms offer autocomplete with existing tag values from the graph
- A `refresh_artifacts` endpoint updates a model's shapes/views/rules graphs without touching user data or requiring uninstall
- An operations log in admin/debug shows timestamped, structured entries for system activities (model install, inference, validation)
- Operations log entries use PROV-O vocabulary (`prov:Activity`, `prov:wasAssociatedWith`, `prov:startedAtTime`)
- Design doc for PROV-O alignment exists with audit of current predicates, migration plan, and recommendation on user-facing exposure
- Design doc for views rethink exists with concrete data model, UI wireframes, and migration path from current per-type views
- Design doc for VFS v2 exists refined against current codebase state with implementation priorities

## Key Risks / Unknowns

- **Operations log PROV-O modeling** — first real usage of PROV-O in the system; if the vocabulary proves awkward for simple log entries, we may need a lighter wrapper. Retire early by building the log first.
- **Tag tree query complexity** — hierarchical grouping by `/` segments in SPARQL may require string manipulation functions (REPLACE, regex). RDF4J supports these but performance with large tag sets is unknown.
- **Views rethink scope** — risk of over-designing. Must stay grounded in "what can we build in one milestone" not "ideal architecture."

## Proof Strategy

- Operations log PROV-O modeling → retire in S01 by proving log entries round-trip through triplestore and render in admin UI
- Tag tree query complexity → retire in S02 by proving multi-level nesting works with real imported data (Ideaverse vault has `/`-delimited tags)

## Verification Classes

- Contract verification: backend pytest for refresh endpoint, tag query parsing, operations log service; browser verification for tag tree and autocomplete
- Integration verification: all features exercised against running Docker stack with real Ideaverse data
- Operational verification: none (local dev)
- UAT / human verification: tag tree visual review, operations log readability, design doc review

## Milestone Definition of Done

This milestone is complete only when all are true:

- All implementation slices pass their verification (tests + browser)
- Tag tree, autocomplete, refresh endpoint, and operations log work in the running stack
- Three design docs exist and are reviewed (PROV-O, views, VFS v2)
- E2E test coverage for new user-visible features
- User guide updated for tag tree, autocomplete, operations log, refresh endpoint

## Requirement Coverage

- Covers: TAG-01 (hierarchical tree), TAG-02 (autocomplete), MIG-01 (refresh artifacts), LOG-01 (operations log)
- Partially covers: PROV-01 (alignment — design only, implementation deferred)
- Leaves for later: VIEW-01 (views rethink — design only), VFS-01 (v2 — design only)
- Orphan risks: none

## Slices

- [ ] **S01: Operations Log & PROV-O Foundation** `risk:high` `depends:[]`
  > After this: admin/debug UI shows timestamped operations log entries using PROV-O vocabulary; model install/inference/validation activities are logged to RDF

- [ ] **S02: Hierarchical Tag Tree** `risk:medium` `depends:[]`
  > After this: By Tag explorer nests tags at arbitrary depth using `/` as delimiter; real Ideaverse tags render as multi-level tree

- [ ] **S03: Tag Autocomplete** `risk:low` `depends:[S02]`
  > After this: tag fields in edit forms suggest existing tag values as user types; new tags can still be entered freely

- [ ] **S04: Model Schema Refresh** `risk:medium` `depends:[]`
  > After this: `POST /admin/models/{name}/refresh-artifacts` updates shapes/views/rules graphs from disk without uninstall; admin UI has a "Refresh" button on installed models

- [ ] **S05: PROV-O Alignment Design** `risk:low` `depends:[S01]`
  > After this: design doc at `.gsd/design/PROV-O-ALIGNMENT.md` audits current event predicates vs PROV-O, proposes migration plan, and recommends what to expose in UI

- [ ] **S06: Views Rethink Design** `risk:low` `depends:[]`
  > After this: design doc at `.gsd/design/VIEWS-RETHINK.md` proposes generic views + query binding data model, UI flow, and migration from current per-type views

- [ ] **S07: VFS v2 Design Refinement** `risk:low` `depends:[]`
  > After this: `.gsd/design/VFS-V2-DESIGN.md` updated with implementation priorities, composable strategy chain decision, and current-state audit

- [ ] **S08: E2E Tests & Docs** `risk:low` `depends:[S01,S02,S03,S04]`
  > After this: Playwright tests cover tag tree, autocomplete, refresh endpoint, and operations log; user guide pages updated

## Boundary Map

### S01 (Operations Log)

Produces:
- `OperationsLogService` with `log_activity(message, actor, activity_type, related_resources)` method
- `urn:sempkm:ops-log` named graph with `prov:Activity` entries
- Admin/debug UI endpoint rendering log entries
- PROV-O usage patterns established for S05 to audit

Consumes:
- nothing (first slice)

### S01 → S05

Produces:
- Working PROV-O usage in operations log (concrete reference for design doc audit)

### S02 (Tag Tree)

Produces:
- Updated `_handle_by_tag()` returning hierarchical structure with `/` nesting
- Updated `tag_tree.html` template with recursive folder rendering
- Tag children endpoint supporting parent-prefix filtering

Consumes:
- nothing (independent)

### S02 → S03

Produces:
- Tag query infrastructure (existing tag values endpoint) reusable for autocomplete

### S04 (Schema Refresh)

Produces:
- `POST /admin/models/{name}/refresh-artifacts` endpoint
- `ModelService.refresh_artifacts(model_name)` method
- Admin UI "Refresh" button on model detail page

Consumes:
- nothing (independent)

### S01,S02,S03,S04 → S08

Produces:
- All user-visible features working in the stack

Consumes:
- All implementation slices complete
