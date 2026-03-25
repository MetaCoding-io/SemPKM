# S04 Research: CSS Theme Completion & Utilities

## Summary

Targeted research — known CSS patterns, established `color-mix()` approach in codebase, clear audit data from M041. The work is mechanical: replace standalone hex/rgba with theme variables, add missing theme tokens, standardize breakpoints, and optionally add utility classes.

## Current State (Measured)

| Metric | Value |
|--------|-------|
| `var(--*)` uses | 2,517 |
| Standalone hex (excl. theme.css) | 81 |
| Standalone rgba (excl. theme.css) | 201 |
| Current adoption | **89.9%** (2517 / 2799) |
| Target | **≥98%** (≤10 hex, ≤20 rgba) |

### Standalone Hex by File

| File | Count | Main offenders |
|------|-------|---------------|
| workspace.css | 32 | `#fff` (6×), `#0d9488`/`#5eead4` (accent light/dark, 8×), `#d97706`/`#fbbf24` (warning light/dark, 4×), `#dc2626`/`#fca5a5` (error light/dark, 4×), `#b91c1c` (2×) |
| views.css | 12 | FullCalendar event colors `#10b981`, `#059669`, `#8b5cf6`, `#7c3aed` (with `!important`), `#fff` (3×) |
| import.css | 11 | Status border/text colors `#f0ad4e`, `#e74c3c`, `#5bc0de`, `#c87f0a`, `#c0392b`, `#fff` (3×) |
| vfs-browser.css | 9 | `#E8A838`, `#27AE60`, `#E74C3C`, `#fff` (4×) |
| okr.css | 6 | Progress bar colors `#22c55e`/`#16a34a`, `#f59e0b`/`#d97706`, `#ef4444`/`#dc2626` |
| federation.css | 4 | `#fff` (4×) |
| copilot.css | 3 | `#fff` (3×) |
| decision-matrix.css | 2 | `#16a34a`, `#4ade80` (light/dark success) |
| settings.css | 2 | `#fff` (2×) |

### Standalone RGBA by File

| File | Count | Pattern |
|------|-------|---------|
| workspace.css | ~60 | Status badge variants at 0.08-0.15-0.25 opacity (teal, amber, red, blue), shadow `rgba(0,0,0,…)`, overlay `rgba(0,0,0,0.5)` |
| import.css | ~25 | Focus rings, status backgrounds, box-shadows |
| quadrant.css | ~25 | Quadrant section background/border colors (green, blue, amber, red) at multiple opacities + dark mode variants |
| bmc.css | ~20 | Business Model Canvas section colors |
| views.css | ~18 | Calendar, kanban, map view colors |
| okr.css | ~16 | Status colors at different opacities |
| decision-matrix.css | ~15 | Score visualization colors |
| copilot.css | ~8 | Message bubble backgrounds |
| others | ~14 | federation, settings, context-indicator, vfs-browser |

### Breakpoints

| Breakpoint | Uses | Files |
|-----------|------|-------|
| 600px | 5 | workspace.css, style.css, views.css, import.css, settings.css |
| 640px | 3 | views.css (1), style.css (2) |
| 768px | 3 | workspace.css (1), style.css (1), import.css (1) |
| 800px | 1 | bmc.css (1) |

Target: Standardize to 600px (mobile) and 768px (tablet). The 640px → 600px and 800px → 768px changes are safe since the differences are small.

## Approach

### 1. New Theme Tokens Needed

Most standalone values map to *existing* tokens. A handful need new semantic tokens:

**Already exist — direct replacement:**
- `#fff` → `var(--_color-white)` or `var(--color-on-accent)` (for text on colored backgrounds)
- `#0d9488` / `#5eead4` → `var(--color-accent)` (already has dark mode override)
- `#d97706` / `#fbbf24` → `var(--color-warning)` (need dark mode override — currently defined for `--color-warning` but not its text-on-bg variant)
- `#dc2626` / `#fca5a5` → `var(--color-error)` / `var(--color-danger)` (already has dark mode override)
- `#b91c1c` → `var(--color-error)` or `var(--color-danger)`
- `#10b981` → `var(--color-success)`
- `#3b82f6` / `#61afef` → `var(--color-primary)`
- `rgba(0,0,0,0.5)` → `var(--_color-black-overlay-medium)` (primitive exists)
- `rgba(0,0,0,0.15)` etc → `var(--shadow-*)` tokens (for box-shadow) or `var(--_color-black-shadow-sm)` (primitive exists)

**Need new tokens in theme.css:**
- `--color-warning-text` / `--color-warning-text-dark`: text color on warning badges (light: `#d97706`, dark: `#fbbf24`)
- `--color-info` / `--color-info-text`: info semantic color (light: `#5bc0de`/`#31b0d5`, dark variant)
- Badge-specific model colors (bpkm green `#10b981`, ppv amber `#f59e0b`, user purple `#8b5cf6`) — may be best as dedicated `--color-badge-*` tokens OR use `color-mix()` from existing semantics

**Quadrant/BMC/OKR colors:**
These are intentionally distinct per-section colors (e.g., quadrant Q1-Q4 each has unique background/border). They don't map to semantic theme tokens. Best approach: define them as primitive tokens (`--_color-quadrant-*`) in theme.css so dark mode can override them, then reference via `color-mix()` for opacity variants. Alternative: leave as-is since these files are self-contained and the colors are decorative, not functional. The latter is pragmatic — these are the "≤20 rgba" exemptions.

### 2. color-mix() Pattern (Established)

The codebase already uses `color-mix(in srgb, var(--color-x) 15%, transparent)` as the standard replacement for `rgba(r,g,b,0.15)`. 21 existing uses. This is the pattern for all rgba replacements.

Example transformation:
```css
/* Before */
background: rgba(20, 184, 166, 0.15);
color: #0d9488;

/* After */
background: color-mix(in srgb, var(--color-accent) 15%, transparent);
color: var(--color-accent);
```

### 3. Dark Mode Elimination

Many standalone colors exist in `[data-theme="dark"]` override blocks because the light-mode value uses a hardcoded hex. When the light-mode value is replaced with a semantic token that already has a dark-mode override in theme.css, the entire `[data-theme="dark"]` block for that rule becomes unnecessary. This is where the "~500 lines" reduction comes from — not from utility classes but from **eliminating redundant dark-mode overrides** when proper tokens are used.

Example: The `.sparql-mirror-btn` section (workspace.css:7505-7652) has ~50 lines of light-mode hardcoded colors + ~50 lines of `[data-theme="dark"]` overrides. Replace with themed vars → delete the dark override block entirely. Similar patterns across ~18 dark-mode blocks in workspace.css.

### 4. Breakpoint Standardization

4 changes total:
- `views.css:789`: `640px` → `600px`
- `style.css:1295`: `640px` → `600px`
- `style.css:1995`: `640px` → `600px`
- `bmc.css:419`: `800px` → `768px`

Trivial, safe, and independent.

### 5. FullCalendar `!important` Values (Leave As-Is)

views.css has 10 `!important` declarations on `.fc-event-task` and `.fc-event-event`. These override FullCalendar's inline styles — they're vendor overrides and can't be removed. The colors themselves should still use theme tokens, but the `!important` stays. Count them toward the "≤10 hex exemptions" allowance since they're FC-specific.

### 6. Utility Classes (Low Priority / Skip)

The audit noted `display: flex` 194×, `align-items: center` 152×, etc. in workspace.css. However:
- This codebase uses **semantic CSS classes** (`.tbox-node`, `.sparql-mirror-btn`), not utility-first classes
- Adding Tailwind-style utilities would require touching hundreds of Jinja2 templates to add class names
- The 9,170-line workspace.css won't shrink meaningfully from utility extraction without template changes
- The "~500 lines" reduction comes from dark-mode block elimination, not utility classes

**Recommendation:** Skip utility class extraction. The dark-mode elimination delivers the line reduction. Utility classes would be a much larger scope change affecting templates (S05 territory).

## Recommendation

### Task Decomposition (Natural Seams)

**T01: Add missing theme tokens to theme.css** (~30min)
- Add `--color-warning-text` (light/dark), `--color-info` semantic pair, and any other missing tokens identified during migration
- Add `--color-on-accent` if not already usable for `#fff`-on-colored-bg pattern
- This unblocks all other tasks

**T02: Migrate workspace.css — hex + rgba replacement + dark-mode block elimination** (~2-3hr)
- Largest file (32 hex, ~60 rgba, 18 dark-mode override blocks)
- Replace hardcoded values with theme vars / `color-mix()`
- Delete now-redundant `[data-theme="dark"]` blocks
- This is where the ~500-line reduction materializes

**T03: Migrate remaining CSS files — views.css, import.css, vfs-browser.css, copilot.css, federation.css, settings.css, okr.css, decision-matrix.css** (~1-2hr)
- Same mechanical pattern as T02 but across 8 smaller files
- Includes breakpoint standardization (4 changes across views.css, style.css, bmc.css)
- FullCalendar colors → theme tokens (keep `!important`)

**T04: Verify adoption metrics + visual regression check** (~30min)
- Count standalone hex/rgba → confirm ≤10 hex and ≤20 rgba
- Visual spot-check: light mode + dark mode on key pages (workspace, settings, import)
- Any intentional exemptions documented

### Risks

- **Visual regression in dark mode:** Eliminating dark-mode override blocks relies on theme tokens having correct dark-mode values. Verify each deletion against the dark theme.
- **color-mix() browser support:** Baseline 2023 — all modern browsers. Not a risk for this app (Electron/modern browser target).
- **Quadrant/BMC/OKR decorative colors:** These are semantically distinct per-section colors. Converting all to tokens would bloat theme.css with ~20 single-use primitives. Pragmatic approach: leave up to 20 of these as standalone rgba (counting toward the ≤20 target). If the planner wants full conversion, add primitive tokens like `--_color-quadrant-q1` etc.

### Verification

```bash
# Count standalone hex (target: ≤10)
rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/ | grep -v 'var(' | grep -v '^\s*/\*' | grep -v theme.css | wc -l

# Count standalone rgba (target: ≤20)
rg 'rgba?\(' frontend/static/css/ | grep -v 'var(' | grep -v '^\s*/\*' | grep -v theme.css | wc -l

# Compute adoption %
# var_uses / (var_uses + hex + rgba) >= 0.98

# Verify breakpoints standardized
rg '@media' frontend/static/css/ | grep -v '600\|768'
# Should return zero non-standard breakpoints

# Visual: dark mode toggle on workspace, settings, import pages
```

## Implementation Landscape

| File | Role | Action |
|------|------|--------|
| `frontend/static/css/theme.css` | Token definitions | Add ~5-8 new semantic tokens |
| `frontend/static/css/workspace.css` | Largest consumer | Replace 32 hex + ~60 rgba, delete ~18 dark-mode blocks |
| `frontend/static/css/views.css` | Calendar/kanban/map views | Replace 12 hex + ~18 rgba (FullCalendar `!important` stays) |
| `frontend/static/css/import.css` | Notion/Obsidian importers | Replace 11 hex + ~25 rgba |
| `frontend/static/css/vfs-browser.css` | VFS file browser | Replace 9 hex + ~5 rgba |
| `frontend/static/css/okr.css` | OKR progress bars | Replace 6 hex + ~16 rgba |
| `frontend/static/css/copilot.css` | AI copilot panel | Replace 3 hex + ~8 rgba |
| `frontend/static/css/federation.css` | SPARQL federation | Replace 4 hex + ~5 rgba |
| `frontend/static/css/decision-matrix.css` | Decision matrix view | Replace 2 hex + ~15 rgba |
| `frontend/static/css/settings.css` | Settings pages | Replace 2 hex, ~5 rgba |
| `frontend/static/css/quadrant.css` | Quadrant views | ~25 rgba (decorative — candidates for exemption) |
| `frontend/static/css/bmc.css` | Business Model Canvas | ~20 rgba (decorative — candidates for exemption) + breakpoint fix |
| `frontend/static/css/style.css` | Global styles (auth, admin) | 2 breakpoint fixes only (no standalone hex/rgba remaining) |

## Skill Discovery

No external skills needed. This is pure CSS refactoring using established codebase patterns. No new libraries or frameworks involved.
