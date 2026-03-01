# Requirements: SemPKM

**Defined:** 2026-03-01
**Core Value:** Install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, views, and graph visualizations — no blank-page syndrome, no schema setup.

## v2.1 Requirements

Requirements for v2.1: Architecture Decision Gate. Formalizes completed research and resolves medium-priority tech debt.

### Decisions

- [x] **DEC-01**: Architectural decision for full-text search committed — RDF4J LuceneSail approach, repository config, SPARQL query API design, phased plan (keyword first, vector later)
- [x] **DEC-02**: Architectural decision for SPARQL UI committed — Zazuko Yasgui CDN embed approach, YASR plugin strategy for SemPKM object links, saved query design
- [x] **DEC-03**: Architectural decision for virtual filesystem committed — wsgidav + a2wsgi approach, MountSpec MVP vocabulary (flat + tag-groups), WebDAV client compatibility matrix
- [x] **DEC-04**: Architectural decision for UI shell committed — Dockview-core over GoldenLayout rationale, incremental Split.js migration plan, CSS token vocabulary expansion design

### Synthesis

- [x] **SYN-01**: Consolidated DECISIONS.md created — all 4 architectural decisions, cross-cutting concerns, v2.2 phase structure derived, tech debt schedule

### Tech Debt

- [x] **TECH-01**: Alembic migration runner at startup — replaces `create_all`, proper schema migration support for both SQLite and PostgreSQL
- [x] **TECH-02**: SMTP email delivery — magic links sent via real email (configurable SMTP settings), not logged to console
- [x] **TECH-03**: Session cleanup job — expired sessions purged on startup or via scheduled task
- [x] **TECH-04**: ViewSpecService TTL cache — reduce SPARQL queries per view spec lookup (currently 2 queries per lookup)

## Future Requirements

### v2.2 — Data Discovery

- **FTS-01**: User can search knowledge base by keyword (full-text search across all literal values)
- **FTS-02**: Search results show object type, label, and matching snippet
- **FTS-03**: Search integrated into command palette (Ctrl+K)
- **SPARQL-01**: User can execute SPARQL queries via embedded Yasgui interface
- **SPARQL-02**: SPARQL results display IRIs as clickable SemPKM object links
- **SPARQL-03**: Query history preserved across sessions (localStorage)
- **VFS-01**: User can mount SemPKM objects as files via WebDAV (read-only)
- **VFS-02**: Object bodies rendered as Markdown files with SHACL-derived frontmatter
- **VFS-03**: Mount configuration accessible via Settings page

### v2.3 — Shell & Navigation

- **DOCK-01**: User can drag-and-drop panels to arbitrary positions (Dockview integration)
- **DOCK-02**: User can save named workspace layouts (Dashboards)
- **THEME-01**: User can select from built-in themes (Dark+, Light, High Contrast, Solarized)
- **THEME-02**: Mental Models can contribute theme bundles

## Out of Scope

| Feature | Reason |
|---------|--------|
| SMTP OAuth2 auth | Start with simple SMTP credentials; OAuth2 is complex and can be added later |
| pgvector / semantic search | Phase 20b (vector) deferred to after keyword FTS is validated in v2.2 |
| Dockview full migration | v2.1 is decisions only; implementation is v2.3 |
| Source model attribution | Lower priority, deferred to v2.2+ |
| validation/report.py hash() fix | Lower priority, deferred to v2.2 |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEC-01 | Phase 20 | Complete |
| DEC-02 | Phase 20 | Complete |
| DEC-03 | Phase 20 | Complete |
| DEC-04 | Phase 20 | Complete |
| SYN-01 | Phase 21 | Complete |
| TECH-01 | Phase 22 | Complete |
| TECH-02 | Phase 22 | Complete |
| TECH-03 | Phase 22 | Complete |
| TECH-04 | Phase 22 | Complete |

**Coverage:**
- v2.1 requirements: 9 total
- Mapped to phases: 9
- Unmapped: 0 ✓

---
*Requirements defined: 2026-03-01*
*Last updated: 2026-03-01 — traceability confirmed during roadmap creation*
