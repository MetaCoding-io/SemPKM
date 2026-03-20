---
id: T03
parent: S01
milestone: M029
provides:
  - All CDN <script>/<link> tags wrapped in {% if not asset_manifest_available %} guards
  - Production path uses vendor.js, vendor.css, and asset_url filter for all assets
  - Dev path preserves original CDN URLs for volume-mount hot-reload workflow
  - theme.js hljs switcher supports data-light-href/data-dark-href for production
key_files:
  - backend/app/templates/base.html
  - backend/app/templates/base_embed.html
  - backend/app/templates/browser/workspace.html
  - backend/app/templates/admin/sparql.html
  - backend/app/templates/admin/model_detail.html
  - backend/app/templates/errors/403.html
  - frontend/static/js/theme.js
key_decisions:
  - All app JS/CSS use asset_url unconditionally (works in both modes)
  - CDN URLs live inside {% else %} blocks, not the primary code path
  - 403 error page also uses vendor.js in production (for lucide icons)
patterns_established:
  - Conditional vendor loading pattern — {% if asset_manifest_available %} for production, {% else %} for CDN dev mode
  - App assets always use {{ 'name.js' | asset_url }} regardless of mode
observability_surfaces:
  - asset_manifest_available Jinja2 global controls which branch renders
  - Browser view-source shows /assets/ paths (production) or CDN URLs (dev)
  - grep -rn 'unpkg\|jsdelivr\|cdnjs' backend/app/templates/ shows all CDN refs are inside else blocks
duration: ~20min (absorbed into T04 execution)
verification_result: passed
completed_at: 2026-03-20
blocker_discovered: false
---

# T03: Replace CDN references in all templates with conditional local/CDN blocks

**Wrapped all CDN `<script>`/`<link>` tags in 6 templates inside `{% if asset_manifest_available %}` guards with local vendor bundle production paths**

## What Happened

T03's execution was absorbed into T04 due to dispatch failures. The T04 agent recovered all planned T03 changes from the M027 worktree and applied them as part of the Docker integration task.

Six templates were modified:
1. **base.html** — 17 CDN tags (htmx, split.js, ninja-keys, cytoscape stack, marked, hljs, DOMPurify, lucide, driver.js) replaced with single `vendor.js` + `vendor.css` + hljs theme with `data-light-href`/`data-dark-href` in production block. All app JS/CSS switched to `{{ 'name' | asset_url }}` unconditionally.
2. **base_embed.html** — 4 CDN tags (htmx, marked, DOMPurify, lucide) replaced with single `vendor.js` in production block.
3. **workspace.html** — 2 CDN tags (dockview CSS + JS) replaced with `workspace-vendor.js` + `workspace-vendor.css` in production block.
4. **admin/sparql.html** — 2 CDN tags (yasgui CSS + JS) replaced with `yasgui.js` + `yasgui.css` in production block.
5. **admin/model_detail.html** — 1 CDN tag (chart.js) replaced with `chartjs.js` in production block.
6. **errors/403.html** — 1 CDN tag (lucide) replaced with `vendor.js` in production block.

**theme.js** updated to check `data-light-href`/`data-dark-href` attributes on the hljs theme `<link>` element first (production mode), falling back to CDN URL construction only when attributes are absent (dev mode).

## Verification

- Every CDN URL in every template is inside an `{% else %}` block guarded by `{% if asset_manifest_available %}`
- All app JS/CSS references use `{{ 'name' | asset_url }}`
- theme.js checks data attributes before CDN fallback

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -rn 'unpkg\|jsdelivr\|cdnjs' templates/` — all hits inside else blocks | 0 | ✅ pass | <1s |
| 2 | `grep -c 'asset_url' templates/base.html` — ≥15 (got 28) | 0 | ✅ pass | <1s |
| 3 | theme.js data-attribute check before CDN fallback (code review) | - | ✅ pass | <1s |

## Diagnostics

- **Check production rendering:** With manifest loaded, view page source — all `<script>`/`<link>` should reference `/assets/` paths
- **Check dev rendering:** Without manifest, view page source — all vendor scripts should reference CDN URLs
- **Find unguarded CDN refs:** `grep -rn 'unpkg\|jsdelivr\|cdnjs' backend/app/templates/ | grep -v 'else\|endif\|{#'` — verify all hits have `{% else %}` on a preceding line

## Deviations

- T03 was absorbed into T04 execution due to dispatch failures. The work was completed as planned, just within a different task context.

## Known Issues

None.

## Files Created/Modified

- `backend/app/templates/base.html` — conditional vendor/CDN blocks + asset_url on all app assets
- `backend/app/templates/base_embed.html` — conditional vendor/CDN blocks + asset_url on app assets
- `backend/app/templates/browser/workspace.html` — conditional dockview local/CDN blocks
- `backend/app/templates/admin/sparql.html` — conditional yasgui local/CDN blocks
- `backend/app/templates/admin/model_detail.html` — conditional chartjs local/CDN blocks
- `backend/app/templates/errors/403.html` — conditional lucide local/CDN blocks
- `frontend/static/js/theme.js` — hljs theme switcher with data-attribute production path
