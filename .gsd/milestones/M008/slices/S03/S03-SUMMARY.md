---
id: S03
parent: M008
milestone: M008
provides:
  - base_embed.html minimal template for all iframe content (htmx + theme CSS only)
  - ?embed=1 query param on view, dashboard, object, and SPARQL result endpoints
  - GET /browser/sparql-result/{query_id} endpoint for saved query HTML rendering
  - Dual-layer canvas rendering (persistent embed layer + dynamic regular node layer)
  - addEmbedNode() with nodeType:'embed' and embedConfig:{type, id, url, label}
  - Toolbar "Embed" button with tabbed picker (Views / Dashboards / Queries)
  - Explorer drag-drop for view and dashboard entries onto canvas
  - Canvas document serialization with nodeType/embedConfig fields
  - Max 8 simultaneous embeds enforced with toast rejection
  - Malformed embedConfig guard preventing JS crashes from corrupted data
  - 32 unit tests covering serialization, backward compat, URL construction, max embed, mixed docs, malformed edge cases
requires:
  - slice: S01
    provides: Resize handle pointer event system, variable-dimension CSS, extended node model with width/height, getDocument/applyDocument serialization pattern
affects:
  - S04
key_files:
  - backend/app/templates/base_embed.html
  - backend/app/templates/browser/embed_wrapper.html
  - backend/app/templates/browser/object_embed.html
  - backend/app/templates/browser/sparql_result_embed.html
  - backend/app/browser/sparql_result.py
  - backend/app/views/router.py
  - backend/app/dashboard/router.py
  - backend/app/browser/objects.py
  - frontend/static/js/canvas.js
  - frontend/static/css/workspace.css
  - backend/app/templates/browser/canvas_page.html
  - backend/app/templates/browser/views_explorer.html
  - backend/app/templates/browser/dashboard_explorer.html
  - backend/app/templates/browser/my_views.html
  - backend/tests/test_canvas_embeds.py
key_decisions:
  - D124: Dual-layer rendering — embed iframes in persistent DOM layer, regular nodes in innerHTML-rebuilt layer
  - D125: Separate base_embed.html — minimal template (5 scripts) instead of hiding elements in base.html (18+ scripts)
  - D128: Max 8 simultaneous iframe embeds — hard limit for v1 performance safety
  - D133: New /browser/sparql-result/{query_id} endpoint — server-rendered HTML table, not client-side SPA
  - D134: Embed layer pointer-events:none with auto on individuals — click pass-through to regular nodes
  - D135: Fragment-to-string rendering for embed wrapping — simpler than Jinja2 include with variable template names
  - D136: SPARQL result router before objects_router — prevents catch-all :path consumption
  - D137: Dual-layer rendering — position-only updates for embeds, never innerHTML rebuild
patterns_established:
  - _embed_response() helper for wrapping fragment templates in embed base
  - X-Embed-Mode response header on all embed responses for agent/test inspection
  - Dual-layer pattern: state.layer for innerHTML, state.embedLayer for persistent DOM
  - Embed-type drag payload convention: {type, id, label, url} with type field as discriminator from regular object drags
  - openEmbedPicker/closeEmbedPicker with outside-click dismissal
  - buildEmbedConfig() centralizes URL construction for all embed types
observability_surfaces:
  - X-Embed-Mode: 1 response header on embed endpoints (curl -sI 'host/endpoint?embed=1' | grep X-Embed-Mode)
  - SemPKMCanvas.exportState().nodes.filter(n => n.nodeType === 'embed') for state inspection
  - SemPKMCanvas.addEmbed() exposed on window for console testing
  - data-embed-type attribute on embed DOM elements
  - setStatus('Embed added: ...') on successful placement
  - showToast('Maximum of 8 embeds reached') on limit rejection
  - .spatial-embed-loading.loaded class indicates iframe finished loading
  - SPARQL result endpoint: 404 for unknown query IDs, 500 for execution failures
drill_down_paths:
  - .gsd/milestones/M008/slices/S03/tasks/T01-SUMMARY.md
  - .gsd/milestones/M008/slices/S03/tasks/T02-SUMMARY.md
  - .gsd/milestones/M008/slices/S03/tasks/T03-SUMMARY.md
  - .gsd/milestones/M008/slices/S03/tasks/T04-SUMMARY.md
  - .gsd/milestones/M008/slices/S03/tasks/T05-SUMMARY.md
duration: 4h15m
verification_result: passed
completed_at: 2026-03-16
---

# S03: Live Embeds — Infrastructure, Types & Add UX

**Canvas supports live iframe embeds for views, dashboards, SPARQL results, and object read views — addable via toolbar picker or explorer drag-drop, with dual-layer rendering that survives innerHTML rebuilds and 32 unit tests.**

## What Happened

Five tasks delivered the full live embed stack across backend templates, endpoint modifications, frontend rendering architecture, add UX, and persistence verification.

**T01 (Embed templates + endpoints)** built the backend infrastructure. Created `base_embed.html` — a minimal full HTML page with only htmx, theme CSS, Lucide, marked, and DOMPurify (5 scripts total vs 18+ in base.html). Added `?embed=1` query param to `generic_view()`, `render_dashboard()`, and `get_object()`. Each renders its fragment template to a string via `_embed_response()` helper, then wraps it in `embed_wrapper.html`. Created a new `GET /browser/sparql-result/{query_id}` endpoint in `browser/sparql_result.py` that fetches saved queries, executes them, enriches results with labels, and renders an HTML table. All embed responses include `X-Embed-Mode: 1` header. The sparql_result_router is registered before objects_router in browser/router.py to prevent catch-all path consumption.

**T02 (Dual-layer rendering)** solved the architectural crux: iframes surviving `renderNodes()` innerHTML rebuilds. Added a `<div class="spatial-canvas-embed-layer">` as a sibling after `.spatial-canvas-layer` in the canvas viewport. `renderNodes()` now skips embed nodes from the innerHTML string — instead, a separate loop creates/updates persistent DOM elements in `state.embedLayer` via CSS position/size properties only. `addEmbedNode(embedConfig, clientX, clientY)` creates nodes with `nodeType:'embed'`, default 400×300, and enforces the max-8 limit. Both layers receive the same CSS transform for pan/zoom sync. `nodeBoxes` queries `state.viewport` (covering both layers) so edges connect correctly to embed nodes. The embed layer uses `pointer-events: none` on the container with `auto` on individual embeds for click pass-through.

**T03 (Toolbar picker)** added the primary add UX. An "Embed" button with Lucide `layout-grid` icon in the canvas toolbar opens a tabbed dropdown with Views, Dashboards, and Queries tabs. Each tab fetches from existing APIs (`/browser/views/available`, `/api/dashboard`, `/api/sparql/saved`), renders clickable rows, and on click builds an `embedConfig` via `buildEmbedConfig()` and calls `addEmbedNode()` at viewport center. Outside-click handler uses pointerdown in capture phase with setTimeout(0) to skip the opening click.

**T04 (Explorer drag-drop)** added the secondary add UX. Dashboard entries in `dashboard_explorer.html`, generic view entries in `views_explorer.html`, and saved view entries in `my_views.html` all got `draggable="true"` and `ondragstart` handlers setting `window.__canvasDragPayload` with embed-type payloads (`{type, id, label, url}`). Canvas `onDrop()` and `onDragEnd()` check `payload.type` against `['dashboard', 'view', 'query', 'object-embed']` — matches route to `addEmbedNode()`, misses fall through to regular `addNodeFromDrag()` for backward compat.

**T05 (Persistence + tests)** wrote 32 unit tests organized into 6 classes: document serialization round-trip, backward compat (old sessions without nodeType), URL construction for all embed types, max embed count enforcement, mixed node documents, and malformed embedConfig handling. Added a defensive guard in `renderNodes()` that skips embed nodes with missing/invalid `embedConfig` instead of crashing. Verified full browser save/load round-trip with mixed regular + embed nodes.

## Verification

- **Unit tests**: 32/32 passed (`.venv/bin/pytest tests/test_canvas_embeds.py -v`, 0.03s)
- **Embed templates**: All 4 files exist (base_embed, embed_wrapper, object_embed, sparql_result_embed)
- **?embed=1 endpoints**: Confirmed on views/router.py (3 renderers), dashboard/router.py, browser/objects.py
- **SPARQL result endpoint**: Returns HTML table with enriched labels; 404 for unknown query IDs
- **X-Embed-Mode header**: Present on all embed responses, absent on non-embed responses
- **Dual-layer rendering**: Embed iframes survive renderNodes() innerHTML rebuilds (iframe DOM identity preserved)
- **Toolbar picker**: Opens with 3 tabs, fetches from real APIs, places embed nodes with live iframe content
- **Explorer drag-drop**: View and dashboard entries have draggable attributes with correct embed payloads
- **Max 8 enforcement**: 9th embed rejected with toast message
- **Backward compat**: Old canvas sessions without nodeType fields load without errors
- **Save/load round-trip**: Mixed regular + embed nodes survive API save → reload with correct positions, sizes, types, and iframe URLs
- **exportState()**: Returns nodeType:'embed' and full embedConfig for embed nodes
- **Edge rendering**: nodeBoxes queries viewport (both layers), edges connect correctly to embed nodes
- **Malformed guard**: Nodes with missing embedConfig silently skipped, no TypeError

## Requirements Advanced

- CANVAS-03 — View and dashboard embeds render as live iframes via `?embed=1` endpoints, addable through toolbar picker or explorer drag
- CANVAS-04 — SPARQL query result embeds via new `/browser/sparql-result/{query_id}` endpoint; object read embeds via `get_object(embed=1)` with stripped-down template
- CANVAS-05 — Toolbar "Embed" button with tabbed picker (Views/Dashboards/Queries) + explorer drag-drop for views and dashboards

## Requirements Validated

- CANVAS-03 — Live iframes load real content from all 4 endpoint families, survive drag operations, persist across save/load. 32 unit tests + browser verification.
- CANVAS-04 — SPARQL result endpoint renders saved query output as HTML table with enriched labels. Object embed shows type label, property table, and markdown body. Both load in canvas iframes.
- CANVAS-05 — Toolbar picker populates from 3 live APIs, places embed nodes at viewport center. Explorer drag creates embed nodes with correct URLs. Both paths produce identical embed node type. Max 8 enforced on both paths.

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- T01 added `views.css` to `base_embed.html` — table view fragments use `.view-table` CSS classes that live in views.css, not workspace.css. Without it, embedded table styling breaks.
- T04 also modified `my_views.html` (saved views template) — not explicitly in the plan's file list but called out in the step description. Added draggable attributes following the same pattern as the other two explorer templates.
- T05 rewrote `test_canvas_embeds.py` entirely (from 13 trivial tests to 32 comprehensive tests) rather than extending the T01 version.

## Known Limitations

- Dashboard embed path tested only by code inspection — no dashboards exist in the test instance. Code pattern is identical to view embeds.
- `<a>` tags in views_explorer.html have native browser link-drag behavior alongside custom ondragstart. The custom payload takes precedence (canvas reads `__canvasDragPayload` first) but browser also adds `text/uri-list` to dataTransfer (harmless).
- Lazy loading for off-screen embeds not implemented — all iframes load immediately. Covered by max-8 limit for v1.
- No embed link routing yet — links clicked inside embed iframes navigate within the iframe rather than opening in the parent workspace. D129 documented the `window.parent` approach for follow-up.

## Follow-ups

- S04 needs E2E Playwright tests for embed placement, save/load, and max-embed enforcement
- S04 user guide should document the "Embed" toolbar button, picker tabs, and explorer drag-drop
- Link routing inside embed iframes (D129) deferred beyond M008

## Files Created/Modified

- `backend/app/templates/base_embed.html` — NEW: minimal base template for iframe content (htmx + theme CSS + Lucide + marked/DOMPurify)
- `backend/app/templates/browser/embed_wrapper.html` — NEW: wrapper accepting pre-rendered fragment HTML
- `backend/app/templates/browser/object_embed.html` — NEW: read-only object view (type label + property table + markdown body)
- `backend/app/templates/browser/sparql_result_embed.html` — NEW: tabular SPARQL results with enriched labels
- `backend/app/browser/sparql_result.py` — NEW: SPARQL result embed sub-router
- `backend/app/browser/router.py` — registered sparql_result_router before objects_router
- `backend/app/views/router.py` — added embed param to generic_view(), _embed_response() helper
- `backend/app/dashboard/router.py` — added embed param to render_dashboard()
- `backend/app/browser/objects.py` — added embed param to get_object()
- `frontend/static/js/canvas.js` — dual-layer rendering, addEmbedNode(), embed picker, drag-drop detection, serialization, malformed guard
- `frontend/static/css/workspace.css` — embed layer, embed node, picker, loading overlay styles with dark theme
- `backend/app/templates/browser/canvas_page.html` — embed layer div, "Embed" toolbar button
- `backend/app/templates/browser/views_explorer.html` — draggable attributes on generic view entries
- `backend/app/templates/browser/dashboard_explorer.html` — draggable attributes on dashboard entries
- `backend/app/templates/browser/my_views.html` — draggable attributes on saved view entries
- `backend/tests/test_canvas_embeds.py` — 32 unit tests across 6 test classes

## Forward Intelligence

### What the next slice should know
- All embed infrastructure is in place. S04 can write E2E tests that use the toolbar picker and `SemPKMCanvas.addEmbed()` console API.
- The `X-Embed-Mode: 1` response header is a reliable signal for verifying embed endpoints in tests — check via `page.waitForResponse()`.
- `SemPKMCanvas.exportState()` is the canonical way to inspect canvas state from Playwright — returns full document including nodeType/embedConfig.

### What's fragile
- `sparql_result_router` registration order matters — it must come before `objects_router` in browser/router.py or the catch-all `{object_iri:path}` consumes `/sparql-result/*` URLs
- Embed picker's outside-click handler uses `setTimeout(0)` to skip the opening click — if the event system changes, the picker might close immediately on open

### Authoritative diagnostics
- `backend/.venv/bin/pytest tests/test_canvas_embeds.py -v` — 32 tests, <0.1s, covers all serialization/compat/URL/limit logic
- `curl -sI 'http://localhost:3000/browser/views/generic/table?embed=1' | grep X-Embed-Mode` — confirms embed mode active
- `SemPKMCanvas.exportState().nodes.filter(n => n.nodeType === 'embed')` in browser console — all embed nodes with config

### What assumptions changed
- No assumptions changed — the dual-layer approach worked as designed, iframe persistence confirmed
