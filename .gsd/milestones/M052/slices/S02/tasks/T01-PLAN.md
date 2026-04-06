---
estimated_steps: 24
estimated_files: 2
skills_used: []
---

# T01: Property table zebra striping, hover highlight, tooltips

Add CSS polish to the object read view property table and add description tooltips to property labels.

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

## Inputs

- ``frontend/static/css/workspace.css` — existing property table styles at line 3589`
- ``backend/app/templates/browser/object_read.html` — existing property label at line 60`

## Expected Output

- ``frontend/static/css/workspace.css` — added zebra striping, hover highlight, value muting, transition rules`
- ``backend/app/templates/browser/object_read.html` — added title attribute from prop.description on property labels`

## Verification

Start the dev stack and open an object in read mode. Verify: (1) alternating row backgrounds visible, (2) hovering a row highlights both cells, (3) labels are visually stronger than values, (4) hover over a label with sh:description shows tooltip. Toggle dark mode and confirm all styling adapts. Run: `rg 'nth-child(even)' frontend/static/css/workspace.css` returns matches, `rg 'title=.*prop.description' backend/app/templates/browser/object_read.html` returns match.
