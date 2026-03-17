---
estimated_steps: 6
estimated_files: 1
---

# T01: Write Chapter 29 — App Platform guide page

**Slice:** S08 — User Guide Documentation
**Milestone:** M009

## Description

Write the main documentation chapter for the app platform. This is a ~200-250 line markdown file following the same conventions as existing chapters (e.g., ch. 28 at 170 lines). Two main sections: "Managing Apps" for end users who install/manage apps via the admin portal, and "Building Apps with the SDK" for developers building new apps.

All source material is in the codebase — use the test app (`apps/test-app/`) as the canonical reference example, the SDK source for API accuracy, and the admin templates for workflow descriptions.

## Steps

1. **Read source material** for accurate content:
   - `apps/test-app/manifest.yaml` — complete manifest example (all fields)
   - `apps/test-app/app.py` — SDK usage patterns (routes, tasks, lifecycle)
   - `backend/sdk/sempkm_app_sdk/app.py` — `App` class API (decorators: `on_install`, `on_startup`, `on_shutdown`, `on_uninstall`, `task()`, `route()`)
   - `backend/sdk/sempkm_app_sdk/context.py` — `AppContext` with 5 client properties (`commands`, `graph`, `state`, `settings`, `http`) + `render_template()`
   - `backend/sdk/sempkm_app_sdk/runner.py` — CLI args for reference
   - `backend/app/templates/admin/apps/list.html` — admin list page structure (status indicators, install form)
   - `backend/app/templates/admin/apps/detail.html` — admin detail page structure (actions, task history, permissions)
   - `docs/guide/28-dashboards-and-workflows.md` — chapter style/structure reference

2. **Write `docs/guide/29-app-platform.md`** with this structure:
   ```
   # Chapter 29: App Platform
   
   Intro paragraph (what the app platform is, why it exists)
   
   ## Managing Apps
   ### The Applications Page
   ### Installing an App
   ### App Status and Monitoring
   ### Starting, Stopping, and Restarting
   ### Task Monitoring
   ### Uninstalling an App
   
   ## Building Apps with the SDK
   ### App Directory Structure
   ### The Manifest File (manifest.yaml)
   ### The App Class and Decorators
   ### AppContext and SDK Clients
   ### Fragment Routes and Templates
   ### Task Handlers
   ### Frontend Integration Levels
   #### Level 1: Standalone Pages
   #### Level 2: Workspace Contributions
   #### Level 3: Object Renderer Overrides
   ### Permissions
   
   ## See Also
   
   footer navigation
   ```

3. **Managing Apps section** should cover:
   - Where to find the admin portal (Admin > Applications)
   - How the install form works (disk path, validation)
   - Status indicators: running (green), stopped (gray), error (red)
   - Start/stop/restart buttons on the detail page
   - Task history table (run times, status, duration)
   - Uninstalling — "Remove App" vs. "Remove App + Data" (if UI supports it, otherwise note API-only for data cleanup)

4. **Building Apps section** should cover:
   - Directory structure (manifest.yaml, app.py, requirements.txt, frontend/templates/, frontend/static/)
   - Key manifest fields with brief descriptions (appId, name, version, permissions, backend, tasks, frontend, ui.pages, ui.contributions, ui.objectRenderers) — use test-app manifest as inline example
   - App class: `App("my-app")`, decorators (`@app.route()`, `@app.task()`, `@app.on_startup`, `@app.on_shutdown`, `@app.on_install`, `@app.on_uninstall`)
   - AppContext: 5 clients (commands, graph, state, settings, http) + `render_template()`
   - Fragment routes: how routes serve HTML fragments loaded by htmx
   - Task handlers: decorated function, receives ctx + body, return dict
   - L1/L2/L3 integration levels with brief description of each
   - Permissions: commands whitelist, IRI prefix enforcement, network domain restriction, SPARQL read gate

5. **Style conventions** to match:
   - Use `>` blockquotes for tips
   - Use fenced code blocks with language tags (yaml, python, etc.)
   - Keep descriptions practical, not exhaustive — link to design doc for full spec if needed
   - Footer format: `**Previous:** [Chapter 28: ...](28-...) | **Next:** [Appendix A: ...](appendix-a-...)`

6. **Verify** the file:
   - `wc -l docs/guide/29-app-platform.md` — should be 150-300 lines
   - `grep -c "^#" docs/guide/29-app-platform.md` — multiple heading levels
   - `grep -c "## Managing Apps" docs/guide/29-app-platform.md` — returns 1
   - `grep -c "## Building Apps" docs/guide/29-app-platform.md` — returns 1

## Must-Haves

- [ ] Chapter 29 file exists at `docs/guide/29-app-platform.md`
- [ ] Has H1: "Chapter 29: App Platform"
- [ ] Has H2: "Managing Apps" with subsections for admin page, install, status, start/stop, tasks, uninstall
- [ ] Has H2: "Building Apps with the SDK" with subsections for directory structure, manifest, App class, AppContext, routes, tasks, integration levels, permissions
- [ ] Uses test-app manifest.yaml as an inline example
- [ ] Shows at least one Python code example (App class + decorator pattern)
- [ ] Has footer navigation line (Previous/Next — exact links filled in by T02)

## Verification

- `test -f docs/guide/29-app-platform.md` — file exists
- `grep "## Managing Apps" docs/guide/29-app-platform.md` — section present
- `grep "## Building Apps" docs/guide/29-app-platform.md` — section present
- `grep "manifest.yaml" docs/guide/29-app-platform.md` — manifest referenced
- `grep "AppContext" docs/guide/29-app-platform.md` — SDK context documented
- `wc -l docs/guide/29-app-platform.md` — 150-300 lines

## Inputs

- `apps/test-app/manifest.yaml` — complete manifest for inline example
- `apps/test-app/app.py` — SDK usage patterns for code examples
- `backend/sdk/sempkm_app_sdk/app.py` — App class API for accurate decorator documentation
- `backend/sdk/sempkm_app_sdk/context.py` — AppContext and clients for API reference
- `backend/app/templates/admin/apps/list.html` — admin list page for Managing Apps section
- `backend/app/templates/admin/apps/detail.html` — admin detail page for Managing Apps section
- `docs/guide/28-dashboards-and-workflows.md` — style reference (170 lines, existing chapter format)

## Observability Impact

This task produces a static markdown file — no runtime behavior changes.

- **Inspection surface:** `cat docs/guide/29-app-platform.md` — the deliverable is a single readable file.
- **Failure state:** If the file is missing or empty, all `grep`-based verification commands fail with non-zero exit. A future agent can detect this with `test -s docs/guide/29-app-platform.md`.
- **No runtime signals:** No logs, metrics, or API changes. The chapter is documentation-only.

## Expected Output

- `docs/guide/29-app-platform.md` — ~200-250 line markdown chapter covering app management and SDK development, following existing guide conventions
