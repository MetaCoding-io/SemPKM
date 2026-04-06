---
estimated_steps: 16
estimated_files: 1
skills_used: []
---

# T02: Graph and ref-pill popover property borders and alternating backgrounds

Add visual polish to the property rows in graph node popovers and reference-pill tooltip popovers.

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

## Inputs

- ``frontend/static/css/views.css` — existing graph popover property styles at line 666`

## Expected Output

- ``frontend/static/css/views.css` — added borders, alternating backgrounds, padding adjustments for popover property rows`

## Verification

Start the dev stack, open graph view, hover a node to trigger popover — verify property rows have borders and alternating backgrounds. Open an object in read view, hover a ref-pill to trigger tooltip — verify same styling. Toggle dark mode and confirm adaptation. Run: `rg 'graph-popover-prop:nth-child' frontend/static/css/views.css` returns match, `rg 'border-bottom.*border-subtle' frontend/static/css/views.css` returns match.
