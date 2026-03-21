# S03: CSS Code-Splitting & Route Optimization — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

This is a straightforward template-level change, not a build tool change. The current `base.html` loads 5 workspace-specific CSS files (workspace.css, forms.css, views.css, settings.css, vfs-browser.css — 227KB raw, ~30KB minified+gzipped combined) on every page, including admin, guide, health, shortcuts, import, and debug pages that don't need them. The fix is to move those CSS `<link>` tags out of `base.html` into a new `{% block page_css %}` block that workspace.html overrides.

Cross-section navigation (admin ↔ workspace) already uses `hx-boost="false"` on all sidebar links, which triggers full page reloads. This means CSS loaded in `<head>` is always correct for the current page section — no risk of missing CSS from htmx partial swaps.

The approach aligns with D271 (CSS splitting via template block inheritance, not build tool) and PERF-06 (CSS code-splitting by route).

## Recommendation

**Add a `{% block page_css %}` block to `base.html`** between the shared CSS (theme.css, style.css) and the `{% block head %}` block. Move all 5 workspace CSS `<link>` tags into the default content of this block. Workspace.html inherits the default. Admin templates override it to empty. Auth pages (login.html, setup.html) are static HTML files served by nginx — they already only load theme.css + style.css and need no changes.

This is the simplest approach because:
1. Admin templates (10 files) all extend base.html and don't override `{% block head %}` — they can override the new block to empty
2. Workspace.html already uses `{% block head %}` with `{{ super() }}` for its additional CSS — the workspace CSS stack stays in the default block content
3. No build.js changes needed — esbuild already minifies each CSS file individually
4. The import pages (notion, obsidian) use `/css/import.css` directly and don't need workspace CSS — they should also override to empty

## Implementation Landscape

### Key Files

**Template changes (the core work):**
- `backend/app/templates/base.html` — Move workspace CSS `<link>` tags from the `<head>` body into a new `{% block page_css %}` block (lines 50-54). Shared CSS (theme.css, style.css, vendor CSS) stays outside the block.
- `backend/app/templates/admin/index.html` — Add `{% block page_css %}{% endblock %}` (empty override)
- `backend/app/templates/admin/models.html` — Same empty override
- `backend/app/templates/admin/model_detail.html` — Same empty override
- `backend/app/templates/admin/sparql.html` — Same empty override (SPARQL console uses yasgui CSS, not workspace CSS)
- `backend/app/templates/admin/ops_log.html` — Same empty override
- `backend/app/templates/admin/webhooks.html` — Same empty override
- `backend/app/templates/admin/api_tokens.html` — Same empty override
- `backend/app/templates/admin/model_entailment_config.html` — Same empty override
- `backend/app/templates/admin/apps/list.html` — Same empty override
- `backend/app/templates/admin/apps/detail.html` — Same empty override
- `backend/app/templates/notion/import.html` — Empty override (has its own import.css in `{% block head %}`)
- `backend/app/templates/obsidian/import.html` — Empty override (has its own import.css in `{% block head %}`)
- `backend/app/templates/guide.html` — Empty override (guide pages don't use workspace classes)
- `backend/app/templates/guide_article.html` — Empty override
- `backend/app/templates/health.html` — Empty override
- `backend/app/templates/shortcuts.html` — Empty override
- `backend/app/templates/debug/sparql.html` — Empty override
- `backend/app/templates/debug/event_console.html` — Empty override
- `backend/app/templates/debug/commands.html` — Empty override
- `backend/app/templates/dashboard.html` — Needs workspace CSS (dashboard uses view-embed blocks with table/card rendering that depends on views.css), keep default

**Templates that need workspace CSS (should NOT override):**
- `backend/app/templates/browser/workspace.html` — Primary consumer. Uses default (inherits workspace CSS from base.html block).
- `backend/app/templates/browser/vfs_browser.html` — Uses vfs-browser.css classes. Uses default.
- `backend/app/templates/browser/settings_standalone.html` — Uses settings.css classes. Uses default.
- `backend/app/templates/dashboard.html` — Dashboard view-embed blocks render table/cards that use views.css. Uses default.

**No changes needed:**
- `frontend/build.js` — No build changes. CSS files are already individually minified and content-hashed.
- `frontend/nginx.conf` — No nginx changes. CSS is served from `/assets/` (production) or `/css/` (dev) regardless of which pages load them.
- `backend/app/template_helpers.py` — No filter changes.
- `frontend/static/login.html`, `frontend/static/setup.html` — Already only load theme.css + style.css (hardcoded paths, not Jinja2). No changes needed.

### Template Change Pattern

The change in `base.html` (lines 49-56 currently):

```
{# Before #}
<link rel="stylesheet" href="{{ 'workspace.css' | asset_url }}">
<link rel="stylesheet" href="{{ 'forms.css' | asset_url }}">
<link rel="stylesheet" href="{{ 'views.css' | asset_url }}">
<link rel="stylesheet" href="{{ 'settings.css' | asset_url }}">
<link rel="stylesheet" href="{{ 'vfs-browser.css' | asset_url }}">

{# After #}
{% block page_css %}
<link rel="stylesheet" href="{{ 'workspace.css' | asset_url }}">
<link rel="stylesheet" href="{{ 'forms.css' | asset_url }}">
<link rel="stylesheet" href="{{ 'views.css' | asset_url }}">
<link rel="stylesheet" href="{{ 'settings.css' | asset_url }}">
<link rel="stylesheet" href="{{ 'vfs-browser.css' | asset_url }}">
{% endblock %}
```

Each admin/non-workspace template adds one line after `{% extends "base.html" %}`:
```
{% block page_css %}{% endblock %}
```

Templates that need workspace CSS (workspace.html, vfs_browser.html, settings_standalone.html, dashboard.html) do nothing — they inherit the default block content.

### Build Order

1. **First: modify base.html** — Add the `{% block page_css %}` wrapping. This is a no-op until templates start overriding it (all existing behavior preserved).
2. **Second: add empty overrides to admin templates** — All 10 admin templates plus debug/import/guide/health/shortcuts templates get `{% block page_css %}{% endblock %}`.
3. **Third: verify** — Check that admin pages render correctly without workspace CSS, and workspace pages still have it.

This is a single task — all changes are in templates, no cross-file dependencies, no build changes.

### Verification Approach

1. **Docker build + workspace check:** Load `/browser/` and confirm workspace CSS loads correctly (panels, explorer, object view all render).
2. **Admin page check:** Load `/admin/models` directly (full page load) and verify:
   - Page renders correctly (uses style.css for layout)
   - Network tab shows NO request for workspace.css, forms.css, views.css, settings.css, or vfs-browser.css
   - OR in production: no `/assets/workspace-*.min.css` request
3. **Guide/health/shortcuts check:** Load `/guide`, `/health/`, `/shortcuts` — no workspace CSS loaded.
4. **Dashboard check:** Load a dashboard page — workspace CSS IS loaded (views.css needed for view-embed blocks).
5. **htmx cross-navigation:** From workspace, click admin sidebar link (htmx swap) — admin content renders correctly (workspace CSS still loaded from initial page load, harmless). From admin (direct load), click Object Browser sidebar link — full page reload, workspace CSS loads.
6. **Size verification:** `curl -sI` on admin page HTML response, confirm no workspace CSS `<link>` tags in response.

**Specific command:**
```bash
# Verify admin page does NOT include workspace CSS
docker compose exec api python -c "
from app.main import app
from httpx import AsyncClient
import asyncio
async def check():
    async with AsyncClient(app=app, base_url='http://test') as c:
        r = await c.get('/admin/models')
        assert 'workspace.css' not in r.text or 'workspace.css' in r.text.split('page_css')[0]
asyncio.run(check())
"

# OR simpler — grep the rendered HTML
curl -s http://localhost:3000/admin/models | grep -c 'workspace'
# Should return 0 (no workspace CSS references)
```

## Constraints

- **Admin page `sparql-results` table class** — Admin templates use `table.sparql-results` class which is defined in `style.css` (confirmed at line 264), NOT in views.css. So removing views.css from admin pages is safe.
- **`dashboard.html` needs views.css** — Dashboard view-embed blocks render table/cards that depend on views.css classes. Dashboard must NOT override `{% block page_css %}`.
- **`base_embed.html` is a separate template** — It's NOT affected by this change. It has its own hardcoded CSS loads (theme.css, style.css, workspace.css, views.css) for iframe content. These are correct since embed content renders workspace objects.
- **Import pages use hardcoded `/css/import.css`** — Not through `asset_url` filter. These should be converted to `{{ 'import.css' | asset_url }}` as a minor cleanup, but this is not required for the CSS splitting goal.

## Common Pitfalls

- **Forgetting a template** — If a new template is added later that extends base.html but doesn't need workspace CSS, it will get it by default (from the `{% block page_css %}` default content). This is the safe direction — extra CSS is harmless, missing CSS breaks pages. Templates that want to opt out add the empty override.
- **htmx partial rendering + CSS** — When htmx renders admin content into a page that initially loaded workspace CSS (e.g., workspace → admin via sidebar click), the workspace CSS is still in `<head>`. This is harmless — unused CSS rules don't cause visual issues. The only time CSS splitting matters is on full page loads (direct URL navigation).
