---
estimated_steps: 60
estimated_files: 2
skills_used: []
---

# T01: Add theme tokens and migrate workspace.css

Define all new theme tokens needed for the full CSS migration, then migrate workspace.css — the largest file with 31 standalone hex and 55 standalone rgba values — to use theme variables and color-mix(). Eliminate redundant dark-mode override blocks where the replacement token already has dark-mode overrides in theme.css.

This task is the creative/risky half of the slice: it decides which tokens to create and establishes the conversion patterns that T02 follows mechanically. T01 must leave theme.css with enough tokens to cover every standalone color across all CSS files — not just workspace.css.

## Steps

1. **Read theme.css** to understand existing token structure (light :root block, dark [data-theme="dark"] block, primitives prefixed with `--_color-`).

2. **Add new semantic tokens to theme.css** in both light and dark :root blocks. Tokens needed across ALL files (not just workspace.css):

   **Semantic tokens (light / dark):**
   - `--color-warning-text`: `#d97706` / `#fbbf24` — text on warning backgrounds
   - `--color-error-text`: `#dc2626` / `#fca5a5` — text on error backgrounds (alias to existing or new)
   - `--color-success-text`: `#16a34a` / `#4ade80` — text on success backgrounds
   - `--color-info`: `#3b82f6` / `#60a5fa` — info semantic color
   - `--color-info-text`: `#2563eb` / `#93c5fd` — info text color
   
   **Primitive tokens for decorative per-section colors (used by bmc.css, quadrant.css, okr.css, decision-matrix.css via color-mix):**
   
   BMC sections (8 sections need distinct colors — light / dark):
   - `--_color-bmc-key-partners`: `rgb(70, 130, 180)` / `rgb(100, 160, 210)` (steel blue)
   - `--_color-bmc-key-activities`: `rgb(16, 185, 129)` / `rgb(52, 211, 153)` (emerald)
   - `--_color-bmc-key-resources`: `rgb(20, 184, 166)` / `rgb(45, 212, 191)` (teal)
   - `--_color-bmc-value-prop`: `rgb(59, 130, 246)` / `rgb(96, 165, 250)` (blue)
   - `--_color-bmc-customer-rel`: `rgb(244, 63, 94)` / `rgb(251, 113, 133)` (rose)
   - `--_color-bmc-channels`: `rgb(249, 115, 22)` / `rgb(251, 146, 60)` (orange)
   - `--_color-bmc-customer-seg`: `rgb(168, 85, 247)` / `rgb(192, 132, 252)` (purple)
   - `--_color-bmc-cost-structure`: `rgb(100, 116, 139)` / `rgb(148, 163, 184)` (slate)
   - `--_color-bmc-revenue`: `rgb(234, 179, 8)` / `rgb(250, 204, 21)` (yellow)
   
   Quadrant sections (4 quadrants — these use the existing primitives `--_color-green-500`, `--_color-blue-500`, `--_color-amber-500`, `--_color-red-500` already in theme.css — **may not need new tokens**, verify if existing primitives match the actual rgba values).
   
   OKR status colors (3 tiers): success=green, warning=amber, danger=red — map to existing `--color-success`, `--color-warning`, `--color-error`.
   
   Decision-matrix score colors: similar — green/amber/red scale. Map to existing semantic tokens.
   
   Additional primitives for other files:
   - `--_color-vfs-warning`: `#E8A838` / `#F0C060` — VFS browser warning icon
   - `--_color-vfs-success`: `#27AE60` / `#52D689` — VFS browser success icon
   - `--_color-vfs-error`: `#E74C3C` / `#F08070` — VFS browser error icon
   - `--_color-import-warning`: `#f0ad4e` / `#fbbf24` — import status warning
   - `--_color-import-error`: `#e74c3c` / `#fca5a5` — import status error
   - `--_color-import-info`: `#5bc0de` / `#7dd3fc` — import status info

3. **Audit workspace.css** for all standalone hex values. Run: `rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/workspace.css | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*'` and replace each:
   - `#fff` → `var(--color-surface)` or `var(--color-on-accent)` depending on context (background vs. text-on-color)
   - `#0d9488` / `#5eead4` → `var(--color-accent)` (light) / already handled by dark-mode override in theme.css
   - `#d97706` / `#fbbf24` → `var(--color-warning-text)` (new token)
   - `#dc2626` / `#fca5a5` / `#b91c1c` → `var(--color-error)` or `var(--color-error-text)` (new token)
   - `#10b981` / `#059669` → `var(--color-success)` or `var(--color-success-text)`
   - `#f59e0b` → `var(--color-warning)`
   - `#8b5cf6` / `#7c3aed` → create `--color-purple` primitive or use `--color-primary` if contextually appropriate

4. **Audit workspace.css** for all standalone rgba values. Run: `rg 'rgba?\(' frontend/static/css/workspace.css | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*'` and replace each using the `color-mix()` pattern:
   - `rgba(R, G, B, OPACITY)` → `color-mix(in srgb, var(--token) OPACITY_PCT%, transparent)`
   - `rgba(0, 0, 0, 0.5)` → `var(--color-overlay-heavy)` (existing token)
   - `rgba(0, 0, 0, 0.15)` → `var(--_color-black-shadow-sm)` (existing) or `color-mix(in srgb, var(--color-text) 15%, transparent)`
   - Status badge variants like `rgba(20, 184, 166, 0.08)` → `color-mix(in srgb, var(--color-accent) 8%, transparent)`
   - Status badge variants like `rgba(245, 158, 11, 0.08)` → `color-mix(in srgb, var(--color-warning) 8%, transparent)`

5. **Eliminate redundant dark-mode blocks.** For each `[data-theme="dark"]` block in workspace.css, check if the light-mode rule now uses a theme token that already has a dark-mode override in theme.css. If so, the dark-mode block is fully redundant — delete it. If the dark-mode block adjusts properties OTHER than colors (e.g., box-shadow, opacity, border-width), keep it.

6. **Verify** the workspace.css migration with the standalone hex/rgba counts.

## Must-Haves

- All standalone hex values in workspace.css replaced with var() references
- All standalone rgba values in workspace.css replaced with var() or color-mix() references (allow ≤5 exceptions if truly unmappable)
- Redundant dark-mode override blocks in workspace.css deleted
- theme.css contains ALL tokens needed for T02's migration of remaining files (not just workspace-specific tokens)
- New tokens defined in BOTH light and dark :root blocks in theme.css

## Inputs

- `frontend/static/css/theme.css`
- `frontend/static/css/workspace.css`

## Expected Output

- `frontend/static/css/theme.css`
- `frontend/static/css/workspace.css`

## Verification

rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/workspace.css | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l
# target: 0 standalone hex in workspace.css
rg 'rgba?\(' frontend/static/css/workspace.css | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l
# target: ≤5 standalone rgba in workspace.css
