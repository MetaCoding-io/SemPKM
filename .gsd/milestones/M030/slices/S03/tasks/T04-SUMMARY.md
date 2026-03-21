---
id: T04
parent: S03
milestone: M030
provides:
  - Dismiss buttons (×) on lint panel warning/info results with fetch() + htmx refresh
  - Suppress buttons (eye-off) on lint dashboard result rows with fetch() + htmx refresh
  - Preset selector dropdown in lint dashboard sidebar with apply/save functionality
  - "N dismissed" indicator on lint panel, "N rules suppressed" badge on dashboard sidebar
  - detail=True passed to dashboard's LintService.get_results() so source_shape is available for suppress buttons
key_files:
  - backend/app/templates/browser/lint_panel.html
  - backend/app/templates/browser/lint_dashboard.html
  - frontend/static/js/workspace.js
  - frontend/static/css/workspace.css
  - backend/app/browser/pages.py
key_decisions:
  - Violations are NOT dismissable (structural issues that must be resolved); only warnings and infos get dismiss buttons
  - Preset selector "No preset" option clears all suppressions via DELETE /api/lint/suppressions
  - Suppress buttons show on hover only (opacity 0 → 1 transition) to keep the dashboard clean
patterns_established:
  - Lint filter JS uses fetch() + htmx.ajax() refresh pattern (same as favorites, dashboards)
  - All lint filter buttons exposed to global scope via window.X for onclick handlers in templates
  - CSS follows CLAUDE.md Lucide SVG rules (flex-shrink: 0, stroke: currentColor) for all new button SVGs
observability_surfaces:
  - Browser console: JS errors from filter handlers logged with descriptive prefixes (e.g., "dismissLintResult error:")
  - Network tab: dismiss/suppress/preset actions produce observable fetch() calls to /api/lint/* endpoints
  - Template context: dismissed_count in lint panel, suppressed_count and active_presets in dashboard
duration: 25m
verification_result: passed
completed_at: 2026-03-20T23:55:00-04:00
blocker_discovered: false
---

# T04: Lint panel dismiss buttons and lint dashboard suppress/preset controls

**Added dismiss buttons on lint panel warnings/infos, suppress buttons on dashboard result rows, and preset selector in dashboard sidebar — all using fetch() + htmx refresh pattern with CLAUDE.md-compliant CSS.**

## What Happened

Implemented the user-facing UI for the lint filter system across 5 files:

1. **Lint panel template** (`lint_panel.html`): Added dismiss buttons (Lucide `x` icon) next to each warning and info result item. Buttons only render when `source_shape` is present (required for stable identification). Violations intentionally excluded — they're structural and shouldn't be dismissable. Added "N dismissed" indicator below results when `dismissed_count > 0`.

2. **Lint dashboard template** (`lint_dashboard.html`): Added a new column with suppress buttons (Lucide `eye-off` icon) in each result row. Added a "Preset" sidebar group below Sort with a `<select>` dropdown populated from `active_presets` and a "Save Current" button (Lucide `save` icon). Added "N rules suppressed" badge in the sidebar summary section.

3. **JavaScript handlers** (`workspace.js`): Added 4 functions in a new IIFE section — `dismissLintResult()`, `suppressLintRule()`, `applyLintPreset()`, `saveLintPreset()`. All use `fetch()` for API calls and `htmx.ajax()` for UI refresh, matching the established codebase pattern. `saveLintPreset()` prompts for a name, fetches current suppressions, and creates the preset. All exposed to `window` for template onclick handlers.

4. **CSS** (`workspace.css`): Added styles for `.lint-dismiss-btn`, `.lint-suppress-btn`, `.lint-dismissed-indicator`, `.lint-suppressed-badge`, `.lint-preset-actions`, and `.lint-preset-save-btn`. All SVG rules include `flex-shrink: 0` and `stroke: currentColor` per CLAUDE.md. Dismiss and suppress buttons use hover-reveal pattern (opacity transition).

5. **Dashboard route** (`pages.py`): Added `detail=True` to `lint_service.get_results()` call so `source_shape` is included in each result item, enabling the suppress button to reference the rule.

## Verification

- All 59 slice tests pass (30 filter service + 11 filtering + 18 API)
- Jinja2 template parsing verified for both modified templates
- JavaScript syntax check passed (`node -c workspace.js`)
- Python AST parsing verified for both modified Python files
- Template correctness verified: violations section has NO dismiss buttons, warnings and infos DO
- CSS has `flex-shrink: 0` and `stroke: currentColor` on all 3 new SVG button rules
- `detail=True` confirmed in dashboard route
- Docker stack browser verification:
  - Lint dashboard shows 4 result rows with suppress buttons (eye-off icons appear on hover)
  - Clicking suppress on "empty body" rule → row disappears, "1 rule suppressed" badge appears in sidebar
  - "Save Current" → preset "Test Preset" appears in dropdown
  - Selecting "No preset" → clears all suppressions, 4 rows return
  - Applying "Test Preset" → re-suppresses the empty body rule, back to 3 rows
  - Lint panel shows dismiss (×) buttons on warnings/infos, NOT on violations
  - Clicking dismiss → warning disappears, "1 dismissed" indicator appears

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_lint_filter_service.py -v` | 0 | ✅ pass | 1.6s |
| 2 | `cd backend && .venv/bin/python -m pytest tests/test_lint_filtering.py -v` | 0 | ✅ pass | 0.2s |
| 3 | `cd backend && .venv/bin/python -m pytest tests/test_lint_filter_api.py -v` | 0 | ✅ pass | 2.4s |
| 4 | Jinja2 template parse check (lint_panel.html, lint_dashboard.html) | 0 | ✅ pass | <1s |
| 5 | `node -c workspace.js` (JS syntax check) | 0 | ✅ pass | <1s |
| 6 | Python AST parse check (pages.py, objects.py) | 0 | ✅ pass | <1s |
| 7 | Docker browser: suppress rule → row disappears, badge shows | - | ✅ pass | - |
| 8 | Docker browser: save preset → appears in dropdown | - | ✅ pass | - |
| 9 | Docker browser: clear → apply preset → suppressions restored | - | ✅ pass | - |
| 10 | Docker browser: dismiss warning → disappears, "1 dismissed" shows | - | ✅ pass | - |

## Diagnostics

- **Inspect dismiss buttons**: Open an object with lint warnings → LINT section in right pane shows × buttons on warning/info items (not on violations)
- **Inspect suppress buttons**: Open LINT tab in bottom panel → each result row has an eye-off icon that appears on hover
- **Inspect preset selector**: Scroll sidebar in LINT dashboard → "Preset" dropdown with "No preset" default + any saved presets
- **JS error diagnostics**: Open browser DevTools console → filter handlers log errors with prefixes like `dismissLintResult error:`
- **Network diagnostics**: DevTools Network tab shows fetch calls to `/api/lint/dismiss`, `/api/lint/suppress`, `/api/lint/presets`

## Deviations

None — implemented exactly as planned.

## Known Issues

- Frontend build pipeline (M029) requires `cd frontend && npm ci && node build.js` to produce hashed assets, then a Docker frontend container rebuild to pick up new JS/CSS. Volume-mounted raw files are NOT served in production mode — only the built/minified versions from the `frontend_assets` volume are used.

## Files Created/Modified

- `backend/app/templates/browser/lint_panel.html` — Added dismiss buttons (×) on warning/info results + dismissed count indicator
- `backend/app/templates/browser/lint_dashboard.html` — Added suppress buttons per row, preset selector + save button in sidebar, suppressed count badge
- `frontend/static/js/workspace.js` — Added dismissLintResult, suppressLintRule, applyLintPreset, saveLintPreset functions in new IIFE section
- `frontend/static/css/workspace.css` — Added CSS for dismiss/suppress/preset UI elements with CLAUDE.md-compliant SVG rules
- `backend/app/browser/pages.py` — Added detail=True to dashboard lint_service.get_results() call
- `.gsd/milestones/M030/slices/S03/tasks/T04-PLAN.md` — Added Observability Impact section (pre-flight fix)
