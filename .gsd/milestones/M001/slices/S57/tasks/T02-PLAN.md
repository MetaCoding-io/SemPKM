# T02: 57-spatial-canvas 02

**Slice:** S57 — **Milestone:** M001

## Description

Wiki-link edge rendering with distinct styling and ghost nodes for unresolved targets.

Purpose: Parse `[[wiki-link]]` syntax in node markdown bodies and render them as visually distinct edges (dashed green) on the canvas. When a wiki-link target is not on the canvas, show a ghost node stub that can be clicked to add the full node.
Output: Modified canvas.js with wiki-link pre-processing and ghost node logic, new backend endpoint for title-to-IRI resolution, CSS for dashed green edges and ghost node styling.

## Must-Haves

- [ ] "Wiki-links in node markdown bodies are parsed and rendered as edges on the canvas"
- [ ] "Wiki-link edges have dashed green stroke, visually distinct from solid blue RDF edges"
- [ ] "Wiki-link edge labels show the display text from [[display text]], not generic 'link'"
- [ ] "Ghost nodes appear for wiki-link targets not yet on the canvas"
- [ ] "Clicking a ghost node adds the full node card to the canvas at that position"

## Files

- `frontend/static/js/canvas.js`
- `frontend/static/css/workspace.css`
- `backend/app/canvas/router.py`
- `backend/app/canvas/schemas.py`
