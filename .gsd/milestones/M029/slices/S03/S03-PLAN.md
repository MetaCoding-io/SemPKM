# S03: CSS Code-Splitting & Route Optimization

**Goal:** Admin, guide, health, debug, import, and shortcut pages load only shared CSS (theme.css, style.css) — not the 5 workspace-specific CSS files (workspace.css, forms.css, views.css, settings.css, vfs-browser.css). Workspace and dashboard pages continue loading the full CSS stack.
**Demo:** Load `/admin/models` in a browser — network tab shows zero requests for workspace.css, forms.css, views.css, settings.css, or vfs-browser.css. Load `/browser/` — all 5 workspace CSS files are present.

## Must-Haves

- `{% block page_css %}` in `base.html` wrapping the 5 workspace CSS `<link>` tags
- 19 templates that don't need workspace CSS override the block to empty
- 4 templates that need workspace CSS (workspace.html, vfs_browser.html, settings_standalone.html, dashboard.html) inherit the default unchanged
- Admin pages render correctly without workspace CSS (layout uses style.css)
- No visual regression on workspace pages

## Verification

- `docker compose build frontend && docker compose up -d` — stack starts without error
- `curl -s http://localhost:3000/admin/models | grep -c 'workspace'` returns `0` — no workspace CSS on admin pages
- `curl -s http://localhost:3000/browser/ | grep -c 'workspace'` returns ≥ `1` — workspace CSS present on workspace page
- `curl -s http://localhost:3000/guide | grep -c 'workspace'` returns `0` — no workspace CSS on guide page
- `curl -s http://localhost:3000/health/ | grep -c 'workspace'` returns `0` — no workspace CSS on health page
- Workspace page visually functional — sidebar, explorer, object tabs render correctly

## Tasks

- [x] **T01: Add page_css block to base.html and empty overrides to 19 non-workspace templates** `est:30m`
  - Why: This is the entire slice — a template-level change that splits CSS loading by route via Jinja2 block inheritance
  - Files: `backend/app/templates/base.html`, plus 19 templates getting empty `{% block page_css %}{% endblock %}` overrides
  - Do: (1) In base.html, wrap lines 50-54 (the 5 workspace CSS `<link>` tags) inside `{% block page_css %}...{% endblock %}`. (2) Add `{% block page_css %}{% endblock %}` after the `{% extends "base.html" %}` line in all 19 non-workspace templates. (3) Verify the 4 workspace-needing templates (workspace.html, vfs_browser.html, settings_standalone.html, dashboard.html) do NOT override the block — they inherit the default content.
  - Verify: `docker compose build frontend && docker compose up -d`, then curl admin/guide/health pages and confirm zero `workspace` CSS references. Curl workspace page and confirm workspace CSS still loads.
  - Done when: Admin pages have zero workspace CSS `<link>` tags in rendered HTML; workspace pages still have all 5.

## Observability / Diagnostics

- **Inspection surface:** `curl -s <page_url> | grep -c 'workspace\.css'` — returns 0 for non-workspace pages, ≥1 for workspace pages. Works in both dev and production.
- **Failure visibility:** If a non-workspace template forgets the empty override, it loads extra CSS (cosmetically harmless, no breakage). If a workspace template accidentally overrides to empty, workspace CSS is missing and layout breaks visually — immediately obvious on page load.
- **Runtime signals:** No new logging or metrics. The change is purely in Jinja2 template rendering — CSS `<link>` tags are present or absent in the rendered HTML `<head>`.
- **Redaction:** No secrets or PII involved. CSS file paths are public static assets.

## Files Likely Touched

- `backend/app/templates/base.html`
- `backend/app/templates/admin/index.html`
- `backend/app/templates/admin/models.html`
- `backend/app/templates/admin/model_detail.html`
- `backend/app/templates/admin/model_entailment_config.html`
- `backend/app/templates/admin/sparql.html`
- `backend/app/templates/admin/ops_log.html`
- `backend/app/templates/admin/webhooks.html`
- `backend/app/templates/admin/api_tokens.html`
- `backend/app/templates/admin/apps/list.html`
- `backend/app/templates/admin/apps/detail.html`
- `backend/app/templates/debug/commands.html`
- `backend/app/templates/debug/event_console.html`
- `backend/app/templates/debug/sparql.html`
- `backend/app/templates/guide.html`
- `backend/app/templates/guide_article.html`
- `backend/app/templates/health.html`
- `backend/app/templates/shortcuts.html`
- `backend/app/templates/notion/import.html`
- `backend/app/templates/obsidian/import.html`
