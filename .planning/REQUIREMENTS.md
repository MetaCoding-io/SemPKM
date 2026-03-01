# Requirements: SemPKM v2.3

**Defined:** 2026-03-01
**Core Value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## v2.3 Requirements

### Dockview Migration

- [ ] **DOCK-01**: User can open and manage object tabs rendered in dockview-core panels (Phase A: editor-pane area replaces Split.js; old HTML5 drag system removed in same commit)
- [ ] **DOCK-02**: User can save named workspace layouts and restore them via the Command Palette; layouts persist across sessions

### Object View

- [ ] **VIEW-01**: Object view shows Markdown body by default with properties collapsed; user can reveal/collapse properties with one click; preference persists per object IRI
- [ ] **VIEW-02**: Object types with multiple manifest-declared views show a tab bar above the view body; user can switch between views; active view persists per type IRI

### FTS

- [ ] **FTS-04**: User can find objects with typo-tolerant fuzzy matching (edit distance ~1); fuzzy mode is a user-controlled toggle in the Ctrl+K palette; tokens <5 chars always use exact match

### Bug Fixes

- [ ] **BUG-01**: User sees correctly grouped concept cards when group-by is applied
- [ ] **BUG-02**: User can access and use VFS mount configuration from the Settings page
- [ ] **BUG-03**: Broken view switch buttons are removed from the object view (replaced by VIEW-02 carousel tab bar)

### Testing

- [ ] **TEST-01**: Playwright E2E tests for SPARQL console operations pass against live stack (no `test.skip()`)
- [ ] **TEST-02**: Playwright E2E tests for FTS keyword search pass against live stack (no `test.skip()`)
- [ ] **TEST-03**: Playwright E2E tests for WebDAV VFS operations pass against live stack (no `test.skip()`)
- [ ] **TEST-04**: Playwright E2E tests cover all v2.3 user-visible features (dockview panels, carousel view switching, fuzzy FTS, named layout save/restore)

## Future Requirements

### v2.4+ Dockview

- **DOCK-03**: Full dockview Phase B migration — sidebar panels into dockview (deferred: Phase A must stabilize first)
- **DOCK-04**: Model-provided default layouts in Mental Model manifest (deferred: user layouts sufficient for v2.3)

### v2.4+ Views

- **VIEW-03**: Cross-model view composition and user-added views for carousel (deferred: design review needed)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Animated cube-flip / 3D carousel for view rotation | HIGH cost, zero functional gain, existing flip is already a maintenance burden |
| SHACL editor environment | v2.4 — research + custom editor design needed |
| Low-code GUI builder (Notion/Airflow-like) | v2.4+ — major new capability, not scoped |
| Full dockview Phase B (sidebar panels) | v2.4 — Phase A must stabilize first |
| VFS custom setups + disable toggle | v2.4+ |
| Per-note property visibility stored in RDF | localStorage per-IRI is acceptable; storing UI state in data graph is an anti-pattern |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| FTS-04 | Phase 29 | Pending |
| DOCK-01 | Phase 30 | Pending |
| VIEW-01 | Phase 31 | Pending |
| VIEW-02 | Phase 32 | Pending |
| BUG-01 | Phase 32 | Pending |
| BUG-03 | Phase 32 | Pending |
| DOCK-02 | Phase 33 | Pending |
| BUG-02 | Phase 33 | Pending |
| TEST-01 | Phase 34 | Pending |
| TEST-02 | Phase 34 | Pending |
| TEST-03 | Phase 34 | Pending |
| TEST-04 | Phase 34 | Pending |

**Coverage:**
- v2.3 requirements: 12 total
- Mapped to phases: 12
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-01*
*Last updated: 2026-03-01 after initial definition*
