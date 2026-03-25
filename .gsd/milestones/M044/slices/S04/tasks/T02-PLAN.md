---
estimated_steps: 53
estimated_files: 12
skills_used: []
---

# T02: Migrate remaining CSS files and standardize breakpoints

Apply the same hex→var() and rgba→color-mix() conversion pattern from T01 across all 12 remaining CSS files. Use the primitive tokens added to theme.css in T01 with color-mix() for opacity variants in decorative files (bmc.css, quadrant.css, okr.css, decision-matrix.css). Standardize all non-standard breakpoints to 600px or 768px. Eliminate dark-mode override blocks where the replacement token provides automatic dark-mode support.

## Steps

1. **Read theme.css** to confirm T01 added all expected tokens. This is the token palette you'll use for all replacements.

2. **Migrate views.css** (12 hex, 2 rgba, 29 dark-mode blocks):
   - FullCalendar event colors (`#10b981`, `#059669`, `#8b5cf6`, `#7c3aed`) → use `var(--color-success)`, `var(--color-success-text)`, and new purple token. Keep `!important` — required to override FC inline styles.
   - `#fff` (3×) → `var(--color-surface)` or `var(--color-on-accent)` depending on context.
   - Standardize breakpoint: `@media (max-width: 640px)` → `@media (max-width: 600px)`.
   - Evaluate dark-mode blocks — delete those made redundant by theme token adoption.

3. **Migrate import.css** (11 hex, 8 rgba):
   - Status colors: `#f0ad4e` → `var(--_color-import-warning)`, `#e74c3c` → `var(--_color-import-error)`, `#5bc0de` → `var(--_color-import-info)`.
   - Darker variants: `#c87f0a` → `color-mix(in srgb, var(--_color-import-warning) 80%, black)`, `#c0392b` → `var(--color-danger)`.
   - `#fff` (3×) → `var(--color-surface)` or `var(--color-on-accent)`.
   - rgba values → `color-mix()` with the corresponding primitive tokens.

4. **Migrate vfs-browser.css** (9 hex, 1 rgba):
   - `#E8A838` → `var(--_color-vfs-warning)`, `#27AE60` → `var(--_color-vfs-success)`, `#E74C3C` → `var(--_color-vfs-error)`.
   - `#fff` (4×) → `var(--color-surface)` or `var(--color-on-accent)`.

5. **Migrate copilot.css** (3 hex, 5 rgba):
   - `#fff` (3×) → `var(--color-surface)`.
   - rgba values → `color-mix()` or existing overlay tokens.

6. **Migrate federation.css** (4 hex, 1 rgba):
   - `#fff` (4×) → `var(--color-surface)` or `var(--color-on-accent)`.
   - 1 rgba → `color-mix()`.

7. **Migrate settings.css** (2 hex):
   - `#fff` (2×) → `var(--color-surface)`.

8. **Migrate okr.css** (6 hex, 16 rgba, 12 dark-mode blocks):
   - Progress bar colors: `#22c55e`/`#16a34a` → `var(--color-success)`/`var(--color-success-text)`, `#f59e0b`/`#d97706` → `var(--color-warning)`/`var(--color-warning-text)`, `#ef4444`/`#dc2626` → `var(--color-error)`/`var(--color-error-text)`.
   - 16 rgba → `color-mix()` with corresponding semantic tokens.
   - Evaluate dark-mode blocks for elimination.

9. **Migrate decision-matrix.css** (2 hex, 26 rgba, 14 dark-mode blocks):
   - `#16a34a`/`#4ade80` → `var(--color-success-text)` light/dark.
   - 26 rgba → `color-mix()` with semantic tokens (success/warning/error scale).
   - Evaluate dark-mode blocks for elimination.

10. **Migrate quadrant.css** (0 hex, 24 rgba, 10 dark-mode blocks):
    - 4 quadrant sections use existing primitives `--_color-green-500`, `--_color-blue-500`, `--_color-amber-500`, `--_color-red-500`.
    - Convert `rgba(R,G,B,0.07)` → `color-mix(in srgb, var(--_color-X-500) 7%, transparent)`.
    - Evaluate dark-mode blocks for elimination.

11. **Migrate bmc.css** (0 hex, 61 rgba, 22 dark-mode blocks):
    - 9 BMC sections use the new `--_color-bmc-*` primitives from theme.css.
    - Convert all `rgba(R,G,B,OPACITY)` → `color-mix(in srgb, var(--_color-bmc-X) OPACITY_PCT%, transparent)`.
    - Standardize breakpoint: `@media (max-width: 800px)` → `@media (max-width: 768px)`.
    - Evaluate dark-mode blocks for elimination.

12. **Migrate style.css** (0 hex, 1 rgba, 2 breakpoint fixes):
    - 1 rgba → `color-mix()` or existing token.
    - Standardize breakpoints: 2× `@media (max-width: 640px)` → `@media (max-width: 600px)`.

13. **Migrate context-indicator.css** (0 hex, 1 rgba):
    - 1 rgba → `color-mix()` or existing token.

14. **Run verification counts** across all files to confirm target is met.

## Must-Haves

- All 12 remaining CSS files migrated to use theme variables and color-mix()
- Total standalone hex across all non-theme.css files ≤10
- Total standalone rgba across all non-theme.css files ≤20
- All breakpoints standardized to 600px or 768px (zero non-standard breakpoints)
- Dark-mode override blocks eliminated where replacement tokens provide automatic dark mode

## Inputs

- `frontend/static/css/theme.css`
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

## Expected Output

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

## Verification

rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/ --glob '!theme.css' | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l  # target: ≤10
rg 'rgba?\(' frontend/static/css/ --glob '!theme.css' | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l  # target: ≤20
rg '@media.*max-width' frontend/static/css/ | grep -v '600\|768'  # target: zero results
