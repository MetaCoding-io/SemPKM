# Requirements: SemPKM

**Defined:** 2026-02-28
**Core Value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## v2.2 Requirements

Requirements for the Data Discovery milestone. Each maps to roadmap phases 23-28.

### Full-Text Search

- [ ] **FTS-01**: User can search knowledge base by keyword (full-text search across all literal values)
- [ ] **FTS-02**: Search results show object type, label, and matching snippet
- [ ] **FTS-03**: Search integrated into command palette (Ctrl+K)

### SPARQL Console

- [ ] **SPARQL-01**: User can execute SPARQL queries via embedded Yasgui interface
- [ ] **SPARQL-02**: SPARQL results display IRIs as clickable SemPKM object links
- [ ] **SPARQL-03**: Query history preserved across sessions (localStorage)

### Virtual Filesystem

- [ ] **VFS-01**: User can mount SemPKM objects as files via WebDAV (read-only)
- [ ] **VFS-02**: Object bodies rendered as Markdown files with SHACL-derived frontmatter
- [ ] **VFS-03**: Mount configuration accessible via Settings page

### UI Polish & Integration

- [ ] **POLSH-01**: Expander/collapse icons visible in sidebar tree in both light and dark themes
- [ ] **POLSH-02**: User can move sidebar panels between left/right sidebar in object browser
- [ ] **POLSH-03**: Object-contextual panels show visual indicator distinguishing them from global views
- [ ] **POLSH-04**: Each v2.2 feature area (FTS, SPARQL, VFS) has a dedicated Playwright E2E integration test file

## Future Candidates

Tracked for future milestones. Not in v2.2 roadmap.

### Shell & Navigation (v2.3)

- **DOCK-01**: Full dockview-core migration — Phase A (inner editor-pane split)
- **DOCK-02**: Named workspace layouts (user-defined, model-provided panel arrangements)
- **CSS-01**: Full theming system (user-selectable themes, model-contributed themes)

### Low-Code & Workflows (v2.4)

- **LC-01**: Low-code UI builder (compose basic components tied to SemPKM actions)
- **LC-02**: Minimal workflow orchestration (orchestrated forms/views)

### Cross-Cutting (ongoing)

- **BKLNK-01**: Backlinks panel (incoming references for any object)
- **EDGE-01**: Edge inspector panel
- **EDGE-02**: Inline wiki-link creation
- **EXPORT-01**: JSON-LD export for objects/collections
- **AI-01**: AI Copilot chat (data, SPARQL generation, writing assistance)
- **VEC-01**: pgvector/semantic search (deferred — validate keyword FTS in v2.2 first)

## Out of Scope

Explicitly excluded. Documented to prevent scope creep.

| Feature | Reason |
|---------|--------|
| VFS write path (Phase 27) | Requires API token auth design — deferred to end of v2.2 |
| Full dockview-core migration | Phase A deferred to v2.3; only lightweight panel rearrangement in v2.2 |
| SPARQL UPDATE as write surface | By design — bypasses event sourcing |
| Real-time collaborative editing | CRDT/OT complexity, v2+ at earliest |
| Semantic/vector search (pgvector) | Deferred until keyword FTS validated in v2.2 |
| Mobile native app | Web-first; responsive design and eventual PWA |
| Ontology editor | Consume via Mental Models; use Protege for authoring |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SPARQL-01 | Phase 23 | Pending |
| SPARQL-02 | Phase 23 | Pending |
| SPARQL-03 | Phase 23 | Pending |
| FTS-01 | Phase 24 | Pending |
| FTS-02 | Phase 24 | Pending |
| FTS-03 | Phase 24 | Pending |
| VFS-01 | Phase 26 | Pending |
| VFS-02 | Phase 26 | Pending |
| VFS-03 | Phase 26 | Pending |
| POLSH-01 | Phase 28 | Pending |
| POLSH-02 | Phase 28 | Pending |
| POLSH-03 | Phase 28 | Pending |
| POLSH-04 | Phase 28 | Pending |

**Coverage:**
- v2.2 requirements: 13 total
- Mapped to phases: 13
- Unmapped: 0 ✓

*Note: Phase 25 (CSS Token Expansion) and Phase 27 (VFS Write + Auth) are infrastructure/preparatory phases with no standalone user-visible requirements — they enable v2.3 and Phase 28 respectively.*

---
*Requirements defined: 2026-02-28*
*Last updated: 2026-02-28 after initial definition*
