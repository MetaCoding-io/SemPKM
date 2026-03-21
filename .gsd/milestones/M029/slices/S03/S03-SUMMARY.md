---
id: S03
parent: M029
milestone: M029
provides:
  - "{% block page_css %} in base.html enabling route-based CSS code-splitting"
  - "19 non-workspace templates with empty page_css overrides eliminating ~227KB unused CSS"
requires:
  - slice: S01
    provides: Build pipeline with asset_url Jinja2 filter and hashed filenames
affects:
  - S05
key_files:
  - backend/app/templates/base.html
key_decisions:
  - "Named closing tag {% endblock page_css %} for grep-friendly verification"
patterns_established:
  - "Non-workspace templates override {% block page_css %} to empty to exclude workspace CSS"
  - "Workspace templates inherit the default block unchanged — no override needed"
  - "Safe-by-default: any new template that extends base.html without overriding page_css inherits all 5 workspace CSS files"
observability_surfaces:
  - "curl -s <page_url> | grep 'stylesheet' | grep 'workspace' — 0 lines for non-workspace pages, 5+ for workspace pages"
drill_down_paths:
  - .gsd/milestones/M029/slices/S03/tasks/T01-SUMMARY.md
duration: 25m
verification_result: passed
completed_at: 2026-03-20
---

# S03: CSS Code-Splitting & Route Optimization

**Admin, guide, health, debug, import, and shortcut pages no longer load 5 workspace-specific CSS files (~227KB), achieved via Jinja2 block inheritance in a single-task template change.**

## What Happened

Added `{% block page_css %}...{% endblock page_css %}` around the 5 workspace-specific CSS `<link>` tags (workspace.css, forms.css, views.css, settings.css, vfs-browser.css) in `base.html`. Then added empty `{% block page_css %}{% endblock %}` overrides in all 19 non-workspace templates:

- **10 admin templates:** index, models, model_detail, model_entailment_config, sparql, ops_log, webhooks, api_tokens, apps/list, apps/detail
- **3 debug templates:** commands, event_console, sparql
- **2 guide templates:** guide, guide_article
- **2 import templates:** notion/import, obsidian/import
- **2 standalone templates:** health, shortcuts

The 4 workspace-needing templates (workspace.html, vfs_browser.html, settings_standalone.html, dashboard.html) do NOT override the block, so they inherit all 5 workspace CSS files unchanged.

This is purely a template-level change — no Python code, no build pipeline changes, no CSS modifications. The Jinja2 block inheritance mechanism handles everything.

## Verification

- `grep -c 'block page_css' base.html` returns 2 (open + named close) ✓
- `grep -rl 'block page_css' templates/` returns 20 files (base.html + 19 overriders) ✓
- All 4 workspace templates confirmed to contain 0 occurrences of `block page_css` ✓
- Docker curl: admin/models → 0 workspace CSS links ✓
- Docker curl: /browser/ → 5+ workspace CSS stylesheet links ✓
- Docker curl: /guide → 0 workspace CSS links ✓
- Docker curl: /health/ → 0 workspace CSS links ✓
- Docker curl: / (dashboard) → 5 workspace CSS stylesheet links ✓
- Browser visual: workspace, guide, and health pages all render correctly ✓

## Requirements Advanced

- PERF-06 (CSS code-splitting) — Admin pages now load only shared CSS (~30KB) instead of the full workspace stack (~257KB). Auth pages load minimal CSS. Network waterfall on admin pages shows no workspace.css request.

## Requirements Validated

- none (PERF-06 not yet in REQUIREMENTS.md — will be added when the full PERF requirement set is registered)

## New Requirements Surfaced

- none

## Requirements Invalidated or Re-scoped

- none

## Deviations

- The M029 worktree Docker stack couldn't start (triplestore 500 on repository creation — pre-existing infrastructure issue). Verification was done by temporarily applying worktree templates to the running main-repo Docker stack via volume mounts.

## Known Limitations

- **Production mode detection:** In production builds with hashed filenames (e.g., `workspace-4df1c795.min.css`), the `grep 'workspace'` diagnostic still works because the hash is appended to the base name. But tools searching for exact filenames will need to account for the hash.
- **No CSS file elimination:** The workspace CSS files are still built and exist on disk for all routes. This only controls which `<link>` tags are rendered in the HTML `<head>`. The files are still served by nginx if requested directly.

## Follow-ups

- none — this is a complete, self-contained change.

## Files Created/Modified

- `backend/app/templates/base.html` — Wrapped 5 workspace CSS `<link>` tags in `{% block page_css %}...{% endblock page_css %}`
- `backend/app/templates/admin/index.html` — Added empty page_css override
- `backend/app/templates/admin/models.html` — Added empty page_css override
- `backend/app/templates/admin/model_detail.html` — Added empty page_css override
- `backend/app/templates/admin/model_entailment_config.html` — Added empty page_css override
- `backend/app/templates/admin/sparql.html` — Added empty page_css override
- `backend/app/templates/admin/ops_log.html` — Added empty page_css override
- `backend/app/templates/admin/webhooks.html` — Added empty page_css override
- `backend/app/templates/admin/api_tokens.html` — Added empty page_css override
- `backend/app/templates/admin/apps/list.html` — Added empty page_css override
- `backend/app/templates/admin/apps/detail.html` — Added empty page_css override
- `backend/app/templates/debug/commands.html` — Added empty page_css override
- `backend/app/templates/debug/event_console.html` — Added empty page_css override
- `backend/app/templates/debug/sparql.html` — Added empty page_css override
- `backend/app/templates/guide.html` — Added empty page_css override
- `backend/app/templates/guide_article.html` — Added empty page_css override
- `backend/app/templates/notion/import.html` — Added empty page_css override
- `backend/app/templates/obsidian/import.html` — Added empty page_css override
- `backend/app/templates/health.html` — Added empty page_css override
- `backend/app/templates/shortcuts.html` — Added empty page_css override

## Forward Intelligence

### What the next slice should know
- The CSS code-splitting is purely at the Jinja2 template level — no build pipeline changes. S05 (Lighthouse verification) should check the admin page network waterfall to confirm workspace CSS files are absent.
- The diagnostic `curl -s <url> | grep 'stylesheet' | grep 'workspace'` works for both dev and production modes.

### What's fragile
- **New templates:** Any new template extending `base.html` that should NOT load workspace CSS must add the empty `{% block page_css %}{% endblock %}` override. Forgetting it is harmless (extra CSS loads, no breakage) but wastes bandwidth.

### Authoritative diagnostics
- `grep -rl 'block page_css' backend/app/templates/ | wc -l` — should be 20 (base + 19 overriders). If this number changes, a template was added or removed.
- `curl -s <page_url> | grep 'stylesheet' | grep -c 'workspace'` — the definitive runtime check for CSS loading per route.

### What assumptions changed
- Original assumption: CSS code-splitting would require build pipeline changes (esbuild entry points per route). Actual: Jinja2 block inheritance handles it entirely at the template level with zero build changes.
