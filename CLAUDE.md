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

## Frontend: CSS 3D Card Flip Animation

**Problem:** Card flip animations flash/flicker when JS `setTimeout` is used to swap face visibility at a hardcoded midpoint (e.g. 300ms into a 600ms transition). The timeout races against the CSS animation — if the browser's main thread is even slightly busy, both faces become invisible for a few frames.

**Rule:** Let `backface-visibility: hidden` handle the visual midpoint. Toggle `visibility` with correct sequencing — never with a hardcoded `setTimeout`.

**How CSS 3D flip works:**
1. Two faces are stacked, the back face pre-rotated `rotateY(180deg)`
2. Both faces have `backface-visibility: hidden` — the browser automatically hides whichever face points away from the viewer
3. The parent `.flip-inner` rotates `rotateY(180deg)` via a CSS transition
4. At exactly 90°, the GPU compositor swaps which face is visible — frame-perfect, no JS needed

**The correct JS sequencing pattern:**
```javascript
// Flipping to show the back face:
backFace.classList.add('face-visible');    // visibility:visible BEFORE animation
flipInner.classList.add('flipped');        // start CSS transition
flipInner.addEventListener('transitionend', function handler(e) {
    if (e.propertyName !== 'transform') return;
    flipInner.removeEventListener('transitionend', handler);
    frontFace.classList.add('face-hidden'); // visibility:hidden AFTER animation
});
```

**Why this order matters:**
- Incoming face must be `visibility: visible` **before** the transition starts, so `backface-visibility` can reveal it at 90°. If it's still `visibility: hidden` at the 90° mark, both faces are invisible → black flash.
- Outgoing face gets `visibility: hidden` **after** `transitionend` for accessibility (removes from tab order, screen readers) — not for visual purposes.

**Required CSS properties on every face element:**
```css
.my-face {
    backface-visibility: hidden;
    -webkit-backface-visibility: hidden;  /* Safari */
}
```

**Anti-patterns (do NOT do):**
```javascript
// BAD — hardcoded timeout races against CSS animation
setTimeout(function() {
    frontFace.classList.add('face-hidden');
    backFace.classList.add('face-visible');
}, 300);
```

**Implementations in codebase:**
- Cards grid view: `views.css` (`.flip-card-*`) — pure CSS, simplest, reference pattern
- Object tab editor: `workspace.css` (`.object-face-*`) + `workspace.js` (`toggleObjectMode`)
- Admin model detail: `style.css` (`.type-flip-*`) + `model_detail.html` (`flipCard`)

---

## Docker Dev Workflow

See memory/MEMORY.md for full details. Short version:

- **No rebuild needed:** Python code, templates, CSS, JS — all hot-reloaded
- **Rebuild needed:** `pyproject.toml` (deps), `migrations/`
- **nginx.conf changes:** `docker compose restart frontend` (no rebuild)

---

## Architecture Notes

- htmx drives most DOM updates; avoid full-page JS frameworks
- Workspace custom events: `sempkm:tab-activated` (detail: `{isObjectTab: bool}`), `sempkm:tabs-empty`
- Panel drag-drop: `[data-panel-name]` + `[data-drop-zone]`, positions in localStorage `sempkm_panel_positions`
- RDF label precedence: `dcterms:title > rdfs:label > skos:prefLabel > schema:name > foaf:name > QName`
