---
id: T02
parent: S02
milestone: M052
key_files:
  - frontend/static/css/views.css
key_decisions:
  - Merged :last-child border-bottom and border-radius into a single rule to avoid duplicate selectors
duration: 
verification_result: passed
completed_at: 2026-04-06T02:10:10.662Z
blocker_discovered: false
---

# T02: Added bottom borders, alternating-row backgrounds, padding, and border-radius to graph and ref-pill popover property rows in views.css

**Added bottom borders, alternating-row backgrounds, padding, and border-radius to graph and ref-pill popover property rows in views.css**

## What Happened

Modified .graph-popover-props and .graph-popover-prop rules in views.css. Reduced parent horizontal padding from 14px to 6px and increased child padding from 3px 0 to 4px 8px so alternating background bands extend to popover edges. Added border-bottom with last-child exemption, nth-child(even) alternating background using --color-surface-recessed, and border-radius on first/last children. Both tokens have dark-mode overrides. The ref-pill tooltip template shares the same classes so gets the styling automatically.

## Verification

Ran grep checks: (1) rg graph-popover-prop:nth-child views.css — matched, (2) rg border-bottom.*border-subtle views.css — matched, (3) confirmed ref_tooltip.html uses same classes, (4) confirmed both theme tokens have light and dark mode values in theme.css.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg 'graph-popover-prop:nth-child' frontend/static/css/views.css` | 0 | ✅ pass | 50ms |
| 2 | `rg 'border-bottom.*border-subtle' frontend/static/css/views.css` | 0 | ✅ pass | 50ms |
| 3 | `rg 'graph-popover-prop' backend/app/templates/ -g '*.html' -l` | 0 | ✅ pass | 50ms |
| 4 | `rg 'color-border-subtle|color-surface-recessed' frontend/static/css/theme.css` | 0 | ✅ pass | 50ms |

## Deviations

Merged two separate :last-child rules into one combined rule to avoid duplicate selectors.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/css/views.css`
