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


## v2.0 Tighten Web UI (Shipped: 2026-03-01)

**Phases completed:** 10 phases (10-19), 27 plans, 53 tasks
**Timeline:** 6 days (2026-02-22 → 2026-02-28)
**Commits:** ~202 | **Source LOC:** ~119k total (Python + JS + CSS + HTML)
**Audit:** 46/46 requirements | 10/10 phases | 10/10 integration wires | 6/6 E2E flows | Status: tech_debt (non-blocking)

**Delivered:** A product-grade web UI with VS Code-style split panes, dark mode, a layered settings system, event log explorer with inline diffs and undo, Driver.js guided tours, encrypted LLM connection configuration, and type-specific node icons — on top of the v1.0 semantic RDF platform.

**Key accomplishments:**
- Polished read-only object view with CSS 3D flip animation to edit mode, reference pills with resolved labels and type tooltips, and client-side Markdown rendering
- Grouped collapsible sidebar with Lucide icons, icon-rail collapse (Ctrl+B), and VS Code-style user menu with Popover API
- Dark mode: 35+ CSS custom property token system, anti-FOUC inline script, tri-state toggle (system/light/dark), full migration of ~430 hardcoded colors; CodeMirror Compartment and Cytoscape style rebuild for third-party dark mode
- VS Code-style editor groups: WorkspaceLayout data model, HTML5 drag-and-drop tab management, Split.js destroy-and-recreate, context menu, collapsible bottom panel (SPARQL/Event Log/AI Copilot) with Ctrl+J
- Layered settings system (system < model < user overrides) with VS Code-style two-column UI, search filter, and Modified badges; Fernet-encrypted LLM API key with streaming SSE proxy for AI Copilot
- Browsable event log with cursor-based pagination, filter chips, inline diffs (unified format), and undo via compensating events
- Driver.js guided tours: 10-step workspace orientation and htmx-gated object creation tutorial; Docs & Tutorials hub page
- Node type icon system: IconService reads manifest icon/color declarations, wired into explorer tree, editor tabs, and Cytoscape graph shapes

**Tech debt carried forward:**
- Cookie secure=False (still local dev only — production config deferred)
- SMTP deferred (magic link tokens logged to console)
- Dual SQLAlchemy engine instances (harmless for SQLite)
- Bottom panel SPARQL/AI Copilot tabs are placeholder stubs (implementation in future milestones)
- Edit form helptext property not yet in SHACL types (pending todo)

**Archives:** milestones/v2.0-ROADMAP.md, milestones/v2.0-REQUIREMENTS.md, milestones/v2.0-MILESTONE-AUDIT.md

---


## v2.1 Architecture Decision Gate (Shipped: 2026-03-01)

**Phases completed:** 13 phases, 36 plans, 4 tasks

**Key accomplishments:**
- (none recorded)

---

