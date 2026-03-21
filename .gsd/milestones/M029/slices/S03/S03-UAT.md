# S03: CSS Code-Splitting & Route Optimization — UAT

**Milestone:** M029
**Written:** 2026-03-20

## UAT Type

- UAT mode: mixed (artifact-driven template checks + live-runtime curl verification)
- Why this mode is sufficient: The change is purely in Jinja2 templates — rendered HTML output is the only meaningful verification surface. No JavaScript logic, no backend behavior, no database state to check.

## Preconditions

- Docker stack running (`docker compose up -d`) with the M029 changes applied
- At least one Mental Model installed (so workspace page has content)
- Access to `curl` or a browser with DevTools network tab

## Smoke Test

```bash
curl -s http://localhost:3000/admin/models | grep -c 'workspace'
# Expected: 0
```

If this returns 0, the core CSS code-splitting is working.

## Test Cases

### 1. Admin pages exclude workspace CSS

1. Run `curl -s http://localhost:3000/admin/ | grep 'stylesheet' | grep -E 'workspace|forms\.css|views\.css|settings\.css|vfs-browser'`
2. **Expected:** No output (zero matching lines). Admin index page loads zero workspace-specific CSS files.

3. Run `curl -s http://localhost:3000/admin/models | grep 'stylesheet' | grep -E 'workspace|forms\.css|views\.css|settings\.css|vfs-browser'`
4. **Expected:** No output. Models page loads zero workspace CSS files.

5. Run `curl -s http://localhost:3000/admin/webhooks | grep 'stylesheet' | grep -E 'workspace|forms\.css|views\.css|settings\.css|vfs-browser'`
6. **Expected:** No output.

### 2. Workspace page includes all workspace CSS

1. Run `curl -s http://localhost:3000/browser/ | grep 'stylesheet' | grep -E 'workspace|forms\.css|views\.css|settings\.css|vfs-browser' | wc -l`
2. **Expected:** 5 (one link per workspace CSS file: workspace.css, forms.css, views.css, settings.css, vfs-browser.css). In production mode, filenames are hashed (e.g., `workspace-4df1c795.min.css`) but the base name prefix still matches.

### 3. Guide page excludes workspace CSS

1. Run `curl -s http://localhost:3000/guide | grep 'stylesheet' | grep -c 'workspace'`
2. **Expected:** 0

### 4. Health page excludes workspace CSS

1. Run `curl -s http://localhost:3000/health/ | grep 'stylesheet' | grep -c 'workspace'`
2. **Expected:** 0

### 5. Dashboard page includes workspace CSS

1. Run `curl -s http://localhost:3000/ | grep 'stylesheet' | grep -E 'workspace|forms\.css|views\.css|settings\.css|vfs-browser' | wc -l`
2. **Expected:** 5 (dashboard inherits the default page_css block)

### 6. Debug pages exclude workspace CSS

1. Run `curl -s http://localhost:3000/debug/commands | grep 'stylesheet' | grep -c 'workspace'`
2. **Expected:** 0

### 7. Import pages exclude workspace CSS

1. Run `curl -s http://localhost:3000/obsidian/import | grep 'stylesheet' | grep -c 'workspace'`
2. **Expected:** 0

### 8. Visual regression check — workspace page

1. Open `http://localhost:3000/browser/` in a browser
2. Check the sidebar (explorer pane), object tabs area, and right panel
3. **Expected:** All workspace UI elements render correctly — sidebar sections expand, explorer shows types, object tabs work. No missing icons, broken layouts, or invisible elements.

### 9. Visual regression check — admin page

1. Open `http://localhost:3000/admin/models` in a browser
2. Check model list, navigation, header
3. **Expected:** Admin page renders correctly with shared CSS (theme.css, style.css). Layout is intact. No broken styles from missing workspace CSS.

### 10. Visual regression check — guide page

1. Open `http://localhost:3000/guide` in a browser
2. Check guide content area
3. **Expected:** Guide page renders correctly. Typography, layout, and button styles intact without workspace CSS.

## Edge Cases

### New template without page_css override

1. Hypothetically, add a new template that extends base.html without overriding `{% block page_css %}`
2. **Expected:** The template inherits all 5 workspace CSS files (safe-by-default). No breakage, just extra CSS loaded. This is intentional — missing CSS breaks pages, extra CSS is harmless.

### Production mode with hashed filenames

1. Run `docker compose build frontend && docker compose up -d` to use production-built assets
2. Run `curl -s http://localhost:3000/admin/models | grep 'stylesheet'`
3. **Expected:** Stylesheet links reference hashed filenames (e.g., `style-abc123.min.css`, `theme-def456.min.css`) but NO workspace-prefixed files appear.

## Failure Signals

- **Admin/guide/health pages load workspace CSS:** A template is missing the empty `{% block page_css %}{% endblock %}` override. Check `grep -rL 'block page_css'` against the 19 expected template files.
- **Workspace page missing CSS / broken layout:** The `{% block page_css %}` wrapper in base.html may be misplaced or the workspace template accidentally overrides the block to empty.
- **Template rendering errors (500):** Jinja2 syntax error in the block tags. Check `{% block page_css %}` is properly opened and closed.

## Requirements Proved By This UAT

- PERF-06 (CSS code-splitting) — Admin pages load only admin-relevant CSS; workspace CSS excluded from non-workspace routes. Network waterfall confirms zero workspace.css requests on admin pages.

## Not Proven By This UAT

- Lighthouse performance improvement from CSS reduction (proven by S05)
- Exact byte savings measurement (cosmetic, not functional)
- CSS loading behavior for `base_embed.html` pages (embed pages have their own template chain)

## Notes for Tester

- In dev mode (volume mounts), CSS filenames are unhashed (e.g., `workspace.css`). In production mode (Docker build), they're hashed (e.g., `workspace-4df1c795.min.css`). Both should show the same code-splitting behavior.
- The `grep` commands work for both modes because the base name prefix is preserved in hashed filenames.
- Auth is required for admin and debug pages — make sure you're logged in or the curl commands include a session cookie.
