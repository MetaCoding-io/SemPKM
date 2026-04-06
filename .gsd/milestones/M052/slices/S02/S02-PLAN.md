# S02: Property Table & Popover Polish

**Goal:** Object read view property table has zebra-striped rows, hover highlight, label/value distinction, and description tooltips. Graph and ref-pill popovers show property rows with borders and alternating backgrounds.
**Demo:** After this: Object read view has zebra-striped property rows with hover highlight, stronger label/value distinction, and tooltips. Graph popover properties have borders and alternating backgrounds.

## Tasks
- [x] **T01: Added zebra striping, hover highlight, muted value text, and description tooltips to object read view property table** — Add CSS polish to the object read view property table and add description tooltips to property labels.

## Steps

1. Read `frontend/static/css/workspace.css` around line 3589 (the `.property-table` block) and `backend/app/templates/browser/object_read.html` around line 60.

2. In `workspace.css`, after the existing `.property-row:last-child` rule (around line 3622), add:
   - **Zebra striping:** `.property-row:nth-child(even) .property-label` and `.property-row:nth-child(even) .property-value` with `background: var(--color-surface-recessed)`. The even-row label override is needed because `.property-label` defaults to `--color-surface-raised`.
   - **Hover highlight:** `.property-row:hover .property-label, .property-row:hover .property-value` with `background: var(--color-surface-hover)`. This works despite `display: contents` — `:hover` still fires on `display: contents` elements in modern browsers (Chrome 105+, Firefox 111+, Safari 16.4+).
   - **Value text distinction:** Change `.property-value` color from `var(--color-text)` to `var(--color-text-muted)` to create visual hierarchy between labels (bold, full color) and values (muted).
   - Add `transition: background 0.15s ease` to `.property-label` and `.property-value` for smooth hover effect.

3. In `object_read.html`, on line 60, change:
   ```html
   <div class="property-label">{{ prop.name }}</div>
   ```
   to:
   ```html
   <div class="property-label"{% if prop.description %} title="{{ prop.description }}"{% endif %}>{{ prop.name }}</div>
   ```
   This adds native browser tooltips to property labels that have `sh:description` in the SHACL shapes. Inferred/extra properties (lines 104+) don't have a `description` field and are left unchanged.

## Must-Haves

- [ ] Zebra striping alternates row backgrounds
- [ ] Hover highlights both label and value cells with smooth transition
- [ ] Values use muted text color for label/value distinction
- [ ] Property labels with sh:description show tooltip on hover
- [ ] All styling uses existing theme tokens — no new CSS custom properties
- [ ] Dark mode works correctly (tokens have overrides in theme.css)
  - Estimate: 20m
  - Files: frontend/static/css/workspace.css, backend/app/templates/browser/object_read.html
  - Verify: Start the dev stack and open an object in read mode. Verify: (1) alternating row backgrounds visible, (2) hovering a row highlights both cells, (3) labels are visually stronger than values, (4) hover over a label with sh:description shows tooltip. Toggle dark mode and confirm all styling adapts. Run: `rg 'nth-child(even)' frontend/static/css/workspace.css` returns matches, `rg 'title=.*prop.description' backend/app/templates/browser/object_read.html` returns match.
- [x] **T02: Added bottom borders, alternating-row backgrounds, padding, and border-radius to graph and ref-pill popover property rows in views.css** — Add visual polish to the property rows in graph node popovers and reference-pill tooltip popovers.

## Steps

1. Read `frontend/static/css/views.css` around line 666 (the `.graph-popover-props` and `.graph-popover-prop` blocks).

2. In `views.css`, modify the existing `.graph-popover-prop` rule and add new rules after it:
   - **Bottom borders:** Add `border-bottom: 1px solid var(--color-border-subtle)` to `.graph-popover-prop`.
   - **Remove last border:** Add `.graph-popover-prop:last-child { border-bottom: none; }`.
   - **Alternating backgrounds:** Add `.graph-popover-prop:nth-child(even) { background: var(--color-surface-recessed); }`.
   - **Horizontal padding:** Change padding from `3px 0` to `4px 8px` — the parent `.graph-popover-props` has `padding: 6px 14px` but children need their own horizontal padding for the alternating background to look right (otherwise the colored bands don't reach the edges). Reduce parent horizontal padding to compensate: change `.graph-popover-props` padding from `6px 14px 10px` to `6px 6px 10px`.
   - **Border radius on first/last for contained look:** Add `border-radius: 3px` to `.graph-popover-prop:first-child` and `.graph-popover-prop:last-child` for subtle rounding on the alternating band edges.

3. These same `.graph-popover-prop` classes are used by `ref_tooltip.html` (ref-pill hover popovers), so the styling improvements apply to both graph popovers and ref-pill popovers automatically.

## Must-Haves

- [ ] Graph popover property rows have subtle bottom borders
- [ ] Last property row has no bottom border
- [ ] Even-numbered rows have alternating background
- [ ] Ref-pill tooltip popovers also show the improved styling (shared classes)
- [ ] Dark mode works correctly (--color-border-subtle and --color-surface-recessed have overrides)
  - Estimate: 15m
  - Files: frontend/static/css/views.css
  - Verify: Start the dev stack, open graph view, hover a node to trigger popover — verify property rows have borders and alternating backgrounds. Open an object in read view, hover a ref-pill to trigger tooltip — verify same styling. Toggle dark mode and confirm adaptation. Run: `rg 'graph-popover-prop:nth-child' frontend/static/css/views.css` returns match, `rg 'border-bottom.*border-subtle' frontend/static/css/views.css` returns match.
