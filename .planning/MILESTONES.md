# Milestones

## v2.5 Polish, Import & Identity (Shipped: 2026-03-09)

**Phases completed:** 8 phases (44-51), 22 plans
**Timeline:** 3 days (2026-03-07 → 2026-03-09)
**Commits:** 184 | **Files:** 257 | **Lines:** +28,502 / -1,649
**Codebase:** ~47K Python, ~7K JS
**Requirements:** 23/23 complete

**Delivered:** Full Obsidian vault import wizard (upload → scan → type mapping → property mapping → preview → batch import with SSE progress); WebID identity layer (Ed25519 keys, RDF profile documents with content negotiation, fediverse rel="me" verification); IndieAuth provider (OAuth2 + PKCE, consent screen, token management); spatial canvas UX overhaul (per-node controls, nav tree drag-drop, named sessions); comprehensive user guide (27 chapters covering v2.0-v2.5).

**Key accomplishments:**
- Obsidian Import Wizard — full ZIP upload → scan → type/property mapping → preview → batch import pipeline with SSE progress, wiki-link and tag edge resolution
- WebID Profiles — per-user Ed25519 key pairs (Fernet-encrypted), RDF profile documents (FOAF + W3C Security Vocabulary), content negotiation (Turtle/JSON-LD/HTML), `rel="me"` links for Mastodon/fediverse verification
- IndieAuth Provider — OAuth2 authorization code flow with mandatory PKCE, consent screen, token introspection, refresh token rotation, authorized apps management UI
- Spatial Canvas UX — per-node expand/delete/chevron controls with provenance-scoped collapse, HTML5 drag-drop from nav tree with custom MIME types, named session management (save-as, auto-restore, session index)
- UI Polish — CodeMirror CSS variable theming, dockview tab type icons, dynamic sidebar accent colors, capture-phase keyboard shortcuts, VFS markdown preview toggle
- User Guide — 27 chapters across 9 parts covering all features from v2.0-v2.5, glossary with 11 new terms, screenshot capture spec

**Archives:** milestones/v2.5-ROADMAP.md, milestones/v2.5-REQUIREMENTS.md

---

## v2.4 Inference & Polish (Shipped: 2026-03-06)

**Phases completed:** 9 phases, 20 plans, 0 tasks

**Key accomplishments:**
- (none recorded)

---

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

**Phases completed:** 3 phases (20-22), 9 plans
**Timeline:** 2026-02-28 → 2026-03-01

**Delivered:** All 4 v2.2 architectural decisions committed with rationale + v2.2 handoffs (LuceneSail FTS, Yasgui SPARQL console, wsgidav VFS, dockview-core UI shell); DECISIONS.md created as canonical reference; 4 tech debt items shipped (Alembic migrations, SMTP email, session cleanup, ViewSpec cache).

**Key accomplishments:**
- Committed DEC-01..04: LuceneSail, Yasgui CDN, wsgidav+a2wsgi, dockview-core — all 4 RESEARCH.md files annotated with decision + v2.2 handoff
- Created DECISIONS.md consolidating all decisions with cross-cutting concerns and v2.2 phase sequencing
- Alembic replaces SQLAlchemy `create_all` — schema migrations now version-controlled with asyncio.to_thread bridge
- SMTP email delivery for magic links with console fallback; ViewSpec TTL cache (300s/64 entries) wired to model install events

**Archives:** milestones/v2.1-ROADMAP.md, milestones/v2.1-REQUIREMENTS.md

---


## v2.2 Data Discovery (Shipped: 2026-03-01)

**Phases completed:** 6 phases (23-28), 14 plans, 13/13 requirements satisfied
**Timeline:** 2026-03-01 (intensive single-day execution)

**Delivered:** Full-text keyword search via RDF4J LuceneSail integrated into the Ctrl+K command palette; embedded SPARQL console via Yasgui CDN with IRI click-through; WebDAV VFS (read + write) via wsgidav with API token auth and Settings UI; CSS token architecture expanded to 108 tokens; sidebar panel drag-reorder and contextual panel indicators; Playwright E2E test suites for all 3 feature areas. Post-ship: event log polish (tabular grid, user names, button colors), Event Console page (/events), relations panel collapsible rollup.

**Key accomplishments:**
- SPARQL Console: Yasgui v4.5.0 CDN embed with custom YASR cell renderer for SemPKM IRI pill links, dark mode CSS overrides, and localStorage query persistence
- FTS Keyword Search: LuceneSail-wrapped NativeStore with SearchService (SPARQL magic predicates), GET /api/search endpoint, Ctrl+K palette integration with type icons and match snippets
- CSS Token Expansion: two-tier primitive (`--_*`) / semantic (`--color-*`, `--tab-*`, `--panel-*`) architecture expanded to 108 tokens; dockview-sempkm-bridge.css pattern file for v2.3 migration
- VFS Read-Only: wsgidav + a2wsgi WSGI bridge, SyncTriplestoreClient, SemPKMDAVProvider hierarchy (Root→Model→Type→Resource), object bodies as Markdown+SHACL-frontmatter files with TTL directory cache
- VFS Write + Auth: SHA-256 API token model, SemPKMWsgiAuthenticator, write path with begin_write/end_write hooks → event store, ETag concurrency (SHA-256 hash), Settings UI with token generation/revocation
- UI Polish: chevron icon token fixes (light+dark), full 4-panel HTML5 drag-reorder (insert-before/after, localStorage persistence), tab-type-aware contextual accent bar, Playwright E2E suites for SPARQL/FTS/VFS

**Tech debt carried forward:**
- Cookie secure=False (local dev only — production config deferred)
- Dual SQLAlchemy engine instances (harmless for SQLite)
- Edit form helptext property not yet in SHACL types
- E2E tests for SPARQL/FTS/VFS use test.skip() graceful degradation pending live service validation

**Archives:** milestones/v2.2-ROADMAP.md, milestones/v2.2-REQUIREMENTS.md

---

