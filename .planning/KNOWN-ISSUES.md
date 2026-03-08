# Known Issues & Technical Debt

Persistent issues that have workarounds but deserve revisiting.

---

## KI-001: Object Read/Edit Toggle — 3D Flip Broken Inside Dockview

**Status:** Workaround in place (crossfade)
**Severity:** Cosmetic
**Date identified:** 2026-03-07
**Commits:** d2853fc (crossfade workaround)

### Problem

The object read/edit toggle in the workspace editor was designed as a CSS 3D card flip (`rotateY(180deg)` with `backface-visibility: hidden`). This same pattern works perfectly in the cards grid view. However, inside dockview panels, the back face never hides — both faces remain visible after the flip animation.

### Root Cause (Hypothesis)

Dockview's `.dv-groupview` sets `overflow: hidden`. Per CSS spec, `overflow` values other than `visible` on an ancestor flatten `transform-style: preserve-3d`, breaking the 3D rendering context that `backface-visibility: hidden` depends on.

The cards grid view works because its flip containers have no `overflow: hidden` ancestors in the 3D context chain.

### Why This Needs Revisiting

The user reports that the 3D flip **was working** inside dockview at some point. This suggests either:
1. A dockview CSS update changed the `overflow` behavior
2. The 3D context was preserved through some other mechanism that was later lost
3. The issue is more nuanced than the `overflow: hidden` hypothesis

### Current Workaround

Replaced 3D flip with a 250ms opacity crossfade (`workspace.css` `.object-flip-container` section). The `.flipped` class toggles `opacity` and `pointer-events` on read/edit faces. Works reliably but loses the visual flair of the flip animation.

### Investigation Leads

- Check if dockview's `overflow: hidden` on `.dv-groupview` can be overridden to `overflow: visible` without breaking dockview's layout/drag-drop
- Check git history for when the 3D flip last worked — what CSS changed between then and now
- Test whether adding `transform-style: preserve-3d` to intermediate dockview DOM elements restores the 3D context
- Check if the cards view flip would also break if placed inside a container with `overflow: hidden`

### Affected Files

- `frontend/static/css/workspace.css` — `.object-flip-container` section (crossfade implementation)
- `frontend/static/css/views.css` — `.flip-card` section (working 3D flip reference)
- `frontend/static/js/workspace.js` — `toggleObjectMode()` function
- `CLAUDE.md` — Documents the flip card pattern and anti-patterns

### Related

- Cards grid view 3D flip: `views.css` lines 730-772 (working reference implementation)
- Admin model detail flip: `model_detail.html` `flipCard()` (also uses 3D flip)
