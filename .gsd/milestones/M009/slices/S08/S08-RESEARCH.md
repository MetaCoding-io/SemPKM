# S08: User Guide Documentation — Research

**Date:** 2026-03-17
**Depth:** Light — straightforward documentation following established guide chapter patterns (DOCS-04 precedent from M007/S05).

## Summary

S08 is pure documentation. No code changes, no tests, no Docker work. The deliverable is a new user guide chapter (ch. 29) covering the app platform for both users (installing/managing apps from admin) and developers (building apps with the SDK), plus ~5 glossary entries in appendix-d-glossary.md, and a README.md TOC update.

The pattern is identical to DOCS-04 (M007/S05) which produced ch. 28 (Dashboards and Workflows): a ~150-250 line markdown chapter, glossary additions in alphabetical order, navigation chain updates (ch. 28 → ch. 29 → Appendix A), and README TOC entry. All source material exists in-repo — the design doc (2035 lines), the test app (manifest + app.py), the SDK source, and the admin templates.

## Recommendation

**Three tasks: (1) chapter 29 guide page, (2) glossary entries, (3) README TOC + navigation chain updates.**

The chapter should have two main sections: "Managing Apps" (user-facing — admin portal, install, monitor, uninstall) and "Building Apps" (developer-facing — manifest format, SDK overview, frontend integration levels). The test app (`apps/test-app/`) is the reference implementation to link/cite. Keep it practical — manifest examples, decorator patterns, directory structure — not a repeat of the design doc.

## Implementation Landscape

### Key Files

- `docs/guide/29-app-platform.md` — **New.** Main chapter. User guide for app management + developer guide for SDK.
- `docs/guide/appendix-d-glossary.md` — **Modify.** Add ~5 entries: App Platform, App Manifest, App SDK, App Sandbox, App Contribution. Insert alphabetically.
- `docs/guide/README.md` — **Modify.** Add ch. 29 entry to Part VIII (Discovery and Integration) between ch. 28 and Appendices.
- `docs/guide/28-dashboards-and-workflows.md` — **Modify.** Update footer navigation: `**Next:** [Chapter 29: App Platform](29-app-platform.md)`.
- `docs/guide/appendix-a-environment-variables.md` — No change needed (no new env vars from app platform — token/socket are internal).

### Source Material (read-only references for content)

- `.gsd/design/APP-PLATFORM-DESIGN.md` — §3 (manifest spec), §6 (SDK), §7 (frontend integration), §10 (lifecycle), §11 (admin portal), §15 (disk layout)
- `apps/test-app/manifest.yaml` — Complete manifest example (all UI contribution types)
- `apps/test-app/app.py` — SDK usage example (routes, tasks, lifecycle hooks)
- `backend/sdk/sempkm_app_sdk/app.py` — `App` class API (decorators: `on_install`, `on_startup`, `on_shutdown`, `on_uninstall`, `task()`, `route()`)
- `backend/sdk/sempkm_app_sdk/context.py` — `AppContext` with 5 client properties (`commands`, `graph`, `state`, `settings`, `http`) + `render_template()`
- `backend/sdk/sempkm_app_sdk/runner.py` — CLI args: `--app-dir`, `--socket`, `--platform-url`, `--app-token`
- `backend/sdk/pyproject.toml` — SDK dependencies (fastapi, uvicorn, httpx, PyJWT, jinja2, pyyaml)
- `backend/app/templates/admin/apps/list.html` (121 lines) — Admin list page structure
- `backend/app/templates/admin/apps/detail.html` (331 lines) — Admin detail page structure

### Build Order

1. **Chapter 29** — the main deliverable (~200 lines). Two sections:
   - "Managing Apps" — where to find admin portal, how to install from disk path, what the status indicators mean, how to start/stop/restart, how to uninstall (with/without data), task monitoring
   - "Building Apps with the SDK" — directory structure, manifest.yaml reference (key fields only — link to design doc for full spec), App class decorators, AppContext clients, fragment routes, task handlers, template rendering, frontend integration levels (L1 pages, L2 contributions, L3 renderer overrides)
2. **Glossary entries** — alphabetical insertion of ~5 terms
3. **Navigation updates** — README.md TOC + ch. 28 footer + ch. 29 footer pointing to Appendix A

### Verification Approach

- `ls docs/guide/29-app-platform.md` — file exists
- `grep "App Platform" docs/guide/appendix-d-glossary.md` — glossary entry present
- `grep "29-app-platform" docs/guide/README.md` — TOC entry present
- `grep "29-app-platform" docs/guide/28-dashboards-and-workflows.md` — navigation chain updated
- `grep "Appendix A" docs/guide/29-app-platform.md` — footer points to next
- Chapter has both "Managing Apps" and "Building Apps" H2 sections
- No broken internal links (all referenced chapters exist)

### Chapter Structure (outline for planner)

```
# Chapter 29: App Platform

intro paragraph

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

### Glossary Entries (draft)

- **App Contribution** — A UI element an app contributes to the workspace: right-pane sections, views, command palette entries, or object renderer overrides. Declared in the manifest's `ui.contributions` section. See [Chapter 29: App Platform](29-app-platform.md).
- **App Manifest** — The `manifest.yaml` file in an app's root directory that declares its identity, dependencies, permissions, tasks, frontend assets, and UI contributions. The platform validates the manifest at install time using a Pydantic schema. See [Chapter 29: App Platform](29-app-platform.md).
- **App Platform** — The subsystem that manages third-party and first-party Python applications. Apps run as sandboxed subprocesses communicating with the platform via HTTP over unix domain sockets. See [Chapter 29: App Platform](29-app-platform.md).
- **App Sandbox** — The isolation boundary for each app: a separate Python subprocess with its own virtual environment, communicating with the platform only through a scoped HTTP API. Apps cannot access platform internals directly. See [Chapter 29: App Platform](29-app-platform.md).
- **App SDK** — The `sempkm-app-sdk` Python package that provides the `App` class, `AppContext`, and scoped clients for building SemPKM applications. Installed automatically into each app's virtual environment. See [Chapter 29: App Platform](29-app-platform.md).
