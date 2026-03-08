---
phase: quick-32
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - backend/app/canvas/router.py
  - frontend/static/js/canvas.js
autonomous: true
requirements: [QUICK-32]

must_haves:
  truths:
    - "Load button fetches saved canvas from backend and renders nodes"
    - "Load Neighbors button reaches the /api/canvas/subgraph endpoint (not shadowed by {canvas_id})"
    - "Canvas mount auto-loads saved data; if none saved, keeps hardcoded demo nodes"
  artifacts:
    - path: "backend/app/canvas/router.py"
      provides: "Canvas API with correct route ordering"
      contains: "subgraph.*before.*canvas_id"
    - path: "frontend/static/js/canvas.js"
      provides: "Canvas JS with working load and auto-load logic"
  key_links:
    - from: "frontend/static/js/canvas.js"
      to: "/api/canvas/{canvas_id}"
      via: "fetch in loadCanvas()"
      pattern: "fetch.*api/canvas"
    - from: "frontend/static/js/canvas.js"
      to: "/api/canvas/subgraph"
      via: "fetch in loadNeighbors()"
      pattern: "fetch.*api/canvas/subgraph"
---

<objective>
Fix spatial canvas load button, route shadowing, and auto-load behavior after Codex merge.

Purpose: The Codex merge introduced a spatial canvas with three bugs: (1) FastAPI route shadowing where GET /api/canvas/subgraph is captured by GET /api/canvas/{canvas_id} because the parameterized route is defined first, (2) the Load button works but if no canvas has been saved yet it replaces demo nodes with empty data, and (3) auto-load on mount (line 68) similarly wipes demo nodes when no saved canvas exists.

Output: Working canvas with functional Load, Save, and Load Neighbors buttons.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@backend/app/canvas/router.py
@backend/app/canvas/service.py
@backend/app/canvas/schemas.py
@frontend/static/js/canvas.js
@backend/app/templates/browser/canvas_page.html
</context>

<tasks>

<task type="auto">
  <name>Task 1: Fix FastAPI route shadowing -- move /subgraph before /{canvas_id}</name>
  <files>backend/app/canvas/router.py</files>
  <action>
Move the `@router.get("/subgraph")` endpoint definition ABOVE the `@router.get("/{canvas_id}")` endpoint. In FastAPI, routes are matched in definition order. Currently "subgraph" is captured by the `{canvas_id}` path parameter and tries to load a canvas document called "subgraph" (returning empty data). By placing the static `/subgraph` route first, it will match before the parameterized `/{canvas_id}` route.

The fix is simply reordering the function definitions in the file:
1. `get_canvas_subgraph` (GET /subgraph) -- move to BEFORE get_canvas_document
2. `get_canvas_document` (GET /{canvas_id}) -- stays
3. `put_canvas_document` (PUT /{canvas_id}) -- stays (PUT doesn't conflict)
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM && python -c "
from backend.app.canvas.router import router
routes = [(r.path, list(r.methods)) for r in router.routes]
print(routes)
# Verify subgraph comes before {canvas_id} in GET routes
get_paths = [path for path, methods in routes if 'GET' in methods]
assert get_paths.index('/subgraph') < get_paths.index('/{canvas_id}'), 'subgraph must come before {canvas_id}'
print('Route order OK')
" 2>/dev/null || cd /home/james/Code/SemPKM/backend && python -c "
import sys; sys.path.insert(0, '.')
from app.canvas.router import router
routes = [(r.path, list(r.methods)) for r in router.routes]
print(routes)
get_paths = [path for path, methods in routes if 'GET' in methods]
assert get_paths.index('/subgraph') < get_paths.index('/{canvas_id}'), 'subgraph must come before canvas_id'
print('Route order OK')
"</automated>
  </verify>
  <done>GET /api/canvas/subgraph route is defined before GET /api/canvas/{canvas_id} in router.py, so "Load Neighbors" hits the correct endpoint</done>
</task>

<task type="auto">
  <name>Task 2: Fix auto-load and Load button to preserve demo nodes when no saved canvas exists</name>
  <files>frontend/static/js/canvas.js</files>
  <action>
Fix the `loadCanvas` function so that when the backend returns an empty document (no saved canvas), it does NOT replace the current nodes. Currently `applyDocument` unconditionally overwrites `state.nodes` and `state.edges`, so loading an empty saved canvas wipes the hardcoded demo nodes.

In `loadCanvas()` (around line 500), after receiving `data.document`, check if it has actual content before applying:

```javascript
async function loadCanvas(silent) {
    try {
      var response = await fetch('/api/canvas/' + encodeURIComponent(state.canvasId || 'default'));
      if (!response.ok) throw new Error('HTTP ' + response.status);
      var data = await response.json();
      if (data && data.document) {
        // Only apply if the saved document has nodes -- otherwise keep current state
        var hasContent = Array.isArray(data.document.nodes) && data.document.nodes.length > 0;
        if (hasContent) {
          applyDocument(data.document);
          if (!silent) {
            setStatus('Loaded ' + (data.updated_at || ''));
            if (window.showToast) window.showToast('Canvas loaded');
          }
        } else if (!silent) {
          setStatus('No saved canvas found');
          if (window.showToast) window.showToast('No saved canvas — showing demo nodes');
        }
      }
    } catch (error) {
      if (!silent) {
        setStatus('Load failed', true);
        if (window.showToast) window.showToast('Canvas load failed');
      }
    }
  }
```

This way:
- On mount (`loadCanvas(true)`): if a saved canvas exists, it loads; if not, demo nodes stay
- On "Load" button click (`loadCanvas(false)`): if saved canvas exists, it loads with toast; if not, shows "no saved canvas" message
- After user clicks "Save" then "Load", it correctly round-trips

Also remove the commented-out dead code block (lines 218-223) that was left from the merge -- the old `nodesHtml` map function that was replaced.
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM && grep -n "hasContent\|nodes\.length" frontend/static/js/canvas.js | head -5 && echo "Guard check present" && grep -c "// var nodesHtml" frontend/static/js/canvas.js | xargs -I{} test {} -eq 0 && echo "Dead code removed"</automated>
  </verify>
  <done>Load button shows "No saved canvas" when nothing is saved (instead of wiping nodes); auto-load on mount preserves demo nodes; dead merge artifact code removed</done>
</task>

</tasks>

<verification>
1. Route order: In canvas/router.py, the `/subgraph` GET endpoint is defined before `/{canvas_id}` GET endpoint
2. Load behavior: `loadCanvas` checks for non-empty nodes before calling `applyDocument`
3. No merge artifacts: commented-out dead code removed from canvas.js
4. Manual smoke test: Navigate to canvas page, verify demo nodes appear, click Load (should show "no saved canvas"), click Save then Load (should round-trip successfully), click Load Neighbors (should prompt for URI and hit subgraph endpoint)
</verification>

<success_criteria>
- GET /api/canvas/subgraph is not shadowed by GET /api/canvas/{canvas_id}
- Canvas Load button preserves demo nodes when no saved data exists
- Canvas Load button loads saved data when it exists
- No commented-out dead code from merge remains in canvas.js
</success_criteria>

<output>
After completion, create `.planning/quick/32-fix-spatial-canvas-load-button-and-verif/32-SUMMARY.md`
</output>
