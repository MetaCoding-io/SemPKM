---
created: 2026-02-28
phase: 21-research-synthesis
requirement: SYN-01
status: committed
---

# Architectural Decisions — SemPKM v2.2

This document is the single consolidated architectural decision record for SemPKM v2.2 (Data Discovery milestone) and v2.3 (Shell and Navigation milestone). It synthesizes all four committed decisions from Phase 20 into a unified view — one document that answers "what are we building in v2.2 and v2.3, and in what order?" Cross-cutting implementation concerns, sequencing rationale, and the tech debt schedule are included so that v2.2 implementation planning can proceed from this document alone without referring back to individual research files.

---

## Decision Summary

| Decision | Technology Chosen | Status | Target Milestone | Source |
|----------|-------------------|--------|-----------------|--------|
| FTS/Keyword Search | RDF4J LuceneSail | Committed | v2.2 | [phase-20-fts-vector/RESEARCH.md](research/phase-20-fts-vector/RESEARCH.md) |
| SPARQL Console UI | @zazuko/yasgui v4.5.0 (CDN) | Committed | v2.2 | [phase-21-sparql-ui/RESEARCH.md](research/phase-21-sparql-ui/RESEARCH.md) |
| Virtual Filesystem (WebDAV) | wsgidav + a2wsgi | Committed | v2.2 | [phase-22-vfs/RESEARCH.md](research/phase-22-vfs/RESEARCH.md) |
| UI Shell / Panel Layout | dockview-core (incremental Split.js migration) | Committed — Phase A in v2.3 | v2.3 | [phase-23-ui-shell/RESEARCH.md](research/phase-23-ui-shell/RESEARCH.md) |

---

## Decision Details

### FTS/Keyword Search

**Committed approach:** Use RDF4J's built-in LuceneSail to add full-text keyword search by wrapping the existing NativeStore with a LuceneSail delegate in the repository configuration file; defer pgvector semantic search to a later phase (Phase 20b) after PostgreSQL migration.

**Key rationale:**
- Zero new containers, zero sync infrastructure: LuceneSail intercepts all SPARQL UPDATE operations at the SAIL layer and updates the Lucene index synchronously within the same RDF4J transaction — `EventStore.commit()` requires no changes
- SemPKM already runs RDF4J 5.0.1; LuceneSail ships in the distribution; activation requires only a repository config file change (`config/rdf4j/sempkm-repo.ttl`)
- PKM-scale datasets (hundreds to low thousands of objects) are well within LuceneSail's ~100K object limit
- SPARQL-native integration via `search:matches` allows FTS results to be combined with type filters and `FROM <urn:sempkm:current>` graph scoping in a single query

**Explicitly rejected:**
- **OpenSearch/Elasticsearch sidecar** — adds 512MB+ RAM and a custom sync pipeline; disproportionate overhead for PKM scale
- **Apache Jena / Fuseki** — switching triplestores requires rewriting TriplestoreClient and EventStore; incompatible REST API
- **Oxigraph** — no built-in FTS capability (confirmed via GitHub issue #48)
- **GraphDB** — licensing restrictions for commercial use; different API requiring full TriplestoreClient rewrite
- **SQLite FTS5** — acceptable only as a stopgap if PostgreSQL migration is blocked; not the primary path

**Prerequisites before implementation:**
1. Verify `rdf4j-sail-lucene-*.jar` exists in the running container at `/usr/local/tomcat/webapps/rdf4j-server/WEB-INF/lib/`; if absent, extend the Dockerfile to add it and matching Lucene JARs
2. Validate the exact Turtle config property names for LuceneSail in RDF4J 5.x unified namespace (`tag:rdf4j.org,2023:config/`); check `/var/rdf4j/server/templates/` inside the container for built-in templates
3. Validate that `FROM <urn:sempkm:current>` properly restricts LuceneSail results to the current state graph and does not surface subjects from event graphs

**First implementation steps:**
1. Update `config/rdf4j/sempkm-repo.ttl` — wrap NativeStore with LuceneSail delegate; add `luceneDir` pointing to a Docker volume path; add `reindexQuery` scoped to `urn:sempkm:current`
2. Add `lucene_index` Docker volume to `docker-compose.yml`; document migration procedure (backup `rdf4j_data` volume, update config, restart, verify with SPARQL count query)
3. Create `backend/app/services/search.py` — `SearchService.search(query, type_filter, limit)` executes the SPARQL FTS query pattern against the TriplestoreClient
4. Add `GET /api/search?q=term&type=Note&limit=20` endpoint returning `{results: [{iri, title, type, score, snippet}]}`
5. Integrate search UI into command palette (Ctrl+K, requirement FTS-03) using the existing ninja-keys infrastructure from Phase 13

---

### SPARQL Console UI

**Committed approach:** Embed `@zazuko/yasgui` v4.5.0 via CDN directly into a new SPARQL Console template, wired to the existing `/api/sparql` endpoint, with a custom YASR table cell renderer that transforms SemPKM data IRIs into object browser links, and localStorage persistence for query tabs and history (key: `sempkm-sparql`).

**Key rationale:**
- Yasgui is the de facto standard SPARQL query UI (used by Apache Jena Fuseki, GraphDB, and dozens of triplestore products); integrating it gives a production-grade editor with syntax highlighting, autocomplete, result visualization, tabs, and persistence at zero backend development cost
- The Zazuko fork (`@zazuko/yasgui`) is fully MIT-licensed, actively maintained (v4.5.0, mid-2025), and CDN-loadable via unpkg — consistent with SemPKM's pattern for htmx, Cytoscape, Split.js, Lucide, and marked
- The existing `/api/sparql` endpoint already speaks the SPARQL Protocol (POST + `application/x-www-form-urlencoded`); Yasgui requires zero backend changes
- Cookie-based auth (`sempkm_session`) is automatically included by the browser for same-origin requests — no special auth configuration needed

**Explicitly rejected:**
- **@sib-swiss/sparql-editor** — requires VoID metadata as a prerequisite (SemPKM does not generate VoID); adds complexity for marginal autocomplete improvement
- **Comunica Web Client** — federated query engine designed for querying the open web, not a single endpoint; heavy bundle, no editor features
- **SPARQL Playground (AtomGraph)** — client-side only against local RDF data; cannot query remote SPARQL endpoints
- **Custom CodeMirror 6 build** — months of work for functionality Yasgui already provides (syntax highlighting, autocomplete, result rendering, tabs, persistence)
- **Iframe embed** — prevents deep JS integration needed for custom IRI rendering
- **Sidecar container** — Yasgui is a client-side JS library; running it in a container is unnecessary
- **npm build step** — violates SemPKM's no-build-step architectural principle
- **@triply/yasgui fork** — bundles proprietary result visualization plugins not available for self-hosted embedding

**Prerequisites before implementation:**
1. No backend changes required — the existing `/api/sparql` endpoint is already Yasgui-compatible
2. Confirm CDN availability: `https://unpkg.com/@zazuko/yasgui@4.5.0/build/yasgui.*`; for air-gapped deployments, vendor files to `frontend/static/vendor/yasgui/`
3. Confirm `BASE_NAMESPACE` value from application config before implementing the custom YASR cell renderer

**First implementation steps:**
1. Create `backend/app/templates/sparql/console.html` — extends `base.html`; loads Yasgui CSS/JS from unpkg CDN in `{% block head %}`; contains `<div id="yasgui-container"></div>` and initialization script
2. Add SPARQL console route — move from `debug/` router to a `sparql/` router; change access from owner-only to any authenticated user (queries are read-only and scoped to current graph)
3. Configure Yasgui initialization: `endpoint: "/api/sparql"`, `method: "POST"`, `persistenceId: "sempkm-sparql"`, `copyEndpointOnNewTab: false`, `endpointCatalogueSize: 0`; pre-populate default query with SemPKM common prefixes
4. Implement custom YASR table cell renderer — detect `BASE_NAMESPACE` IRIs and render as `<a href="/browser/objects/{encodedIri}" class="sparql-pill">` links; use `shortenIri()` from `app.js` for display text (satisfies SPARQL-02)
5. Add dark mode CSS overrides for Yasgui — add `[data-theme="dark"] .yasgui` overrides to `theme.css`

---

### Virtual Filesystem (WebDAV)

**Committed approach:** Implement a read-only WebDAV virtual filesystem using `wsgidav` v4.3.x bridged into FastAPI via `a2wsgi.WSGIMiddleware`, with a `SemPKMDAVProvider` that maps MountSpec definitions to SPARQL-backed directory listings and markdown+frontmatter file rendering; start with `flat` and `tag-groups` directory strategies; defer write support to a later phase.

**Key rationale:**
- wsgidav provides the exact extension points needed (`DAVProvider`, `DAVCollection`, `DAVNonCollection`) with a sample `VirtualResourceProvider` that almost exactly matches the MountSpec `tag-groups` strategy; the WSGI/ASGI bridge via `a2wsgi.WSGIMiddleware` is a solved, well-documented pattern for FastAPI
- WebDAV is natively supported by macOS Finder, Windows Explorer (Map Network Drive), and Linux file managers (Nautilus, Dolphin) — no special client software required
- The WebDAV protocol is HTTP-only, requiring no kernel-level access; critical for Docker-deployed architecture where managed hosting environments (AWS Fargate, Fly.io, Railway) prohibit `SYS_ADMIN` capability
- All required Python dependencies (`pyyaml`, `rdflib`, `pyshacl`, `cachetools`, `httpx`) are already in `pyproject.toml`; only three new packages needed
- Read-only first bounds risk and delivers immediate user value; write path is complex (diff engine, concurrency control, ETag management) and can be deferred after the read-only MVP is validated

**Explicitly rejected:**
- **FUSE (pyfuse3, fusepy, mfusepy)** — requires `--cap-add SYS_ADMIN` and `--device /dev/fuse` Docker flags; prohibited by managed hosting environments; only viable for local-only Docker or self-hosted VPS
- **Full async WebDAV from scratch** — no production-ready async WebDAV Python library exists; implementing the full protocol from scratch is weeks of work
- **Nginx WebDAV module** — provides only static file serving, not dynamic SPARQL-backed virtual directories; cannot implement the MountSpec concept

**Prerequisites before implementation:**
1. Add Python packages to `pyproject.toml`: `wsgidav>=4.3.3,<5.0`, `a2wsgi>=1.10`, `python-frontmatter>=1.1.0`
2. Add nginx proxy block for `/dav/` path with WebDAV-specific headers (`Depth`, `Destination`, `Overwrite`) and extended timeouts to `frontend/nginx.conf`
3. Create `SyncTriplestoreClient` — the DAVProvider runs in a WSGI thread pool and cannot use `httpx.AsyncClient`; create a synchronous wrapper using `httpx.Client` mirroring the existing `TriplestoreClient` API
4. Resolve API token auth design — WebDAV clients do not support cookie sessions; use Basic auth with API tokens as the password field (username = SemPKM username, password = revocable long-lived token)

**First implementation steps (Phase 22a — read-only MVP):**
1. Create `backend/app/vfs/provider.py` — implement `SemPKMDAVProvider(DAVProvider)` with `get_resource_inst(path, environ)` dispatching to mount handlers
2. Create `backend/app/vfs/collections.py` — implement `MountCollection(DAVCollection)` executing the `sparqlScope` SPARQL query and returning member names; implement `FlatStrategy` returning all results as a flat directory
3. Create `backend/app/vfs/resources.py` — implement `ResourceFile(DAVNonCollection)` rendering a single RDF resource as markdown+frontmatter bytes via `get_content()`
4. Mount wsgidav in `backend/app/main.py` — `app.mount("/dav", WSGIMiddleware(WsgiDAVApp(dav_config)))` with hard-coded mount config pointing to basic-pkm Note type
5. Add `cachetools.TTLCache` for directory listings keyed by `(mount_path, directory_path)` with 30-second TTL

---

### UI Shell / Panel Layout

**Committed approach:** Use `dockview-core` (the framework-agnostic package of Dockview v4.x) as the panel management library, replacing Split.js incrementally across three migration phases (Phase A: inner editor-pane split in v2.3; Phase B: full workspace; Phase C: floating panels and named layouts); simultaneously expand `theme.css` from ~40 to ~91 CSS custom property tokens using a two-tier primitive + semantic architecture (CSS token expansion is v2.2-eligible preparatory work).

**Key rationale:**
- `dockview-core` has zero dependencies and first-class vanilla TypeScript support; content injection via `params.containerElement` (a plain DOM element) is a perfect integration point for htmx's `htmx.ajax()` — matching the existing `loadTabInGroup()` pattern in `workspace-layout.js` exactly
- Dockview's CSS custom property theming (`--dv-*` variables) integrates cleanly with SemPKM's existing `theme.css` token system; `--dv-*` variables can be mapped directly to `--color-*` and `--tab-*` tokens
- Dockview supports drag-and-drop panel reordering, floating panels, popout windows, and named layout serialization (`toJSON()`/`fromJSON()`) — the full feature set required for v2.3 without any framework dependency
- Incremental migration from Split.js bounds risk: Phase A replaces only the inner editor-groups split, keeping the sidebar, nav tree, and bottom panel structure unchanged; this validates the htmx integration before committing to full workspace migration
- The two-tier CSS token architecture (primitive `--_*` + semantic `--color-*`, `--tab-*`, `--panel-*`, etc.) formalizes the existing approach, adds coverage for spacing, typography, and new panel surfaces, and stays under 100 tokens

**Explicitly rejected:**
- **GoldenLayout 2** — DOM reparenting in non-Virtual mode breaks htmx event handlers and internal state; Virtual mode requires managing `position:absolute` overlays manually; LESS-based themes (not CSS custom properties) require a translation layer; no floating panels (only popout windows)
- **Lumino (PhosphorJS)** — requires multiple `@lumino/*` packages; tightly coupled to the Lumino Widget lifecycle model; would require wrapping every htmx partial in a Lumino Widget subclass; Jupyter-centric documentation
- **FlexLayout-React** — requires React as a runtime dependency; SemPKM's architecture is vanilla JS + htmx
- **rc-dock** — requires React; eliminated for the same reason as FlexLayout-React
- **Keep Split.js** — provides only basic two-pane splitting with no tabs, no drag-and-drop, no layout serialization, and no floating panels; `workspace-layout.js` is already 1024+ lines managing these features manually

**Prerequisites before implementation (Phase A):**
1. Measure `dockview-core` bundle size from Bundlephobia; if under ~400KB gzipped, load via CDN; if larger, vendor to `frontend/static/vendor/dockview/`
2. Validate htmx event handler survival on panel reparent — build a minimal test page with a Dockview panel containing an htmx-enhanced element, drag to new group, verify `hx-trigger` events still fire
3. Audit `workspace-layout.js` for htmx patterns using `closest` or ancestor-scoped selectors — these break on reparent; document each occurrence and prepare `htmx.process()` call sites for `onDidLayoutChange` handler
4. Define `dockview-core` component registration: enumerate panel content components (`object-editor`, `relations-panel`, `lint-panel`, `nav-tree`, `graph-view`)

**First implementation steps (CSS token expansion — v2.2 eligible):**
1. Add new CSS tokens to `theme.css`: spacing scale (7 tokens), typography sizes (5 tokens), panel/tab tokens (13 tokens), sidebar tokens (4 tokens), graph tokens (4 tokens), modal tokens (4 tokens), focus ring (1 new token); bringing total from ~40 to ~91 tokens
2. Audit `workspace.css`, `style.css`, `forms.css`, `views.css` to replace hardcoded values with new tokens (pure refactor, no behavior changes)
3. Map `--dv-*` Dockview variables to SemPKM tokens in `theme.css` using a `dockview-sempkm-bridge.css` pattern; add dark mode overrides

---

## Cross-Cutting Concerns

### Authentication Scoping

The four decisions involve three distinct authentication patterns that must be understood together:

- **Session cookie auth (Yasgui, all browser-based features):** The existing `sempkm_session` cookie is automatically included by the browser for same-origin requests. SPARQL Console, FTS search, and browser-based VFS configuration all reuse this pattern without changes.
- **API token Basic auth (wsgidav VFS):** WebDAV clients (Finder, Explorer, Nautilus) do not support cookie sessions. The committed pattern is Basic auth where username = SemPKM username and password = a revocable long-lived API token. This token auth mechanism does not yet exist and must be designed before Phase 22c (VFS write + auth). The token is validated against SemPKM's auth system via a custom wsgidav `HTTPAuthenticator`.
- **LuceneSail (no auth change):** LuceneSail operates at the SAIL layer inside RDF4J; all RDF4J queries already pass through the existing auth pipeline. FTS queries inherit the same auth and graph-scoping (`FROM <urn:sempkm:current>`) as all other SPARQL queries. No new auth surface is introduced.

**Design implication:** The API token system (needed for VFS) is independent of the other three decisions and can be sequenced separately. It must be in place before VFS write support (Phase 22c) but is not required for the read-only MVP (Phase 22a).

### SPARQL Query Patterns

The four decisions interact at the SPARQL query layer in two ways:

- **LuceneSail extends the SPARQL vocabulary:** FTS queries use the `search:` namespace (`search:matches`, `search:query`, `search:score`, `search:snippet`) as magic predicates that join with standard SPARQL triple patterns. The `SearchService` uses `TriplestoreClient` (the existing async client) for FTS queries — no new client needed.
- **Yasgui exposes direct SPARQL access:** The SPARQL Console sends queries directly to `/api/sparql`, which applies prefix injection and `FROM <urn:sempkm:current>` scoping automatically. Users writing queries that use `search:matches` in the SPARQL Console will trigger LuceneSail FTS — the two features compose naturally without additional wiring.
- **wsgidav uses SyncTriplestoreClient:** The DAVProvider runs in a WSGI thread pool (via a2wsgi) and cannot use `httpx.AsyncClient`. A `SyncTriplestoreClient` wrapper using `httpx.Client` must be created. This is the only client that diverges from the standard async pattern. It should mirror the `TriplestoreClient` API but must not share the async client instance.

**Key constraint:** Any new SPARQL query pattern introduced by FTS, VFS, or future features should use `FROM <urn:sempkm:current>` scoping to avoid surfacing subjects from event graphs. This is the established pattern — maintain it consistently.

### CSS Token Usage

The CSS token expansion (from ~40 to ~91 tokens) is cross-cutting work that should land in v2.2 regardless of the Dockview migration timeline:

- **Dockview dependency:** `dockview-core`'s `--dv-*` CSS variables must be mapped to SemPKM's `--color-*` and `--tab-*` tokens in a bridge file. For this mapping to be maintainable, the semantic token layer must be well-defined before Phase A of the Dockview migration.
- **v2.2 benefit independent of Dockview:** New `--panel-*`, `--sidebar-*`, `--spacing-*`, `--font-size-*` tokens formalize values currently hardcoded in `workspace.css`, `style.css`, `forms.css`, and `views.css`. Introducing these tokens is a prerequisite for consistent theming across the new SPARQL Console page and VFS settings UI.
- **Two-tier architecture:** Primitive tokens (`--_*`, e.g. `--_blue-600: #2d5a9e`) are defined first; semantic tokens (`--color-primary`, `--tab-bg-active`, etc.) reference primitives. The dark mode section overrides semantic tokens only — primitives never change between themes.
- **Dockview migration is v2.3, token expansion is v2.2:** CSS token expansion is explicitly categorized as v2.2-eligible preparatory work in the UI Shell decision. Schedule it early in v2.2 so new page templates (SPARQL Console, VFS config) can use the expanded token set.

### Dependency Footprint

The combined new dependency surface across all four decisions is minimal by design:

| Dependency | Type | New Containers | Footprint |
|------------|------|---------------|-----------|
| LuceneSail JAR | JVM library (ships with RDF4J 5.0.1 distribution) | 0 | ~300KB JAR + Lucene JARs in existing RDF4J container |
| @zazuko/yasgui v4.5.0 | CDN JS/CSS (frontend only) | 0 | ~350KB JS + ~50KB CSS, loaded only on SPARQL page |
| wsgidav + a2wsgi + python-frontmatter | Python packages | 0 | 3 new packages in existing `pyproject.toml` |
| dockview-core | CDN or vendor JS/CSS (frontend only) | 0 | ~50-100KB gzipped (needs measurement); loaded only on workspace page |

Total: zero new Docker containers, three new Python packages, two new CDN libraries (page-scoped). This is the lowest possible footprint consistent with the feature requirements.

### Incremental Delivery

Understanding which features can ship independently is essential for sequencing:

- **Yasgui (SPARQL Console):** Fully independent — no backend changes needed; zero prerequisites; ships first in v2.2
- **wsgidav read-only MVP:** Mostly independent — requires `SyncTriplestoreClient` (new) and the three Python packages; does not depend on LuceneSail or Yasgui; can ship in parallel
- **LuceneSail (FTS):** Independent of wsgidav and Yasgui at the code level; however, LuceneSail JAR verification and config validation prerequisites mean it requires upfront infrastructure work before any code is written
- **dockview-core Phase A:** Deferred to v2.3; CSS token expansion (the v2.2 prep work) is independent of all other features and can ship in any sprint
- **VFS write + auth (Phase 22c/22d):** Depends on the API token auth system (new) and a stable read-only VFS; do not attempt before read-only MVP is validated

---

## v2.2 Phase Structure

The following phase structure is derived from the prerequisites and dependencies in the four Handoff sections. Phase numbers continue from Phase 22 (last v2.1 phase).

| Phase | Name | Delivers | Requirements | Depends On | Rationale |
|-------|------|----------|-------------|-----------|-----------|
| 23 | SPARQL Console | Yasgui CDN embed, custom IRI renderer, localStorage persistence | SPARQL-01, SPARQL-02, SPARQL-03 | Nothing (zero backend changes needed) | No prerequisites; highest ROI for lowest effort; ships first to unblock SPARQL testing of other features |
| 24 | FTS Keyword Search | LuceneSail config, SearchService, search API endpoint, Ctrl+K integration | FTS-01, FTS-02, FTS-03 | LuceneSail JAR verification, Turtle config validation (infrastructure prereqs) | JAR verification and config validation must happen first; can proceed in parallel with Phase 23 |
| 25 | CSS Token Expansion | 91-token theme.css, updated workspace/style/forms/views CSS | (preparatory, no v2.2 requirement) | None | Preparatory work for Dockview migration (v2.3); independent of FTS/VFS; natural to group with frontend polish sprint |
| 26 | VFS Read-Only MVP | wsgidav mount, SyncTriplestoreClient, flat strategy, Notes browse/read | VFS-01, VFS-02 | SyncTriplestoreClient (new), 3 Python packages | Read-only first; SyncTriplestoreClient is new engineering but well-defined; defers auth and write complexity |
| 27 | VFS Auth + Settings | API token generation, custom wsgidav auth, MountSpec config UI, tag-groups strategy | VFS-03 | Phase 26 (read-only VFS validated), API token auth design | Auth design must precede this phase; write support deferred until read-only MVP is proven in production |

**Sequencing rationale:**

- **Phase 23 before Phase 24:** Yasgui has no prerequisites and provides immediate value. Shipping it first also provides a SPARQL testing tool for validating LuceneSail FTS queries during Phase 24 development.
- **Phase 24 after infrastructure verification:** The LuceneSail JAR presence check and Turtle config validation must happen before any Phase 24 code is written — if the JAR is absent, a Dockerfile extension is required first.
- **Phase 25 (CSS tokens) between VFS phases:** CSS token expansion is independent of FTS and VFS; positioning it between phases 24 and 26 provides a natural context-switching break while infrastructure (wsgidav thread pool, nginx WebDAV proxy) is set up and tested.
- **Phase 26 before Phase 27:** The read-only VFS MVP must be validated across macOS Finder, Windows Explorer, and Linux Nautilus before write support is attempted. Write path (ETag concurrency, frontmatter diff engine, `python-frontmatter` round-trips) is the highest-risk component; early validation of the read path isolates risk.
- **Phase 27 last:** API token auth is the only new auth mechanism in v2.2; designing it last (after read-only VFS is proven) minimizes the chance of auth design changes requiring VFS rework.

**Note:** Dockview Phase A (inner editor-pane split migration) is v2.3 Phase 1. CSS token expansion (Phase 25 above) is the only UI Shell work in v2.2.

---

## Tech Debt Schedule

### Completed in v2.1 (Phase 22)

| Item | Resolution | Phase |
|------|-----------|-------|
| Alembic migration runner | `asyncio.to_thread` wraps `alembic command.upgrade`; startup runs migrations instead of `create_all` | Phase 22 Plan 01 |
| Session cleanup job | Cleanup runs after service creation on startup; logs only if non-zero sessions purged | Phase 22 Plan 01 |
| SMTP email delivery for magic links | `send_magic_link_email` returns bool; falls through to console fallback on SMTP failure; `app_base_url` config avoids internal container URL in links | Phase 22 Plan 02 |
| ViewSpecService TTL cache | Cache reduces SPARQL queries per view spec lookup; invalidation wired to EventStore | Phase 22 Plan 03 |

### Remaining Known Tech Debt

| Item | Priority | Target | Notes |
|------|----------|--------|-------|
| Cookie `secure=False` | Medium | v2.2 | Needs production config; currently acceptable for local dev |
| Dual SQLAlchemy engine instances | Low | v2.3 | Harmless for SQLite; revisit when PostgreSQL migration is planned |
| `empty_shapes_loader` dead code | Low | v2.3 | Remove during code cleanup sprint |
| Edit form helptext property not in SHACL types | Low | v2.2 or v2.3 | Pending todo from v2.0; no breaking impact |
| Bottom panel SPARQL/AI Copilot tabs are placeholder stubs | Medium | v2.2 / v2.3 | SPARQL tab: replace with Yasgui embed (Phase 23); AI Copilot: deferred to v2.3+ |
| validation/report.py `hash()` fix | Low | v2.2 | Noted as out-of-scope but easily resolved; schedule for early v2.2 cleanup |

### Deferred to v2.3+

| Item | Deferred Because |
|------|-----------------|
| pgvector semantic search (Phase 20b) | Blocked on PostgreSQL migration; `all-MiniLM-L6-v2` model + HNSW index design is documented in FTS RESEARCH.md |
| Dockview Phase A (inner editor-pane split) | v2.3 Phase 1; CSS token expansion (Phase 25) is the only UI Shell work in v2.2 |
| Dockview Phase B (full workspace) | Depends on Phase A validation in production |
| Dockview Phase C (floating panels, named layouts) | After Phase B is stable |
| VFS write support (Phase 22d) | Deferred until read-only MVP is validated; ETag concurrency + frontmatter diff engine are high-risk |
| Model-contributed themes (THEME-02) | Requires Phase B workspace and model manifest parsing |
| Named dashboard layouts (DOCK-02) | Requires Phase C Dockview and layout serialization infrastructure |
| SMTP OAuth2 auth | Out of scope; simple SMTP credentials are sufficient |
| Source model attribution | Lower priority; deferred to v2.2+ |

---

## Implementation Readiness Checklist

The following verifications must be completed before v2.2 development begins:

- [ ] LuceneSail JAR present in Docker image — `docker exec <rdf4j-container> ls /usr/local/tomcat/webapps/rdf4j-server/WEB-INF/lib/rdf4j-sail-lucene-*.jar`
- [ ] Turtle config syntax validated for RDF4J 5.x unified namespace (`tag:rdf4j.org,2023:config/`) — check `/var/rdf4j/server/templates/` inside the container for built-in LuceneSail config templates
- [ ] Yasgui CDN availability confirmed — `curl -I https://unpkg.com/@zazuko/yasgui@4.5.0/build/yasgui.min.js` returns HTTP 200
- [ ] wsgidav >= 4.3.3 available on PyPI — `pip index versions wsgidav` shows 4.3.3
- [ ] CSS token count measured — count `:root` property declarations in `frontend/static/css/theme.css` as baseline before token expansion
- [ ] dockview-core bundle size measured — `npm pack dockview-core` or check Bundlephobia before deciding CDN vs vendor loading strategy
