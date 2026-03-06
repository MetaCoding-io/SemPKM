# SemPKM — Claude Coding Guide

Project-specific conventions and hard-won patterns. Follow these to avoid known pitfalls.

---

## Frontend: Lucide Icons in Flex Containers

**Problem:** Lucide SVGs shrink to 0 width when placed inside a `display:flex` button without `flex-shrink: 0`.

Lucide replaces `<i data-lucide="...">` with an `<svg>`. SVG elements are flex items when inside a flex container. Without an explicit `min-width` or `flex-shrink: 0`, the browser can compress their rendered width to 0px even if an inline `style="width:Xpx"` is set — making the icon completely invisible.

**Rule:** Always size Lucide icons via CSS, not inline HTML styles. Add `flex-shrink: 0` when the SVG is a child of a flex container.

```css
/* Good — CSS rule, explicit size, flex-safe */
.my-btn svg {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
    stroke: currentColor;
}
```

```html
<!-- Good — no inline size, CSS handles it -->
<button class="my-btn"><i data-lucide="x"></i></button>

<!-- Bad — inline style gets overridden by flex layout, icon goes invisible -->
<button class="my-btn"><i data-lucide="x" style="width:14px;height:14px;"></i></button>
```

**Affected file:** `frontend/static/css/workspace.css` — `.panel-btn svg` block is the reference implementation.

---

## Frontend: SVG Icon Stroke Inheritance

Lucide SVGs use `stroke` (not `fill`) for rendering. Setting `color` on the parent button is not enough — you must forward it via `stroke: currentColor` on the SVG or its container.

```css
.my-btn {
    color: var(--color-text-muted); /* sets color token */
}
.my-btn svg {
    stroke: currentColor; /* forwards color to SVG strokes */
}
```

---

## Docker Dev Workflow

See memory/MEMORY.md for full details. Short version:

- **No rebuild needed:** Python code, templates, CSS, JS — all hot-reloaded
- **Rebuild needed:** `pyproject.toml` (deps), `migrations/`
- **nginx.conf changes:** `docker compose restart frontend` (no rebuild)

---

## Frontend: CSS 3D Flip Card (Object Read/Edit)

**Problem:** The object view uses a CSS 3D flip card to switch between read and edit modes. `backface-visibility: hidden` is the standard CSS approach but is unreliable -- it has caused content bleed-through bugs 3 times due to browser/GPU rendering differences.

**Rule:** Always use the two-layer defense:
1. `backface-visibility: hidden` on `.object-face` (works during animation)
2. `display: none` via `.face-hidden` class (bulletproof after animation completes)
3. Before starting any flip animation, set `style.display = ''` on the target face
4. Wait for the FULL animation duration (600ms) before toggling face classes -- never use a midpoint timeout

**Affected files:**
- `frontend/static/css/workspace.css` -- `.object-face`, `.face-hidden`, `.face-visible` rules
- `frontend/static/js/workspace.js` -- `toggleObjectMode()` function

**Anti-pattern:** Do NOT rely solely on `backface-visibility: hidden` or `visibility: hidden`. These are CSS hints that browsers can ignore under certain compositing conditions. `display: none` is the only guaranteed way to remove an element from the rendering tree.

---

## Architecture Notes

- htmx drives most DOM updates; avoid full-page JS frameworks
- Workspace custom events: `sempkm:tab-activated` (detail: `{isObjectTab: bool}`), `sempkm:tabs-empty`
- Panel drag-drop: `[data-panel-name]` + `[data-drop-zone]`, positions in localStorage `sempkm_panel_positions`
- RDF label precedence: `dcterms:title > rdfs:label > skos:prefLabel > schema:name > foaf:name > QName`
