---
id: T01
parent: S04
milestone: M044
key_files:
  - frontend/static/css/theme.css
  - frontend/static/css/workspace.css
key_decisions:
  - Added --color-danger-hover as a semantic token (not just using color-mix on --color-danger) because the hover state for danger buttons needs a specific darker shade
  - Used color-mix(in srgb, ...) consistently for all transparent color variants rather than mixing approaches
  - Eliminated ~8 dark-mode override blocks that became redundant once semantic tokens with automatic dark-mode switching were adopted
duration: ""
verification_result: passed
completed_at: 2026-03-25T20:38:20.691Z
blocker_discovered: false
---

# T01: Add 45+ theme tokens and migrate workspace.css to 0 standalone hex / 0 standalone rgba

**Add 45+ theme tokens and migrate workspace.css to 0 standalone hex / 0 standalone rgba**

## What Happened

Migrated all 31 standalone hex values and all 55 standalone rgba values in workspace.css to use theme tokens and color-mix() expressions. Added 45+ new tokens to theme.css across both light and dark blocks:

**New semantic tokens:** `--color-success-text`, `--color-error-text`, `--color-warning-text`, `--color-info`, `--color-info-text`, `--color-danger-hover`, `--color-accent-text-dark`

**New primitive tokens:** `--_color-emerald-500`, `--_color-amber-400`, `--_color-violet-500`, `--_color-orange-600` (model badges); `--_color-canvas-grid`, `--_color-canvas-select`, `--_color-canvas-drop`, `--_color-spatial-link` (canvas/spatial); `--_color-form-success`, `--_color-form-error` (form results); 9 BMC section colors (`--_color-bmc-*`); 6 VFS/import status colors (`--_color-vfs-*`, `--_color-import-*`)

**Migration patterns used:**
- Direct token substitution: `#0d9488` → `var(--color-accent)`, `#fff` → `var(--color-on-accent)`, `#b91c1c` → `var(--color-danger-hover)`
- color-mix() for transparent variants: `rgba(20, 184, 166, 0.1)` → `color-mix(in srgb, var(--color-accent) 10%, transparent)`
- Shadow tokens: `0 4px 12px rgba(0,0,0,0.15)` → `var(--shadow-elevated)`
- Overlay tokens: `rgba(0,0,0,0.5)` → `var(--color-overlay-heavy)`

**Eliminated dark-mode override blocks:**
- `[data-theme="dark"] .mirrored-badge` — accent token auto-switches
- All `[data-theme="dark"] .sparql-mirror-btn*` blocks (5 blocks) — semantic color/warning/error tokens auto-switch
- `[data-theme="dark"] .sparql-service-info .endpoint-allowed` — accent-subtle token auto-switches
- `[data-theme="dark"] .sparql-service-info .endpoint-blocked` — warning token auto-switches

Total: ~8 dark-mode blocks eliminated. The remaining dark-mode blocks in workspace.css serve non-color purposes (spatial layout backgrounds, editor-empty pseudo-elements) or reference tokens that need per-component overrides.

All tokens needed for T02's migration of remaining CSS files (bmc.css, quadrant.css, okr.css, decision-matrix.css, vfs-browser.css, import.css, copilot.css, views.css, settings.css, federation.css) are now defined in theme.css.

## Verification

Ran the exact verification commands from the task plan. Both returned 0, exceeding targets (0 hex target met, ≤5 rgba target beaten with 0).

Also verified:
- theme.css braces balanced (35/35)
- workspace.css braces balanced (1350/1350)
- All new tokens appear in both light and dark :root blocks
- All var() references to new tokens have corresponding definitions
- T02-required tokens confirmed present for all 10 remaining CSS files

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/workspace.css | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l` | 0 | ✅ pass — 0 standalone hex (target: 0) | 450ms |
| 2 | `rg 'rgba?\(' frontend/static/css/workspace.css | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l` | 0 | ✅ pass — 0 standalone rgba (target: ≤5) | 450ms |


## Deviations

None. The plan's token suggestions were followed closely, with minor additions (--color-accent-text-dark for the 5eead4 dark teal alias, --_color-form-success/error for form-group colors that didn't map cleanly to existing success/error tokens).

## Known Issues

None.

## Files Created/Modified

- `frontend/static/css/theme.css`
- `frontend/static/css/workspace.css`
