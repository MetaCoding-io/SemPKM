# S06: Frontend Level 2+3 — Workspace Contributions & Renderer Overrides — UAT

**Milestone:** M009
**Written:** 2026-03-17

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: All 4 tasks deliver backend endpoints + templates + JS wiring tested by 61 unit/integration tests with mocked registry. Live Docker verification deferred to S07 (test app exercising all features). Contract-level correctness is proven by tests; visual/interactive verification needs the test app.

## Preconditions

- Docker stack running (`docker compose up -d`)
- At least one app installed and running (or test app from S07)
- App manifest declares `ui.rightPane`, `ui.views`, `ui.commands`, and `ui.objectRenderers` sections

## Smoke Test

Navigate to the workspace, open any object tab, and verify the right pane loads via the dynamic endpoint (Network tab shows `GET /browser/apps/right-pane-sections?iri=...` instead of 3 separate section requests).

## Test Cases

### 1. Dynamic right pane loads platform sections for any object

1. Open an object tab in the workspace
2. Observe the right pane area
3. Open browser Network tab and check requests
4. **Expected:** Single request to `/browser/apps/right-pane-sections?iri=<object-iri>` returns HTML with Relations, Lint, and Comments `<details>` sections. Each section has `hx-get` for lazy content loading.

### 2. Right pane includes app contributions when app matches object type

1. Install an app that declares a `rightPane` contribution with `targetTypes` matching an existing object's type
2. Open an object of that type
3. **Expected:** Right pane shows the 3 platform sections (Relations, Lint, Comments) followed by the app's `<details>` section with an app badge. The app section has `hx-get="/app/{appId}/_fragments/{fragment}?iri=<object-iri>"`.

### 3. Right pane excludes app contributions for non-matching types

1. With the same app installed (targeting specific types), open an object of a different type
2. **Expected:** Right pane shows only the 3 platform sections. No app contribution sections appear.

### 4. Right pane wildcard contributions appear for all objects

1. Install an app with `targetTypes: ["*"]` in its rightPane contribution
2. Open any object
3. **Expected:** The app's right pane section appears regardless of the object's type.

### 5. Rapid tab switching cancels stale right pane requests

1. Click rapidly between 3-4 different object tabs
2. Open Network tab
3. **Expected:** Only the last request completes successfully; earlier requests are cancelled (status shows "cancelled" in DevTools). No stale section content from previous objects appears.

### 6. Views explorer shows app view entries

1. Install an app that declares `ui.views` with at least one view
2. Open the Views section in the explorer sidebar
3. **Expected:** App views appear as clickable entries. Entries show the app view label.

### 7. Clicking an app view opens a workspace tab

1. Click an app view entry in the Views explorer
2. **Expected:** A new workspace tab opens with the app view content loaded via htmx from `/app/{appId}/_fragments/{fragment}`. Tab title matches the view label. Tab key follows `app-view:{appId}:{viewId}` pattern.

### 8. Command palette includes app commands

1. Install an app that declares `ui.commands` with at least one command
2. Open the command palette (Ctrl+K or Cmd+K)
3. Type part of the app command's title
4. **Expected:** App command appears in search results with the app name as section header and correct icon.

### 9. Command palette dialog command opens modal

1. Select an app command with `actionType: "dialog"` from the command palette
2. **Expected:** An htmx GET request fetches the command's fragment URL and displays the result in a modal dialog.

### 10. Object renderer override replaces default SHACL form

1. Install an app that declares `ui.objectRenderers` for a specific type with a read fragment
2. Open an object of that type
3. **Expected:** The object tab renders `object_tab_app.html` instead of `object_tab.html`. The read face shows content loaded via htmx from `/app/{appId}/_fragments/{readFragment}?iri=<object-iri>`. Toolbar (label, type badge, favorite star, mode toggle) is preserved.

### 11. Renderer override edit face falls back to SHACL form

1. With the same app (declares read renderer only, no edit renderer), click the mode toggle to switch to edit mode
2. **Expected:** The edit face shows the standard SHACL form + body editor, not an app fragment. The flip animation works correctly.

### 12. Renderer override with custom edit renderer

1. Install an app that declares both read and edit fragments in `objectRenderers`
2. Open an object of the matching type and toggle to edit mode
3. **Expected:** Edit face loads the app's edit fragment via htmx, not the SHACL form.

### 13. Admin detail page shows renderer assignments

1. Navigate to `/admin/apps/{app_id}` for an app with declared renderers
2. Scroll to the Renderer Overrides section
3. **Expected:** Table shows Type IRI, Mode, Status (Active/Default), and Action buttons. Status uses color-coded badges.

### 14. Admin set/clear renderer preference

1. On the admin detail page, click "Set as preferred" for a renderer type
2. **Expected:** Status badge changes to "Active" (green). `app_renderer_prefs` table has a new row.
3. Click "Clear preference"
4. **Expected:** Status badge changes to "Default" (yellow). Row removed from `app_renderer_prefs`.

### 15. Renderer conflict resolution via AppRendererPref

1. Install two apps that both declare renderers for the same type
2. Open an object of that type
3. **Expected:** First-match-wins (registry iteration order). 
4. In admin, set App B as preferred for that type
5. Reopen the object
6. **Expected:** App B's renderer is used instead of App A's.

## Edge Cases

### Right pane with no apps installed

1. Ensure no apps are installed/running
2. Open any object tab
3. **Expected:** Right pane shows exactly the 3 platform sections (Relations, Lint, Comments). No errors. Behavior identical to pre-S06 workspace.

### Right pane with unknown/deleted IRI

1. Navigate to `GET /browser/apps/right-pane-sections?iri=http://nonexistent/iri` directly
2. **Expected:** Returns 200 with platform sections only (graceful degradation). No 404 or 500.

### Command palette with no apps running

1. Ensure no apps are running
2. Open command palette
3. **Expected:** Only platform commands appear. No errors in console. Fetch to `/api/apps/commands` returns `[]`.

### Stopped app excluded from all integration points

1. Stop an app that has views, commands, and right pane contributions
2. Verify: Views explorer no longer shows its entries, command palette no longer shows its commands, right pane no longer shows its sections
3. **Expected:** All contribution points respect app running status.

### Renderer override graceful degradation

1. Simulate a registry error (e.g., corrupt manifest in registry)
2. Open an object whose type would match the broken renderer
3. **Expected:** Standard SHACL form renders (object_tab.html). WARNING logged in `app.browser.objects`. No user-visible error.

## Failure Signals

- Right pane shows 3 separate requests to `/browser/relations/`, `/browser/lint/`, `/browser/comments/` instead of single `/browser/apps/right-pane-sections` → dynamic endpoint not wired
- Network tab shows stale right pane requests completing after tab switch → AbortController not working
- Command palette missing app entries after palette opened → fetch to `/api/apps/commands` failing (check console)
- Object with renderer override shows SHACL form instead of app fragment → check `app.browser.objects` logger for override lookup details
- Admin renderer section still shows "coming soon" placeholder → template not updated
- `focus` jumps to `select#explorer-mode-select` after clicking app view → selector miss (see CLAUDE.md browser click targeting rules)

## Requirements Proved By This UAT

- **APP-08** — Right pane sections, views explorer, and command palette all include app contributions when apps are running and exclude them when stopped
- **APP-09** — Object renderer override dispatch, template loading, conflict resolution, and SHACL fallback all verified
- **APP-10** (partial) — Admin renderer assignment section with set/clear controls and status display

## Not Proven By This UAT

- Live app fragment content rendering (requires a real app serving fragments — deferred to S07 test app)
- Visual correctness of app content within platform chrome (requires browser verification with real app)
- Command palette action dispatch (dialog/post/navigate) with real app endpoints
- Cross-browser CSS 3D flip card animation with app renderer content
- App CSS/JS isolation when multiple apps contribute to the same page

## Notes for Tester

- Test cases 2-15 require an installed app with appropriate manifest sections. S07's test app will provide this — until then, mock data in tests proves the contract.
- The `test_sdk_integration.py` failure is pre-existing (missing `sempkm_app_sdk` module) and unrelated to S06.
- The deprecated `TemplateResponse` ordering warning on `apps_explorer` is pre-existing cosmetic debt.
- Right pane content relies on `htmx.process()` being called after innerHTML swap — if htmx is not loaded (broken CDN), sections will render but lazy-load triggers won't fire.
