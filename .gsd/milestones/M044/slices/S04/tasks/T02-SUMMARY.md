---
id: T02
parent: S04
milestone: M044
key_files:
  - frontend/static/css/views.css
  - frontend/static/css/import.css
  - frontend/static/css/vfs-browser.css
  - frontend/static/css/copilot.css
  - frontend/static/css/federation.css
  - frontend/static/css/settings.css
  - frontend/static/css/okr.css
  - frontend/static/css/decision-matrix.css
  - frontend/static/css/quadrant.css
  - frontend/static/css/bmc.css
  - frontend/static/css/style.css
  - frontend/static/css/context-indicator.css
key_decisions:
  - Eliminated 58 dark-mode override blocks (okr/dm/quadrant/bmc) since color-mix() with theme primitive vars auto-adapts to both themes
  - Used color-mix(in srgb, var(--_color-*) PCT%, transparent) pattern consistently for all decorative tints — produces identical visual results to the original rgba values
  - Left #cd7f32 bronze medal hex as standalone since no semantic token exists for it — decorative one-off
  - Standardized breakpoints: 640px→600px (views, style), 800px→768px (bmc)
duration: ""
verification_result: passed
completed_at: 2026-03-25T20:54:51.211Z
blocker_discovered: false
---

# T02: Migrate 12 remaining CSS files to theme variables and color-mix(), standardize breakpoints, eliminate 58 dark-mode override blocks

**Migrate 12 remaining CSS files to theme variables and color-mix(), standardize breakpoints, eliminate 58 dark-mode override blocks**

## What Happened

Migrated all 12 remaining CSS files from standalone hex/rgba values to theme tokens and color-mix() expressions:

**Simple files (hex→var only):**
- settings.css: 2 `#fff` → `var(--color-on-accent)`
- federation.css: 4 `#fff` → `var(--color-on-accent)`, 1 rgba → `var(--shadow-elevated)`
- copilot.css: 3 `#fff` → `var(--color-on-accent)`, 5 rgba → `color-mix()` or shadow tokens
- vfs-browser.css: 9 hex → VFS primitive tokens + `var(--color-on-accent)`, 1 rgba → `var(--shadow-elevated)`

**FullCalendar colors (views.css):**
- 12 hex → `var(--_color-emerald-500)`, `var(--_color-violet-500)`, `var(--color-on-accent)` etc.
- FC event type colors use `!important` as before — required to override FC inline styles
- 2 rgba → `color-mix()` expressions
- Breakpoint 640px → 600px

**Import wizard (import.css):**
- 11 hex → import primitive tokens + semantic tokens
- 8 rgba → `color-mix()` expressions with primary/import tokens

**Decorative view files with heavy rgba usage:**
- okr.css: 6 hex → `var(--color-success-text)` etc., 16 rgba → `color-mix()`, 12 dark-mode blocks eliminated
- decision-matrix.css: 2 hex → `var(--color-success-text)`, 26 rgba → `color-mix()`, 14 dark-mode blocks eliminated
- quadrant.css: 24 rgba → `color-mix(in srgb, var(--_color-green-500) 7%, transparent)` etc., 10 dark-mode blocks eliminated
- bmc.css: 61 rgba → `color-mix(in srgb, var(--_color-bmc-*) PCT%, transparent)`, 22 dark-mode blocks eliminated, breakpoint 800px → 768px

**Other files:**
- style.css: 1 rgba → `color-mix()`, 2 breakpoints 640px → 600px
- context-indicator.css: 1 rgba → `var(--shadow-elevated)`

Total dark-mode blocks eliminated: 58 (12 okr + 14 dm + 10 quadrant + 22 bmc). These are now unnecessary because `color-mix()` with theme primitive vars produces correct values in both themes automatically — the primitives are overridden in the dark-mode section of theme.css.

## Verification

Ran all three verification commands from the task plan:
1. Standalone hex count: 1 (target ≤10) — the sole remaining hex is `#cd7f32` (bronze medal color in decision-matrix.css), a decorative one-off with no semantic equivalent
2. Standalone rgba count: 0 (target ≤20) — all rgba values converted to color-mix() or existing shadow/overlay tokens
3. Non-standard breakpoints: 0 — all 640px→600px, 800px→768px standardized
4. CSS syntax validation: all 12 files have balanced braces and balanced parentheses in color-mix calls

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/ --glob '!theme.css' | grep -v var( | wc -l` | 0 | ✅ pass (1 ≤ 10) | 5ms |
| 2 | `rg 'rgba?\(' frontend/static/css/ --glob '!theme.css' | grep -v var( | wc -l` | 0 | ✅ pass (0 ≤ 20) | 5ms |
| 3 | `rg '@media.*max-width' frontend/static/css/ | grep -v '600|768'` | 1 | ✅ pass (zero non-standard breakpoints) | 6ms |


## Deviations

The bronze medal color #cd7f32 in decision-matrix.css was left as a standalone hex inside a color-mix() expression since there's no semantic token for 'bronze'. This is well within the ≤10 target and is a legitimate one-off decorative color.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/css/views.css`
- `frontend/static/css/import.css`
- `frontend/static/css/vfs-browser.css`
- `frontend/static/css/copilot.css`
- `frontend/static/css/federation.css`
- `frontend/static/css/settings.css`
- `frontend/static/css/okr.css`
- `frontend/static/css/decision-matrix.css`
- `frontend/static/css/quadrant.css`
- `frontend/static/css/bmc.css`
- `frontend/static/css/style.css`
- `frontend/static/css/context-indicator.css`
