# S06: Frontend Level 2+3 — Workspace Contributions & Renderer Overrides — UAT

**Milestone:** M009
**Written:** 2026-03-17

## UAT Type

- UAT mode: artifact-driven
- Why this mode is sufficient: S06 is a contract-level slice — all integration points tested via 61 pytest contract tests with mocked registry/triplestore. Live runtime proof deferred to S07 which exercises everything through the Docker stack with a real test app.

## Preconditions

- Worktree at `.gsd/worktrees/M009` has the S06 changes applied
- `.venv` in the worktree has all dependencies installed
- No Docker stack required (all tests use mocked services)

## Smoke Test

```bash
cd /home/james/Code/SemPKM/.gsd/worktrees/M009
.venv/bin/python -m pytest backend/tests/test_right_pane_sections.py backend/tests/test_app_views_commands.py backend/tests/test_renderer_overrides.py backend/tests/test_admin_renderers.py -v
```
**Expected:** 61 tests pass, zero failures.

## Test Cases

### 1. Dynamic right pane — platform sections always present

1. Run `test_right_pane_sections.py::TestRightPaneSectionsEndpoint::test_no_apps_returns_platform_sections`
2. **Expected:** Response HTML contains Relations, Lint, and Comments `<details>` blocks with correct hx-get URLs, even with no apps registered.

### 2. Dynamic right pane — app contributions merged by type

1. Run `test_right_pane_sections.py::TestRightPaneSectionsEndpoint::test_matching_app_included`
2. **Expected:** When an app declares rightPane contributions targeting a type, and the object has that type, the app section appears after platform sections.

### 3. Dynamic right pane — type filtering excludes non-matching apps

1. Run `test_right_pane_sections.py::TestRightPaneSectionsEndpoint::test_non_matching_type_excluded`
2. **Expected:** App contributions targeting type A are excluded when viewing an object of type B.

### 4. Dynamic right pane — stopped apps excluded

1. Run `test_right_pane_sections.py::TestRightPaneSectionsEndpoint::test_stopped_app_excluded`
2. **Expected:** Even if a stopped app's manifest declares rightPane contributions, they don't appear.

### 5. Dynamic right pane — graceful degradation on triplestore error

1. Run `test_right_pane_sections.py::TestRightPaneSectionsEndpoint::test_triplestore_error_graceful_degradation`
2. **Expected:** When triplestore query fails, endpoint returns 200 with platform-only sections (no crash, no 500).

### 6. Views explorer shows app view entries

1. Run `test_app_views_commands.py::TestViewsExplorerApps::test_running_app_with_views`
2. **Expected:** HTML response contains tree-leaf entries for the app's declared views with correct onclick handlers.

### 7. Views explorer excludes stopped apps

1. Run `test_app_views_commands.py::TestViewsExplorerApps::test_stopped_app_excluded`
2. **Expected:** Stopped app's views do not appear in the views explorer response.

### 8. App view tab renders with fragment URL

1. Run `test_app_views_commands.py::TestAppViewTab::test_returns_template_with_fragment`
2. **Expected:** Response contains hx-get URL pointing to `/app/{appId}/_fragments/{fragment}`.

### 9. App view tab 404 for unknown app

1. Run `test_app_views_commands.py::TestAppViewTab::test_404_unknown_app`
2. **Expected:** Returns 404 with descriptive detail for unknown app_id.

### 10. Command palette JSON with all action types

1. Run `test_app_views_commands.py::TestCommandsAPI::test_running_app_with_dialog_command`
2. Run `test_app_views_commands.py::TestCommandsAPI::test_post_command_format`
3. Run `test_app_views_commands.py::TestCommandsAPI::test_navigate_command_format`
4. **Expected:** Each returns JSON with correct id (appcmd: prefix), title, section (app name), actionType, and actionUrl.

### 11. Renderer override dispatches to app template

1. Run `test_renderer_overrides.py::TestGetObjectRendererDispatch::test_override_dispatches_to_app_template`
2. **Expected:** When object's type matches an app's objectRenderers declaration, get_object() renders `object_tab_app.html` instead of `object_tab.html`.

### 12. Renderer override — no match falls back to default

1. Run `test_renderer_overrides.py::TestGetObjectRendererDispatch::test_no_override_uses_default_template`
2. **Expected:** When no app declares a renderer for the object's type, standard `object_tab.html` is rendered.

### 13. Renderer override — AppRendererPref wins over registry

1. Run `test_renderer_overrides.py::TestGetRendererOverride::test_pref_overrides_registry_default`
2. **Expected:** When AppRendererPref table has a row for a type, that app's renderer is used regardless of which app the registry would return by default.

### 14. Renderer override — edit fallback to SHACL form

1. Run `test_renderer_overrides.py::TestGetObjectRendererDispatch::test_edit_fallback_when_no_custom_edit`
2. **Expected:** When app declares only a read renderer (no edit), the edit face renders the standard SHACL form.

### 15. Renderer override — embed mode unaffected

1. Run `test_renderer_overrides.py::TestGetObjectRendererDispatch::test_embed_mode_not_affected`
2. **Expected:** With `embed=1`, object always renders `object_embed.html` regardless of renderer overrides.

### 16. Renderer override — error falls back to default

1. Run `test_renderer_overrides.py::TestGetObjectRendererDispatch::test_registry_error_falls_back_to_default`
2. **Expected:** When `_get_renderer_override()` raises an exception, get_object() renders default template (no crash).

### 17. Admin renderer display — shows declared renderers

1. Run `test_admin_renderers.py::TestDetailRendererDisplay::test_detail_shows_renderer_info`
2. **Expected:** Admin detail page shows Renderer Overrides section with type IRI, mode, and status for each declared renderer.

### 18. Admin renderer set — creates preference

1. Run `test_admin_renderers.py::TestRendererSet::test_set_creates_pref_row`
2. **Expected:** POST to set endpoint creates AppRendererPref row in database.

### 19. Admin renderer clear — removes preference

1. Run `test_admin_renderers.py::TestRendererClear::test_clear_removes_pref_row`
2. **Expected:** POST to clear endpoint deletes AppRendererPref row.

### 20. Admin renderer — role enforcement

1. Run `test_admin_renderers.py::TestRendererRoleEnforcement::test_non_owner_gets_403_on_set`
2. **Expected:** Non-owner role gets 403 on renderer set endpoint.

## Edge Cases

### Priority ordering in right pane

1. Run `test_right_pane_sections.py::TestRightPaneSectionsEndpoint::test_multiple_apps_sorted_by_priority`
2. **Expected:** When multiple apps contribute sections, they appear sorted by priority (lower number = higher position).

### Wildcard targetTypes

1. Run `test_right_pane_sections.py::TestRegistryGetRightPaneContributions::test_wildcard_matches_any_type`
2. **Expected:** App contributions with `targetTypes: ["*"]` match any object type.

### Multiple apps with renderers for same type

1. Run `test_renderer_overrides.py::TestRegistryGetRenderer::test_returns_first_match_across_apps`
2. **Expected:** Without a preference, the first registered app's renderer is used.

### Stale preference (pref points to app without that renderer)

1. Run `test_renderer_overrides.py::TestGetRendererOverride::test_stale_pref_falls_back_to_registry`
2. **Expected:** If AppRendererPref points to an app that doesn't actually have a renderer for that type, system falls back to registry default.

### Idempotent clear

1. Run `test_admin_renderers.py::TestRendererClear::test_clear_idempotent`
2. **Expected:** Clearing a preference that doesn't exist doesn't raise an error.

## Failure Signals

- Any of the 61 S06 tests failing indicates a regression
- `loadRightPaneSection` appearing in workspace.js means the old hardcoded pattern leaked back
- `right-pane-dynamic` missing from workspace.html means the dynamic container was reverted
- Missing `apps_api_router` import in main.py would break the `/api/apps/commands` endpoint
- `app-view` case missing from workspace-layout.js would break app view tab rendering

## Requirements Proved By This UAT

- **APP-08** — Contract tests prove right pane sections merge correctly, views explorer includes app entries, command palette returns correct JSON. Runtime proof in S07.
- **APP-09** — Contract tests prove get_object() dispatches to app renderer when type matches, falls back when not, respects preferences. Runtime proof in S07.
- **APP-10** (partial) — Contract tests prove admin detail page shows renderer assignments with working set/clear controls.

## Not Proven By This UAT

- **Live runtime behavior** — All tests use mocked registry, triplestore, and app manager. Real app subprocess serving fragments through the proxy chain is S07's job.
- **Visual rendering** — CSS styles for `.app-renderer-content`, `.app-renderer-loading`, `.object-toolbar-app-badge` not visually verified.
- **ninja-keys integration** — JS `_loadAppCommandEntries()` tested only at contract level (endpoint returns correct JSON). Actual injection into ninja-keys component requires browser runtime.
- **AbortController cancellation** — Tested structurally (old function removed, new function present), but rapid-tab-switching behavior requires live browser testing.

## Notes for Tester

- `test_sdk_integration.py` is excluded from full regression runs due to a pre-existing `sempkm_app_sdk` module import issue — this is not an S06 problem.
- The DeprecationWarning about `TemplateResponse` on S04 endpoints is cosmetic, not a functional issue.
- Command palette app entries only load at workspace init — after installing an app via admin, the page must be reloaded for commands to appear.
