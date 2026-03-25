# S04: CSS Theme Completion & Utilities

**Goal:** CSS theme variable adoption ≥98% — standalone hex ≤10, standalone rgba ≤20 across all CSS files (excluding theme.css). Breakpoints standardized to 600px/768px. Redundant dark-mode override blocks eliminated where theme tokens provide automatic dark-mode support.
**Demo:** After this: CSS theme variable adoption is ≥98%; shared utility classes reduce workspace.css by ~500 lines; breakpoints are standardized to 600/768

## Must-Haves

- `rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/ --glob '!theme.css' | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l` returns ≤10
- `rg 'rgba?\(' frontend/static/css/ --glob '!theme.css' | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l` returns ≤20
- `rg '@media.*max-width' frontend/static/css/ | grep -v '600\|768'` returns zero results
- Visual spot-check confirms no regressions in light and dark mode on workspace, settings, and import pages

## Proof Level

- This slice proves: operational — visual regression check in browser required to confirm dark-mode correctness after eliminating override blocks

## Integration Closure

Upstream: reads `frontend/static/css/theme.css` for existing token definitions. New wiring: ~30 new primitive and semantic tokens added to theme.css, consumed by all other CSS files via var() and color-mix(). Nothing remains — slice is self-contained within the CSS layer.

## Verification

- None — pure CSS refactoring with no runtime signals, APIs, or error paths.

## Tasks

- [x] **T01: Add theme tokens and migrate workspace.css** `est:2h`
  Define all new theme tokens needed for the full migration (semantic tokens for warning-text, info, success-text; primitive tokens for BMC sections, quadrant sections, OKR status colors, decision-matrix colors). Then migrate all 31 standalone hex and 55 standalone rgba values in workspace.css to use theme variables and color-mix(). Eliminate redundant [data-theme="dark"] blocks (~18 blocks, ~68 lines) where the replacement token already has dark-mode overrides in theme.css. This task establishes the conversion patterns that T02 follows mechanically.
  - Files: `frontend/static/css/theme.css`, `frontend/static/css/workspace.css`
  - Verify: rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/workspace.css | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l  # target: ≤3 (FullCalendar exemptions only live in views.css, workspace should be zero or near-zero)
rg 'rgba?\(' frontend/static/css/workspace.css | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l  # target: ≤5

- [x] **T02: Migrate remaining CSS files and standardize breakpoints** `est:2h`
  Apply the same hex→var() and rgba→color-mix() conversion pattern from T01 across all 12 remaining CSS files: views.css (12 hex, 2 rgba), import.css (11 hex, 8 rgba), vfs-browser.css (9 hex, 1 rgba), copilot.css (3 hex, 5 rgba), federation.css (4 hex, 1 rgba), settings.css (2 hex), okr.css (6 hex, 16 rgba), decision-matrix.css (2 hex, 26 rgba), quadrant.css (24 rgba), bmc.css (61 rgba), style.css (1 rgba), context-indicator.css (1 rgba). For bmc/quadrant/okr/decision-matrix, use the primitive tokens added in T01 with color-mix() for opacity variants. Standardize breakpoints: views.css 640px→600px, style.css 640px→600px (2 occurrences), bmc.css 800px→768px. Eliminate dark-mode override blocks (~94 lines in views.css, ~41 in okr.css, ~44 in decision-matrix.css, ~36 in quadrant.css, ~76 in bmc.css) where replacement tokens provide automatic dark-mode support.
  - Files: `frontend/static/css/views.css`, `frontend/static/css/import.css`, `frontend/static/css/vfs-browser.css`, `frontend/static/css/copilot.css`, `frontend/static/css/federation.css`, `frontend/static/css/settings.css`, `frontend/static/css/okr.css`, `frontend/static/css/decision-matrix.css`, `frontend/static/css/quadrant.css`, `frontend/static/css/bmc.css`, `frontend/static/css/style.css`, `frontend/static/css/context-indicator.css`
  - Verify: rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/ --glob '!theme.css' | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l  # target: ≤10
rg 'rgba?\(' frontend/static/css/ --glob '!theme.css' | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l  # target: ≤20
rg '@media.*max-width' frontend/static/css/ | grep -v '600\|768'  # target: zero results

- [ ] **T03: Verify adoption metrics and visual regression check** `est:30m`
  Run the adoption metric counts to confirm ≤10 standalone hex and ≤20 standalone rgba. Verify breakpoint standardization. Start the Docker dev stack and visually verify light and dark mode on workspace, settings, and import pages — checking that colors render correctly and no regressions are visible. Document any intentional exemptions (e.g., FullCalendar !important overrides) in a brief comment block in theme.css.
  - Files: `frontend/static/css/theme.css`
  - Verify: rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/ --glob '!theme.css' | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l  # must be ≤10
rg 'rgba?\(' frontend/static/css/ --glob '!theme.css' | grep -v '^\s*/\*' | grep -v '\*/' | grep -v 'var(' | grep -v '^\s*\*' | wc -l  # must be ≤20
rg '@media.*max-width' frontend/static/css/ | grep -v '600\|768'  # must be empty

## Files Likely Touched

- frontend/static/css/theme.css
- frontend/static/css/workspace.css
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
