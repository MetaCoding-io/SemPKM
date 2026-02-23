# Milestones

## v1.0 MVP (Shipped: 2026-02-23)

**Phases completed:** 9 phases, 26 plans, ~354 tasks
**Timeline:** 2 days (2026-02-21 to 2026-02-23)
**Commits:** 158 | **Files:** 227 | **Lines:** ~19,900 LOC (Python 9,230 + JS 2,584 + HTML 1,918 + CSS 3,360 + JSON-LD 2,643)
**Audit:** 43/43 requirements | 47/47 integration wires | 4/4 E2E flows | Status: tech_debt (non-blocking)

**Delivered:** A semantics-native personal knowledge management platform where users install a Mental Model and immediately create, browse, and explore structured knowledge through auto-generated forms, table/card/graph views, and SHACL validation — with passwordless multi-user auth and event provenance.

**Key accomplishments:**
- Event-sourced RDF data platform with immutable event store, 5-command write API, and SPARQL reads on RDF4J
- Semantic intelligence: label resolution (4-predicate COALESCE), prefix registry (4-layer), async SHACL validation with immutable reports
- Mental Model packaging system with manifest validation, Basic PKM starter (4 types, shapes, views, seed data)
- IDE-style workspace with SHACL-driven create/edit forms, CodeMirror Markdown editor, command palette, lint panel
- Multi-renderer data browsing: table (sort/filter/paginate), cards (3D flip), graph (Cytoscape.js with layout picker)
- Passwordless multi-user auth (setup wizard, magic links), owner/member/guest RBAC, server-side auth on all 33+ endpoints, user provenance on every write

**Tech debt carried forward:**
- 5 human verification items (setup wizard, auth redirect, logout, model install/remove)
- Cookie secure=False (local dev only)
- SMTP deferred (magic link tokens logged to console)
- Dual SQLAlchemy engine instances (harmless for SQLite)
- No logout button in UI sidebar

**Archives:** milestones/v1.0-ROADMAP.md, milestones/v1.0-REQUIREMENTS.md, milestones/v1.0-MILESTONE-AUDIT.md

---

