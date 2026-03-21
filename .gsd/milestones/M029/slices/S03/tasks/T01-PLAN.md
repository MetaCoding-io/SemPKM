---
estimated_steps: 4
estimated_files: 20
---

# T01: Add page_css block to base.html and empty overrides to 19 non-workspace templates

**Slice:** S03 — CSS Code-Splitting & Route Optimization
**Milestone:** M029

## Description

Split CSS loading by route using Jinja2 template block inheritance. The 5 workspace-specific CSS files (workspace.css, forms.css, views.css, settings.css, vfs-browser.css — ~227KB raw) currently load on every page including admin, guide, health, debug, and import pages that don't use any workspace CSS classes. By wrapping these `<link>` tags in a `{% block page_css %}` block in `base.html`, non-workspace templates can override the block to empty to skip loading them entirely.

This is a low-risk, high-impact change: admin pages drop ~227KB of unused CSS, and the pattern is safe by default — any future template that forgets to override will still get workspace CSS (extra CSS is harmless; missing CSS breaks pages).

## Steps

1. **Edit `backend/app/templates/base.html`** — Wrap the 5 workspace CSS `<link>` tags (lines 50-54) in a `{% block page_css %}...{% endblock %}` block. The block should go between the shared CSS / vendor CSS (lines above) and the `<script>` / `{% block head %}` lines below. The result should look like:
   ```html
   {% block page_css %}
   <link rel="stylesheet" href="{{ 'workspace.css' | asset_url }}">
   <link rel="stylesheet" href="{{ 'forms.css' | asset_url }}">
   <link rel="stylesheet" href="{{ 'views.css' | asset_url }}">
   <link rel="stylesheet" href="{{ 'settings.css' | asset_url }}">
   <link rel="stylesheet" href="{{ 'vfs-browser.css' | asset_url }}">
   {% endblock %}
   ```
   Important: Do NOT move or change any other lines. The `tutorials.js` script and `{% block head %}` that follow should stay in place.

2. **Add empty `{% block page_css %}{% endblock %}` to all 19 non-workspace templates.** Place it on the line immediately after `{% extends "base.html" %}`. The templates are:

   **Admin templates (10):**
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

   **Debug templates (3):**
   - `backend/app/templates/debug/commands.html`
   - `backend/app/templates/debug/event_console.html`
   - `backend/app/templates/debug/sparql.html`

   **Guide templates (2):**
   - `backend/app/templates/guide.html`
   - `backend/app/templates/guide_article.html`

   **Import templates (2):**
   - `backend/app/templates/notion/import.html`
   - `backend/app/templates/obsidian/import.html`

   **Other (2):**
   - `backend/app/templates/health.html`
   - `backend/app/templates/shortcuts.html`

3. **Verify workspace-needing templates do NOT override the block.** These 4 templates must inherit the default `{% block page_css %}` content (i.e., they load all 5 workspace CSS files). Confirm none of them already have or need a `{% block page_css %}` override:
   - `backend/app/templates/browser/workspace.html`
   - `backend/app/templates/browser/vfs_browser.html`
   - `backend/app/templates/browser/settings_standalone.html`
   - `backend/app/templates/dashboard.html`

4. **Rebuild Docker and verify via curl checks:**
   ```bash
   docker compose build frontend
   docker compose up -d
   # Wait for stack to be ready
   sleep 5

   # Admin page should have ZERO workspace CSS references
   count=$(curl -s http://localhost:3000/admin/models | grep -c 'workspace\.css\|workspace-')
   echo "Admin workspace CSS count: $count"  # expect 0

   # Workspace page should have workspace CSS
   count=$(curl -s http://localhost:3000/browser/ | grep -c 'workspace\.css\|workspace-')
   echo "Workspace CSS count: $count"  # expect >= 1

   # Guide page should have ZERO workspace CSS references
   count=$(curl -s http://localhost:3000/guide | grep -c 'workspace\.css\|workspace-')
   echo "Guide workspace CSS count: $count"  # expect 0

   # Health page should have ZERO workspace CSS references
   count=$(curl -s http://localhost:3000/health/ | grep -c 'workspace\.css\|workspace-')
   echo "Health workspace CSS count: $count"  # expect 0
   ```

## Must-Haves

- [ ] `{% block page_css %}` wraps exactly the 5 workspace CSS `<link>` tags in base.html
- [ ] All 19 non-workspace templates have `{% block page_css %}{% endblock %}` empty override
- [ ] 4 workspace-needing templates (workspace.html, vfs_browser.html, settings_standalone.html, dashboard.html) do NOT override `{% block page_css %}`
- [ ] Admin pages render correctly without workspace CSS (uses style.css for layout)
- [ ] Workspace pages render correctly with all 5 workspace CSS files present

## Verification

- `grep -c 'block page_css' backend/app/templates/base.html` returns `2` (open + close)
- `grep -rl 'block page_css' backend/app/templates/ | wc -l` returns `20` (base.html + 19 overriders)
- `grep -rL 'block page_css' backend/app/templates/browser/workspace.html backend/app/templates/browser/vfs_browser.html backend/app/templates/browser/settings_standalone.html backend/app/templates/dashboard.html` returns all 4 files (they should NOT contain it)
- Docker curl: admin page has 0 workspace CSS references, workspace page has ≥1
- Docker curl: guide and health pages have 0 workspace CSS references

## Observability Impact

- **What changes:** Non-workspace pages no longer emit `<link>` tags for workspace.css, forms.css, views.css, settings.css, vfs-browser.css. No new logging or metrics.
- **How to inspect:** `curl -s <page_url> | grep 'workspace\.css'` — empty output means the override is working. Presence of workspace CSS link tags means the template inherits the default block.
- **Failure visibility:** Missing workspace CSS on workspace pages causes immediate visual breakage (no sidebar layout, no panel styles). Extra workspace CSS on non-workspace pages is harmless — just wasted bandwidth.

## Inputs

- `backend/app/templates/base.html` — current base template with 5 workspace CSS `<link>` tags at lines 50-54
- S01 summary — `{{ 'name' | asset_url }}` filter pattern works in both dev and production modes; no build.js changes needed

## Expected Output

- `backend/app/templates/base.html` — modified with `{% block page_css %}` wrapper around workspace CSS links
- 19 template files — each with one added line: `{% block page_css %}{% endblock %}`
- Admin pages serving ~30KB less CSS per page load
- PERF-06 requirement (CSS code-splitting by route) delivered
