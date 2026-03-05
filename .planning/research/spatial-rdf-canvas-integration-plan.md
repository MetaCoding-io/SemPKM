# SemPKM Spatial RDF Canvas — Project-Specific Implementation Plan

## Why this plan is different from the generic PRD plan
The PRD/implementation draft assumes a greenfield React app with canvas-specific APIs. SemPKM today is:
- FastAPI + Jinja templates + htmx shell (no frontend build pipeline in main app).
- Cytoscape-based graph view already present under `/browser/views/graph/*`.
- Server-rendered workspace tabs managed by Dockview, where each view is loaded via htmx into an editor panel.

This plan integrates the canvas incrementally into that architecture so we can ship value without destabilizing the existing graph/browser flows.

---

## 1) Current-codebase fit analysis (concrete integration points)

### Frontend shell and navigation
- Workspace view tabs are opened by `frontend/static/js/workspace.js` and route through `/browser/views/{renderer}/{spec}`.
- Graph view currently renders via template + Cytoscape boot code (`frontend/static/js/graph.js`).
- Base scripts are CDN/static JS loaded from `backend/app/templates/base.html`.

### Backend services we can leverage
- View loading and graph data access already live in `backend/app/views/router.py` + `backend/app/views/service.py`.
- User-scoped settings persistence exists (`/browser/settings/*`) backed by `user_settings` rows via `SettingsService`.
- Event-sourced writes already exist via command dispatch (`/api/commands`), which can later support “agent writes” provenance hooks.

### Implication
We should ship canvas as a new **view renderer type** in the existing workspace flow first, not a separate SPA.

---

## 2) Proposed architecture for SemPKM

## 2.1 Rendering model
- Keep HTMX shell as-is.
- Add a **React Flow island** inside a new template (`browser/canvas_view.html`) mounted to a single DOM root.
- Keep inspector/details on the server side initially (existing right pane + htmx partials), avoiding duplicate state systems.

## 2.2 Frontend packaging decision
Because the app currently has no JS build step, we should choose one of these two tracks before coding:

### Track A (recommended): checked-in bundled asset
- Build a small Vite bundle in a `frontend/canvas-ui/` workspace.
- Commit built artifacts to `frontend/static/js/canvas/`.
- Load with normal `<script src="/js/canvas/main.js">` from template.
- Pros: modern React Flow DX, predictable runtime, no CDN module complexity.
- Cons: introduces build workflow for contributors.

### Track B: CDN ESM only
- Attempt no-build React/ReactDOM/ReactFlow via ESM CDNs.
- Pros: no local build tooling.
- Cons: brittle imports/version pinning/caching/debuggability; higher long-term risk.

Recommendation: **Track A** for maintainability.

## 2.3 Data and persistence model
- Internal saved canvas format = React Flow `toObject()` + SemPKM metadata in `node.data` / `edge.data`.
- Store per-user canvases using `user_settings` first (keyed under `canvas.{canvas_id}`) to avoid introducing a new DB table in MVP.
- If size/scale becomes an issue, migrate to dedicated SQL table (`canvas_documents`) in Beta.

## 2.4 RDF graph source
- Reuse existing graph service primitives where possible.
- Add focused canvas endpoints for predictable payload shape:
  - `GET /api/canvas/{id}`
  - `PUT /api/canvas/{id}`
  - `GET /api/canvas/subgraph?root_uri=&depth=&predicates=`
- Keep query scoping rules consistent with existing current-graph semantics.

---

## 3) Phased implementation plan (SemPKM-specific)

## Phase C0 — Decision gate + thin vertical slice (2–3 days)
**Goal:** de-risk packaging and mount strategy.

Tasks:
1. Finalize Track A vs B packaging.
2. Add a minimal `/browser/views/canvas/{spec_iri}` route and template shell.
3. Mount a hard-coded React Flow graph in workspace tab.
4. Ensure no regression to existing table/card/graph renderers.

Deliverable: canvas tab opens in Dockview and supports pan/zoom with hardcoded nodes.

---

## Phase C1 — Backend canvas document API (3–4 days)
**Goal:** save/restore canvas state using existing auth + user setting infrastructure.

Tasks:
1. Add `backend/app/canvas/router.py` with read/write endpoints.
2. Add lightweight schemas for flow document validation.
3. Implement storage adapter backed by `SettingsService` key namespace:
   - `canvas.{id}.document`
   - `canvas.{id}.meta`
4. Add optimistic concurrency field (`updated_at` or revision token) to avoid accidental overwrite.

Deliverable: exact restore of nodes/edges/viewport after refresh.

---

## Phase C2 — Integrate RDF subgraph loading (4–5 days)
**Goal:** load real resource nodes + RDF edges into canvas.

Tasks:
1. Add subgraph endpoint reusing ViewSpecService/SPARQL helper patterns.
2. Transform response to React Flow node/edge contracts with stable IDs.
3. Add “add node by URI” action in canvas panel UI.
4. Add edge metadata payload for right-pane inspection (predicate IRI, labels).

Deliverable: users can place resources and see RDF edges among present nodes.

---

## Phase C3 — Markdown expansion + link-anchor edges (5–7 days)
**Goal:** make nodes semantically rich and spatially anchored.

Tasks:
1. Reuse markdown rendering conventions from existing `markdown-render.js` behavior where possible (sanitization/link policies).
2. Implement node expand/collapse with markdown preview.
3. Parse rendered links and compute dynamic anchor handles.
4. Trigger `updateNodeInternals(nodeId)` whenever anchors change.
5. Create markdown-link edges to existing target nodes; prompt to add missing targets.

Deliverable: expanded nodes show anchor dots and edges originate from link-aligned handles.

---

## Phase C4 — Agent write streaming MVP (4–6 days)
**Goal:** live node updates while file/resource content changes.

Tasks:
1. Add SSE endpoint under existing API conventions (or bridge to existing event stream if available).
2. Implement `useAgentStream` client hook with reconnect/backoff.
3. Update node markdown incrementally (v1 full-text replace acceptable).
4. Recompute anchors after each update.
5. Badge state: writing / updated / error.

Deliverable: demo where node content visibly updates in real time without page refresh.

---

## Phase C5 — JSON Canvas import/export + perf guardrails (4–5 days)
**Goal:** interoperability and stability at moderate graph size.

Tasks:
1. Export React Flow document to JSON Canvas 1.0 (best effort).
2. Import JSON Canvas into node/edge layout.
3. Add zoom-threshold behavior to hide markdown/anchors when zoomed out.
4. Limit neighbor-expansion batch size and add predicate filters.

Deliverable: 50 nodes / 200 edges remains smooth on modern laptop baseline.

---

## 4) Concrete file-level change map

### New backend modules
- `backend/app/canvas/router.py`
- `backend/app/canvas/schemas.py`
- `backend/app/canvas/service.py`
- `backend/app/canvas/__init__.py`

### Backend integration touchpoints
- `backend/app/main.py` (router registration)
- `backend/app/templates/browser/canvas_view.html` (canvas host)
- `backend/app/views/router.py` (add/route renderer type `canvas` if needed)

### Frontend additions (Track A)
- `frontend/canvas-ui/*` (source + build config)
- `frontend/static/js/canvas/main.js` (built artifact)
- `frontend/static/css/canvas.css`
- `frontend/static/js/workspace.js` (open/load canvas view type)

---

## 5) Testing and rollout strategy

## Automated
- Backend pytest:
  - canvas API CRUD + auth checks.
  - subgraph endpoint contract tests.
  - JSON canvas adapter unit tests.
- Frontend tests (if added in canvas-ui):
  - transform functions, anchor math, import/export.
- E2E Playwright:
  - open canvas tab, add node, save, reload, restore.
  - expand markdown node and verify anchor markers.

## Manual acceptance gates
1. No regression in current table/card/graph views.
2. Canvas doc persists per user session/account as expected.
3. Anchor edges remain attached after node drag, zoom changes, and markdown updates.
4. SSE stream survives brief network drop and resumes cleanly.

## Release strategy
- Ship behind feature flag (`settings.experimental.canvas_enabled`) for one milestone.
- Enable for **all authenticated users** in the initial rollout (no admin-only restriction).

---

## 6) Risks and SemPKM-specific mitigations
- **Build-pipeline drift risk:** committing built assets can drift from source.
  - Mitigation: add CI check that rebuild diff is clean.
- **Anchor measurement instability inside Dockview/htmx lifecycle:** render timing races.
  - Mitigation: schedule anchor measure on `requestAnimationFrame` + `ResizeObserver` + node expansion events.
- **Payload bloat in user_settings:** very large canvases may exceed practical limits.
  - Mitigation: enforce size cap + migrate to dedicated table at Beta.
- **Semantic mismatch between markdown links and RDF URIs:** existing content may mix wiki links/files/IRIs.
  - Mitigation: define canonical link resolver before C3 (see locked decisions below).

---

## 7) Decisions (locked)

The following implementation decisions are now **approved** and should be treated as baseline constraints for execution:

1. **Packaging:** **Track A** (Vite-built, checked-in bundle).
2. **Storage scope (MVP):** **Per-user private** canvases.
3. **Canonical ID:** **RDF URI canonical**; file path retained as metadata.
4. **Link dialect (MVP):** **Standard Markdown links only** (`[text](...)`).
5. **Auto-triples from markdown links:** **No** in MVP (visual edge only).
6. **Rollout policy:** **All authenticated users** (feature enabled broadly, no admin-only preview).

### Execution implications of locked decisions

- Frontend implementation should proceed with `frontend/canvas-ui/` source + committed built output under `frontend/static/js/canvas/` (Track A).
- Canvas persistence should use the existing user-scoped settings path for MVP (`canvas.{id}.*` in `user_settings`), deferring shared/team canvases to a later phase.
- Node identity handling, subgraph lookup, and edge wiring should treat URI as the sole canonical key to avoid duplication conflicts.
- Markdown anchor parsing can scope to standard link tokens in MVP; wiki-link parsing is explicitly out-of-scope for initial delivery.
- Markdown link edges remain UI/visual semantics only in MVP; RDF graph mutation stays opt-in and future-scoped.
- Feature flagging, if used, should target all authenticated users rather than admin-only gating.

These decisions unblock conversion into execution-ready phase plans (`C0-01`, `C1-01`, etc.) matching the existing `.planning/phases/*` workflow.
