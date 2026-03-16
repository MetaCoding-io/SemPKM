---
estimated_steps: 6
estimated_files: 2
---

# T02: User Guide Chapter 27 Update and Glossary

**Slice:** S04 — E2E Tests & User Guide
**Milestone:** M008

## Description

Extend the existing Spatial Canvas user guide (chapter 27) with documentation for the three features shipped in M008: node resizing, property flip, and live embeds. Update the glossary with new terms. All content should match the implemented behavior from S01–S03.

## Steps

1. In `docs/guide/27-spatial-canvas.md`, update the **Node Anatomy** section:
   - Add **Flip** button to the header controls list (between Expand and Delete): "**Flip** -- Toggle between the object's Markdown body and a property table showing SHACL-derived metadata. The button turns accent blue when properties are shown."
   - Add **Resize handles** mention: "Invisible resize handles appear on the right edge, bottom edge, and bottom-right corner when hovering a node. Drag any handle to resize."

2. Add a new section **"Resizing Nodes"** after "Expanding Neighborhoods" (before "Practical Workflows"):
   - Explain corner/edge/bottom resize handles (appear on hover)
   - Grid snapping (24px grid)
   - Minimum size constraints (160px wide, 80px tall)
   - Default width of 260px for un-resized nodes
   - Resized dimensions persist in saved sessions
   - Old sessions load at default size

3. Add a new section **"Property Flip"** after "Resizing Nodes":
   - The flip button in the header (between expand and delete)
   - Click toggles between Markdown body and a compact property table
   - Property table shows type label, property names and values derived from SHACL shapes
   - Multi-value properties shown as pills, booleans as ✓/✗
   - Inferred properties (from SHACL-AF rules) included
   - Flip state persists in saved sessions (re-fetched on reload)
   - Tip callout: "Use property flip to quickly inspect an object's metadata without leaving the canvas."

4. Add a new section **"Live Embeds"** after "Property Flip":
   - Explain the embed concept: live interactive content from other parts of SemPKM rendered inside canvas nodes as iframes
   - Four embed types with a table: View (Table/Cards/Graph), Dashboard, SPARQL Query Result, Object Read View
   - **Adding Embeds — Toolbar Picker**: Click "Embed" in the toolbar → tabbed dropdown (Views / Dashboards / Queries) → click item → embed placed at viewport center
   - **Adding Embeds — Explorer Drag**: Drag a view, dashboard, or saved query from the Explorer sidebar onto the canvas
   - Maximum of 8 simultaneous embeds (performance safety)
   - Embeds are resizable using the same handles as regular nodes
   - Tip callout: "Combine a Table View embed filtered to one type with an Object Read embed to build a mini research dashboard right on your canvas."

5. Update the **"What Gets Saved"** section:
   - Add to the existing bullet list: "Node dimensions (width and height) for resized nodes", "Property flip state (which nodes show the property table)", "Embed configurations (content type, URL, and label)"

6. Update the **"The Toolbar"** table:
   - Add row: **Embed** | Open the embed picker to place a View, Dashboard, or SPARQL result on the canvas

7. Update the **"Canvas vs. Graph View"** comparison table:
   - Add row: **Embeds** | No | Views, dashboards, SPARQL results, and objects as live iframes

8. Add a new practical workflow example **"Building a Research Dashboard on Canvas"**:
   - Place a Table View embed filtered to Notes
   - Place a Graph View embed next to it
   - Add a SPARQL query result showing recent changes
   - Resize each to fit
   - Save as "Research Dashboard"

9. In `docs/guide/appendix-d-glossary.md`, add two entries in alphabetical order:
   - **Embed Node** — A canvas node that displays live content from another part of SemPKM (view, dashboard, SPARQL result, or object) inside an iframe. Embeds are interactive and update in real-time. Maximum 8 per canvas. See [Chapter 27: Spatial Canvas](27-spatial-canvas.md).
   - **Property Flip** — A toggle on spatial canvas object nodes that switches between the Markdown body and a compact property table showing SHACL-derived metadata. See [Chapter 27: Spatial Canvas](27-spatial-canvas.md).
   - "Embed Node" goes after "Edge" / before "Event". "Property Flip" goes after "PKCE" / before "Property".

10. Verify the navigation footer is intact: `**Previous:** [Chapter 26: IndieAuth](26-indieauth.md) | **Next:** [Chapter 28: Dashboards and Workflows](28-dashboards-and-workflows.md)`

## Must-Haves

- [ ] Node Anatomy updated with flip button and resize handles
- [ ] "Resizing Nodes" section with handles, grid snapping, min constraints, default 260px
- [ ] "Property Flip" section with toggle behavior, property table description, persistence
- [ ] "Live Embeds" section with 4 embed types, toolbar picker, explorer drag, max 8
- [ ] "What Gets Saved" updated with dimensions, showProperties, embedConfig
- [ ] Toolbar table updated with Embed button
- [ ] Comparison table updated with embeds row
- [ ] Glossary: "Embed Node" and "Property Flip" entries added alphabetically
- [ ] No references to features that don't exist
- [ ] Navigation chain ch.26 → ch.27 → ch.28 intact

## Observability Impact

This task modifies documentation only — no runtime behavior changes. Future agents verify correctness by:
- Reading `docs/guide/27-spatial-canvas.md` and checking section headings match the feature set from M008
- Checking glossary entries exist and are alphabetically ordered
- The navigation footer chain (ch.26 → ch.27 → ch.28) is the structural health signal

## Verification

- Read through `docs/guide/27-spatial-canvas.md` — all new sections present, formatting consistent
- Check glossary entries are alphabetically placed
- Verify nav footer links
- No broken markdown (tables render, headings consistent)

## Inputs

- `docs/guide/27-spatial-canvas.md` — existing chapter to extend (base canvas features already documented)
- `docs/guide/appendix-d-glossary.md` — existing glossary to add entries to
- S01 summary: Corner/edge/bottom resize handles, grid-snapped, 160px/80px min, 260px default, width/height in getDocument/applyDocument
- S02 summary: Flip button between expand and delete, `.spatial-node-flip`, property table from `/api/canvas/properties`, showProperties serialized, memory-only cache re-fetched on load
- S03 summary: 4 embed types (view, dashboard, SPARQL, object), toolbar "Embed" button with tabbed picker, explorer drag-drop, max 8, dual-layer rendering, embedConfig in document JSON

## Expected Output

- `docs/guide/27-spatial-canvas.md` — extended with ~150-200 new lines (3 feature sections + updates to existing sections)
- `docs/guide/appendix-d-glossary.md` — 2 new entries added
