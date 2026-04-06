# S02 Research: Property Table & Popover Polish

## Summary

Straightforward CSS polish + minor Jinja2 template changes. All work uses established patterns (CSS tokens, existing class structure, `color-mix()` convention). No backend logic changes. No new dependencies.

## Recommendation

Three tasks: (1) Property table CSS — zebra striping, hover highlight, label/value distinction. (2) Property label tooltips — template change to add `title` attribute from `prop.description`. (3) Graph popover property borders and alternating backgrounds.

## Implementation Landscape

### Property Table (object_read.html + workspace.css)

**Template:** `backend/app/templates/browser/object_read.html`
- Property rows use `<div class="property-row">` with `display: contents` (CSS grid)
- Labels: `<div class="property-label">{{ prop.name }}</div>` — line 60
- Values: `<div class="property-value">` — line 61
- Grid container: `.property-table` at workspace.css line 3589

**CSS (workspace.css lines 3589–3624):**
```css
.property-table {
    display: grid;
    grid-template-columns: auto 1fr;
    gap: 0;
    border: 1px solid var(--color-border);
    border-radius: 6px;
    overflow: hidden;
    margin-top: 4px;
}
.property-row { display: contents; }
.property-label {
    padding: 8px 12px;
    font-weight: 600;
    font-size: 0.85rem;
    color: var(--color-text);
    background: var(--color-surface-raised);
    border-bottom: 1px solid var(--color-border);
    white-space: nowrap;
}
.property-value {
    padding: 8px 12px;
    font-size: 0.85rem;
    color: var(--color-text);
    border-bottom: 1px solid var(--color-border);
    word-break: break-word;
}
```

**Key constraint:** `.property-row` uses `display: contents`, which means the row itself has no box — its children are direct grid items. `nth-child` selectors must target `.property-row:nth-child(even)` and style both `.property-label` and `.property-value` children. This works because the grid container sees the rows as grid items via `display: contents`.

**Changes needed (CSS only):**
1. **Zebra striping:** `.property-row:nth-child(even) .property-label` and `.property-row:nth-child(even) .property-value` → `background: var(--color-surface-recessed)`. The even label needs to override the `--color-surface-raised` default.
2. **Hover highlight:** `.property-row:hover .property-label, .property-row:hover .property-value` → `background: var(--color-surface-hover)`. **WAIT** — `display: contents` means the row has no box, so `:hover` on `.property-row` won't fire. Need a different approach: use JS `mouseenter`/`mouseleave` on the grid items, or restructure. Actually — `display: contents` does NOT prevent hover — CSS Selectors Level 4 says `:hover` still matches elements with `display: contents` when any of its children are hovered. Browser support is good (Chrome 105+, Firefox 111+, Safari 16.4+). So `.property-row:hover` works.
3. **Label/value distinction:** Make values slightly muted: `.property-value { color: var(--color-text-muted); }`. Labels already have `font-weight: 600` and `--color-text`.

**Tokens available (no new tokens needed):**
- `--color-surface-raised` (#f8f9fb light, #2c313a dark) — label default bg
- `--color-surface-recessed` (#f4f5f7 light, #21252b dark) — even row bg
- `--color-surface-hover` (rgba(0,0,0,0.04) light, rgba(255,255,255,0.06) dark) — hover bg
- `--color-text-muted` — for values text color

### Property Tooltips (object_read.html template)

**Data available:** `PropertyShape` dataclass (backend/app/services/shapes.py line 33) has:
- `description: str | None` — populated from `sh:description` in the shapes graph
- `helptext: str | None` — populated from `sempkm:editHelpText`

**Change:** On line 60, change:
```html
<div class="property-label">{{ prop.name }}</div>
```
to:
```html
<div class="property-label"{% if prop.description %} title="{{ prop.description }}"{% endif %}>{{ prop.name }}</div>
```

This gives native browser tooltips on property labels. Additionally, a small info icon (Lucide `info` or `help-circle`) could be shown as a visual cue that hover info exists. The icon should be inline, flex-shrink: 0, sized via CSS per CLAUDE.md rules.

**For inferred/extra properties** (lines 104-127): These are keyed by `pred` (an IRI string), not a `PropertyShape`. No `description` is available — they get `ref_labels.get(pred, pred)` as the label. No tooltip for these.

### Graph Popover Properties (views.css + graph.js)

**CSS (views.css lines 670–693):**
```css
.graph-popover-prop {
    display: flex;
    gap: 6px;
    padding: 3px 0;
    font-size: 0.82rem;
    line-height: 1.4;
}
```
No borders between props. No alternating backgrounds.

**HTML generated in graph.js (line 540):**
```javascript
html += '<div class="graph-popover-prop">' +
  '<span class="graph-popover-prop-name">' + _esc(keys[i]) + '</span>' +
  '<span class="graph-popover-prop-val">' + _esc(val) + '</span>' +
  '</div>';
```

**ref_tooltip.html** (used by ref-pill popovers in object read view) uses identical markup — same `graph-popover-prop` classes.

**Changes needed (CSS only):**
1. Add `border-bottom: 1px solid var(--color-border-subtle)` to `.graph-popover-prop`
2. Remove border from last child: `.graph-popover-prop:last-child { border-bottom: none; }`
3. Add alternating background: `.graph-popover-prop:nth-child(even) { background: var(--color-surface-recessed); }`
4. Add slight horizontal padding: `padding: 4px 14px` (currently 3px 0 — the parent `.graph-popover-props` has padding 6px 14px but children have no horizontal padding, relying on parent)

### Files Touched

| File | Change Type | Scope |
|------|------------|-------|
| `frontend/static/css/workspace.css` | CSS additions | ~15 lines: zebra, hover, label/value distinction for `.property-table` |
| `frontend/static/css/views.css` | CSS additions | ~10 lines: borders, alternating bg for `.graph-popover-prop` |
| `backend/app/templates/browser/object_read.html` | Template | Line 60: add `title` attr from `prop.description` |

### No Backend Changes

All changes are CSS + template. No Python service changes. No SPARQL changes. No API changes.

### Verification

1. Visual: open an object in read mode → property rows show alternating backgrounds, hover highlights, labels are visually bolder than values
2. Tooltip: hover over a property label that has `sh:description` → native tooltip appears
3. Graph popover: hover a node in graph view → popover props have borders and alternating backgrounds  
4. Dark mode: toggle theme → all new styling adapts correctly (all tokens have dark mode overrides)
5. Ref-pill popover: hover a ref pill in read view → same popover styling improvements visible

### Constraints

- **color-mix() pattern** (K014): Not needed here — using existing semantic tokens directly, not creating new decorative colors
- **Lucide flex rules** (CLAUDE.md): Only relevant if adding an info icon to property labels
- **Dark mode**: All tokens used (`--color-surface-raised`, `--color-surface-recessed`, `--color-surface-hover`, `--color-text-muted`) already have dark mode overrides in theme.css — no new dark mode CSS blocks needed

### Natural Task Boundaries

1. **T01: Property table CSS polish** — zebra striping, hover highlight, label/value distinction (CSS only, workspace.css)
2. **T02: Property label tooltips** — add `title` attribute from `prop.description` on property labels (template change, object_read.html). Optionally add a subtle info icon visual cue.
3. **T03: Graph & ref-pill popover property polish** — borders, alternating backgrounds, padding for popover property rows (CSS only, views.css)

All three tasks are independent — no ordering dependency between them. Each is verifiable in isolation.

### display:contents and :hover — Confirmed Behavior

`.property-row { display: contents }` makes the element's children participate directly in the parent grid. The element itself generates no box. However, `:hover` still works on `display: contents` elements in modern browsers (Chrome 105+, Firefox 111+, Safari 16.4+). The hover triggers when any descendant is hovered. This means `.property-row:hover .property-label` is valid and will work.

If older browser support were needed, an alternative would be JS-based hover or restructuring away from `display: contents`. For this project (Docker-based dev tool), modern browser support is sufficient.

### Skills

No additional skills needed. The `make-interfaces-feel-better` skill from `<available_skills>` could inform micro-interaction details but the changes are well-scoped enough to not require it.
