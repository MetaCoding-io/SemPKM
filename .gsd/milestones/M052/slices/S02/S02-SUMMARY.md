---
id: S02
parent: M052
milestone: M052
provides:
  - Polished property table CSS pattern available for S04 form sections
  - Popover property row styling shared between graph popovers and ref-pill tooltips
requires:
  []
affects:
  - S04
key_files:
  - frontend/static/css/workspace.css
  - frontend/static/css/views.css
  - backend/app/templates/browser/object_read.html
key_decisions:
  - Used display:contents :hover for property row highlighting — supported in all modern browsers (Chrome 105+, Firefox 111+, Safari 16.4+)
  - All styling uses existing theme tokens only — zero new CSS custom properties
patterns_established:
  - Property table zebra striping pattern: nth-child(even) with --color-surface-recessed, hover with --color-surface-hover
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M052/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M052/slices/S02/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-06T02:11:18.976Z
blocker_discovered: false
---

# S02: Property Table & Popover Polish

**Added zebra striping, hover highlights, label/value distinction, and description tooltips to object read view property tables; added borders, alternating backgrounds, padding, and border-radius to graph and ref-pill popover property rows.**

## What Happened

Two CSS-focused tasks delivered visual polish to property display surfaces across the workspace.

**T01 — Object read view property table:** Added four enhancements to `.property-row` in workspace.css: (1) zebra striping via `nth-child(even)` with `--color-surface-recessed` background, (2) hover highlight on both label and value cells via `--color-surface-hover`, (3) smooth `transition: background 0.15s ease` on label and value cells, (4) muted value text via `--color-text-muted` to create visual hierarchy. In `object_read.html`, added conditional `title="{{ prop.description }}"` attribute on property labels — properties with `sh:description` in the SHACL shapes now show native browser tooltips on hover.

**T02 — Graph and ref-pill popover property rows:** Modified `.graph-popover-prop` in views.css to add bottom borders (`--color-border-subtle`), alternating-row backgrounds (`--color-surface-recessed`), adjusted padding (parent reduced from 14px to 6px horizontal, child increased from `3px 0` to `4px 8px`), and border-radius on first/last children. Since `ref_tooltip.html` uses the same `.graph-popover-prop` class, both graph node popovers and reference-pill tooltip popovers automatically received the improved styling.

All styling uses existing theme tokens with dark-mode overrides already defined in `theme.css` — no new CSS custom properties were introduced.

## Verification

All four plan-specified verification checks passed:
1. `rg 'nth-child(even)' frontend/static/css/workspace.css` — matched zebra striping rules
2. `rg 'title=.*prop.description' backend/app/templates/browser/object_read.html` — matched tooltip attribute
3. `rg 'graph-popover-prop:nth-child' frontend/static/css/views.css` — matched alternating background rule
4. `rg 'border-bottom.*border-subtle' frontend/static/css/views.css` — matched border rules
Additionally confirmed: all theme tokens (`--color-surface-recessed`, `--color-surface-hover`, `--color-text-muted`, `--color-border-subtle`) have both light and dark mode values in theme.css. Ref-pill tooltip template confirmed to share `.graph-popover-prop` class.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

T02 merged two planned separate `:last-child` rules (border-bottom removal and border-radius) into a single combined rule to avoid duplicate selectors. Minor CSS hygiene improvement, no functional change.

## Known Limitations

None.

## Follow-ups

None.

## Files Created/Modified

- `frontend/static/css/workspace.css` — Added zebra striping, hover highlight, transition, and muted value text to .property-row/.property-label/.property-value
- `frontend/static/css/views.css` — Added borders, alternating backgrounds, padding adjustment, and border-radius to .graph-popover-prop
- `backend/app/templates/browser/object_read.html` — Added conditional title attribute for sh:description tooltip on property labels
