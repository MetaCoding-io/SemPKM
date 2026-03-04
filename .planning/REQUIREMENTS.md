# Requirements: SemPKM v2.4

**Defined:** 2026-03-03
**Core Value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## v2.4 Requirements

### OWL 2 RL Inference

- [x] **INF-01**: User adds a participant to a Project; the Person's detail page automatically shows the Project in their "participatesIn" list without manual inverse entry (OWL 2 RL inference materializes `owl:inverseOf` triples)
- [ ] **INF-02**: Mental Models can ship SHACL-AF rules (sh:TripleRule, sh:SPARQLRule) that pyshacl executes with `advanced=True`; inferred triples are stored in `urn:sempkm:inferred` named graph and visible in object views and graph visualization

### Global Lint Dashboard

- [ ] **LINT-01**: User can open a Global Lint Status view (as a dockview panel or dedicated page) that shows all SHACL validation results across every object in the knowledge base, with summary counts by severity (violations, warnings, infos) and a per-object breakdown
- [ ] **LINT-02**: Global lint view updates automatically after each EventStore.commit() via the existing AsyncValidationQueue; user sees the latest validation state without manual refresh
- [ ] **LINT-03**: User can see a visual health indicator (e.g., status bar badge or sidebar icon) showing the overall knowledge base validation status at a glance (pass / N violations / N warnings)
- [ ] **LINT-04**: User can filter lint results by severity level (violations only, warnings only, infos only, or combinations)
- [ ] **LINT-05**: User can filter lint results by object type (e.g., show only Note violations, only Project violations) using the Mental Model's type registry
- [ ] **LINT-06**: User can search/filter lint results by keyword across message text, property path, and object label
- [ ] **LINT-07**: User can sort lint results by severity, object name, property path, or timestamp

### Edit Form Helptext

- [ ] **HELP-01**: SHACL shapes can declare `sempkm:editHelpText` annotation property; edit forms render it as collapsible markdown below the field, providing context about what to enter and why

### Bug Fixes

- [ ] **BUG-04**: Accent bar on tabs is type-aware (different accent colors per type, not just teal for all)
- [ ] **BUG-05**: Card view borders render correctly in both light and dark themes
- [ ] **BUG-06**: Firefox Ctrl+K opens ninja-keys command palette (not Firefox's native address bar focus)
- [ ] **BUG-07**: Tab accent bar does not bleed into adjacent inactive tabs
- [ ] **BUG-08**: Panel chevron icons are visible in dark mode (not invisible-on-dark)
- [ ] **BUG-09**: Concept search and linking functionality works correctly (search finds concepts, links are created)

### Testing

- [ ] **TEST-05**: Playwright E2E tests cover all v2.4 user-visible features (inference bidirectional links, lint dashboard filtering/sorting, edit form helptext, bug fix verifications)

## Future Requirements

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

### Lint Fix Guidance & Triage (future milestone)

**Fix Guidance:**
- [ ] **LINT-08**: Each lint result displays a human-readable "how to fix" message that explains what the constraint expects and how to resolve the violation
- [ ] **LINT-09**: Fix guidance messages are derived from SHACL shape metadata (sh:description, sh:name, constraint component type) and augmented with Mental Model-provided help text when available
- [ ] **LINT-10**: Common constraint violations (sh:minCount, sh:maxCount, sh:datatype, sh:pattern, sh:class) have built-in human-friendly message templates that produce actionable guidance

**Click-to-Edit Workflow:**
- [ ] **LINT-11**: User can click any lint result row and the corresponding object opens in a dockview pane (or focuses the existing pane if already open), scrolled/focused to the relevant field
- [ ] **LINT-12**: After editing and saving the object, the lint view updates to reflect whether the issue is resolved, removed from the list, or still present
- [ ] **LINT-13**: User can work through lint results sequentially: fix one issue, see it disappear from the global list, click the next issue, fix it — a continuous triage workflow

## Out of Scope

| Feature | Reason |
|---------|--------|
| Animated cube-flip / 3D carousel for view rotation | HIGH cost, zero functional gain, existing flip is already a maintenance burden |
| SHACL editor environment | Future — research + custom editor design needed |
| Low-code GUI builder (Notion/Airflow-like) | Future — major new capability, not scoped |
| Full dockview Phase B (sidebar panels) | v2.5 — Phase A must stabilize first |
| VFS custom setups + disable toggle | Future |
| SPARQL UPDATE as general write surface | By design — bypasses event sourcing |
| Automated lint auto-fix (programmatic correction) | Too risky — automated edits bypass user intent; fix guidance is sufficient |
| Custom user-defined validation rules beyond SHACL | SHACL shapes are the validation language; custom rules belong in Mental Model shapes |
| Cross-object relationship validation (orphan detection) | Distinct feature from per-object SHACL validation; future graph-level health check |
| RDF4J server-side inference (SchemaCachingRDFSInferencer) | Python-side owlrl is sufficient; triplestore reconfiguration deferred |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| INF-01 | Phase 35 | Complete |
| INF-02 | Phase 36 | Planned |
| LINT-01 | Phase 37 | Planned |
| LINT-02 | Phase 37 | Planned |
| LINT-03 | Phase 38 | Planned |
| LINT-04 | Phase 38 | Planned |
| LINT-05 | Phase 38 | Planned |
| LINT-06 | Phase 38 | Planned |
| LINT-07 | Phase 38 | Planned |
| HELP-01 | Phase 39 | Planned |
| BUG-04 | Phase 39 | Planned |
| BUG-05 | Phase 39 | Planned |
| BUG-06 | Phase 39 | Planned |
| BUG-07 | Phase 39 | Planned |
| BUG-08 | Phase 39 | Planned |
| BUG-09 | Phase 39 | Planned |
| TEST-05 | Phase 40 | Planned |

**Coverage:**
- v2.4 requirements: 17 total
- Mapped to phases: 17
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-03*
