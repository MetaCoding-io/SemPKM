# Requirements: SemPKM v2.3

**Defined:** 2026-03-01
**Core Value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## v2.3 Requirements

### Dockview Migration

- [x] **DOCK-01**: User can open and manage object tabs rendered in dockview-core panels (Phase A: editor-pane area replaces Split.js; old HTML5 drag system removed in same commit)
- [x] **DOCK-02**: User can save named workspace layouts and restore them via the Command Palette; layouts persist across sessions

### Object View

- [x] **VIEW-01**: Object view shows Markdown body by default with properties collapsed; user can reveal/collapse properties with one click; preference persists per object IRI
- [x] **VIEW-02**: Object types with multiple manifest-declared views show a tab bar above the view body; user can switch between views; active view persists per type IRI

### FTS

- [x] **FTS-04**: User can find objects with typo-tolerant fuzzy matching (edit distance ~1); fuzzy mode is a user-controlled toggle in the Ctrl+K palette; tokens <5 chars always use exact match

### Bug Fixes

- [x] **BUG-01**: User sees correctly grouped concept cards when group-by is applied
- [x] **BUG-02**: User can access and use VFS mount configuration from the Settings page
- [x] **BUG-03**: Broken view switch buttons are removed from the object view (replaced by VIEW-02 carousel tab bar)

### Testing

- [x] **TEST-01**: Playwright E2E tests for SPARQL console operations pass against live stack (no `test.skip()`)
- [x] **TEST-02**: Playwright E2E tests for FTS keyword search pass against live stack (no `test.skip()`)
- [x] **TEST-03**: Playwright E2E tests for WebDAV VFS operations pass against live stack (no `test.skip()`)
- [ ] **TEST-04**: Playwright E2E tests cover all v2.3 user-visible features (dockview panels, carousel view switching, fuzzy FTS, named layout save/restore)

## Future Requirements

### v2.4+ Dockview

- **DOCK-03**: Full dockview Phase B migration — sidebar panels into dockview (deferred: Phase A must stabilize first)
- **DOCK-04**: Model-provided default layouts in Mental Model manifest (deferred: user layouts sufficient for v2.3)

### v2.4+ Views

- **VIEW-03**: Cross-model view composition and user-added views for carousel (deferred: design review needed)

### SPARQL Interface (future milestone)

**Permissions:**
- [ ] **SQ-01**: User's SPARQL queries are automatically scoped to graphs they have permission to read; owner can opt into all-graphs mode; members/guests cannot access event graphs or other users' draft graphs
- [ ] **SQ-02**: Admin can define SPARQL execution policies (e.g., query timeout limits, result size caps, UPDATE prohibition) per role

**Autocomplete:**
- [ ] **SQ-03**: SPARQL editor offers prefix autocomplete from the project's prefix registry (user > model > LOV > built-in layers)
- [ ] **SQ-04**: SPARQL editor offers class and property autocomplete derived from installed Mental Model ontologies and SHACL shapes
- [ ] **SQ-05**: Autocomplete suggestions show human-readable labels alongside IRIs (using the label service precedence chain)

**UI Pills:**
- [ ] **SQ-06**: IRIs and prefixed names in the SPARQL editor render as compact, styled pills showing the human-readable label; clicking a pill navigates to the object or expands the full IRI
- [ ] **SQ-07**: Prefix declarations in the query header render as collapsed pill chips that can be expanded/removed inline

**Query History:**
- [ ] **SQ-08**: User can browse a searchable, filterable history of previously executed queries with execution timestamp, duration, and result count
- [ ] **SQ-09**: Query history is persisted server-side (not just localStorage) and accessible across devices/sessions

**Saved Queries:**
- [ ] **SQ-10**: User can save/bookmark a SPARQL query with a name and optional description; saved queries appear in a dedicated panel or palette section
- [ ] **SQ-11**: User can share a saved query with other workspace members via a shareable link or by publishing it to a shared query library
- [ ] **SQ-12**: Saved queries support parameterization (template variables like `$type` or `$label` that prompt the user on execution)

**Named Queries as Views:**
- [ ] **SQ-13**: User can promote a saved query to a "named query" that appears as a reusable view in the object browser's view switcher
- [ ] **SQ-14**: Named query views execute their SPARQL query on demand and render results using the standard view renderers (table, cards, graph)
- [ ] **SQ-15**: Named query views can be included in Mental Model manifests as model-provided views alongside built-in view specs

### Global Lint Status (future milestone)

**Global Lint Dashboard:**
- [ ] **LINT-01**: User can open a Global Lint Status view (as a dockview panel or dedicated page) that shows all SHACL validation results across every object in the knowledge base, with summary counts by severity (violations, warnings, infos) and a per-object breakdown
- [ ] **LINT-02**: Global lint view updates automatically after each EventStore.commit() via the existing AsyncValidationQueue; user sees the latest validation state without manual refresh
- [ ] **LINT-03**: User can see a visual health indicator (e.g., status bar badge or sidebar icon) showing the overall knowledge base validation status at a glance (pass / N violations / N warnings)

**Filtering and Search:**
- [ ] **LINT-04**: User can filter lint results by severity level (violations only, warnings only, infos only, or combinations)
- [ ] **LINT-05**: User can filter lint results by object type (e.g., show only Note violations, only Project violations) using the Mental Model's type registry
- [ ] **LINT-06**: User can search/filter lint results by keyword across message text, property path, and object label
- [ ] **LINT-07**: User can sort lint results by severity, object name, property path, or timestamp

**Fix Guidance:**
- [ ] **LINT-08**: Each lint result displays a human-readable "how to fix" message that explains what the constraint expects and how to resolve the violation (not just "constraint violated" but "This field requires at least 1 value -- add a title to fix")
- [ ] **LINT-09**: Fix guidance messages are derived from SHACL shape metadata (sh:description, sh:name, constraint component type) and augmented with Mental Model-provided help text when available
- [ ] **LINT-10**: Common constraint violations (sh:minCount, sh:maxCount, sh:datatype, sh:pattern, sh:class) have built-in human-friendly message templates that produce actionable guidance without requiring shape authors to write custom messages

**Click-to-Edit Workflow:**
- [ ] **LINT-11**: User can click any lint result row and the corresponding object opens in a dockview pane (or focuses the existing pane if already open), scrolled/focused to the relevant field
- [ ] **LINT-12**: After editing and saving the object, the lint view updates to reflect whether the issue is resolved, removed from the list, or still present
- [ ] **LINT-13**: User can work through lint results sequentially: fix one issue, see it disappear from the global list, click the next issue, fix it -- a continuous triage workflow without navigating away from the lint view

## Out of Scope

| Feature | Reason |
|---------|--------|
| Animated cube-flip / 3D carousel for view rotation | HIGH cost, zero functional gain, existing flip is already a maintenance burden |
| SHACL editor environment | v2.4 — research + custom editor design needed |
| Low-code GUI builder (Notion/Airflow-like) | v2.4+ — major new capability, not scoped |
| Full dockview Phase B (sidebar panels) | v2.4 — Phase A must stabilize first |
| VFS custom setups + disable toggle | v2.4+ |
| Per-note property visibility stored in RDF | localStorage per-IRI is acceptable; storing UI state in data graph is an anti-pattern |
| SPARQL UPDATE as general write surface | By design -- bypasses event sourcing; named queries are read-only SELECT/CONSTRUCT |
| Federated SPARQL (SERVICE keyword) | Security and performance concerns; single-triplestore scope for now |
| Automated lint auto-fix (programmatic correction of violations) | Too risky -- automated edits bypass user intent; fix guidance is sufficient |
| Custom user-defined validation rules beyond SHACL | SHACL shapes are the validation language; custom rules belong in Mental Model shapes |
| Cross-object relationship validation (e.g., orphan detection) | Distinct feature from per-object SHACL validation; future graph-level health check |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FTS-04 | Phase 29 | Complete |
| DOCK-01 | Phase 30 | Complete |
| VIEW-01 | Phase 31 | Complete |
| VIEW-02 | Phase 32 | Complete |
| BUG-01 | Phase 32 | Complete |
| BUG-03 | Phase 32 | Complete |
| DOCK-02 | Phase 33 | Complete |
| BUG-02 | Phase 33 | Complete |
| TEST-01 | Phase 34 | Complete |
| TEST-02 | Phase 34 | Complete |
| TEST-03 | Phase 34 | Complete |
| TEST-04 | Phase 34 | Pending |

**Coverage:**
- v2.3 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-01*
*Last updated: 2026-03-03 after adding Global Lint Status future requirements*
