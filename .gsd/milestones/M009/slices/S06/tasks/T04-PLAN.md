---
estimated_steps: 6
estimated_files: 3
---

# T04: Admin renderer assignment management

**Slice:** S06 — Frontend Level 2+3 — Workspace Contributions & Renderer Overrides
**Milestone:** M009

## Description

Replace the placeholder renderer assignment section in the admin app detail page with a real UI showing which types each app renders, current assignment status (active/overridden/default), and set/clear controls. This completes APP-10's supporting role for S06 — admin visibility into renderer assignments. The `AppRendererPref` table (created in S01 migration) is already used by T03's dispatch logic; this task provides the admin UI to manage those preferences.

## Steps

1. **Extend `app_detail()` endpoint** in `backend/app/apps/admin_router.py`:
   - After loading the app manifest, collect renderer declarations from `manifest.ui.objectRenderers` (may be empty list or None).
   - For each declared renderer, query `AppRendererPref` table for a row matching `(type_iri=renderer.type, mode='read')`:
     - If row exists and `app_id == current_app_id` → status is "active" (this app is the preferred renderer)
     - If row exists and `app_id != current_app_id` → status is "overridden" (another app is preferred), include `active_app_id`
     - If no row exists → status is "default" (no explicit preference; registry order determines)
   - Build list of `{ type_iri, type_label, mode, status, active_app_id }` dicts.
   - Pass as `renderer_assignments` to template context.
   - Also pass a boolean `has_renderers` for template conditional display.

2. **Add `POST /admin/apps/{app_id}/renderers/set` endpoint** in `admin_router.py`:
   - Accepts form params: `type_iri` (str), `mode` (str, default 'read').
   - Validates the app exists and is installed.
   - Upsert `AppRendererPref` row: `type_iri`, `mode`, `app_id`. Use SQLAlchemy merge or delete-then-insert pattern (check which pattern the codebase uses for upserts — S05's admin endpoints used an upsert pattern for `AppTaskConfig`).
   - Commit.
   - Return htmx fragment: re-render the renderer section partial (or redirect to detail with `HX-Refresh`).
   - Use `require_role("owner")` decorator matching existing admin endpoints.

3. **Add `POST /admin/apps/{app_id}/renderers/clear` endpoint** in `admin_router.py`:
   - Accepts form params: `type_iri` (str), `mode` (str, default 'read').
   - Delete `AppRendererPref` row matching `(type_iri, mode)`.
   - Commit.
   - Return htmx fragment: re-render renderer section or `HX-Refresh`.
   - Handle case where no row exists (idempotent — just return success).

4. **Replace placeholder in `detail.html`** (`backend/app/templates/admin/apps/detail.html`):
   - Find the placeholder at ~line 273 (text like "Renderer assignments coming soon" or similar).
   - Replace with a renderer assignments section:
     - Section heading: "Renderer Overrides" (or "Object Renderers")
     - If `not has_renderers`: show "This app does not declare any object renderers."
     - If `has_renderers`: render a table with columns: Type, Mode, Status, Action.
       - Type: `renderer.type_iri` (or a shortened/labeled version)
       - Mode: `read` / `edit`
       - Status: badge — green "Active" / yellow "Default" / red "Overridden by {app_id}"
       - Action: 
         - If status is "default" or "overridden": button "Set as preferred" → `hx-post="/admin/apps/{app_id}/renderers/set"` with hidden inputs for type_iri and mode
         - If status is "active": button "Clear preference" → `hx-post="/admin/apps/{app_id}/renderers/clear"` with hidden inputs
     - Use htmx `hx-target` and `hx-swap` for inline updates (or `hx-on::after-request` with page refresh for simplicity).
   - Match existing admin detail page styling (card sections, tables, badges).

5. **Write tests** in `backend/tests/test_admin_renderers.py`:
   - Test: detail page shows renderer info when app has objectRenderers declared
   - Test: detail page shows "no renderers" message when app has no objectRenderers
   - Test: set endpoint creates `AppRendererPref` row
   - Test: set endpoint updates existing `AppRendererPref` row (upsert)
   - Test: clear endpoint removes `AppRendererPref` row
   - Test: clear endpoint is idempotent (no row to delete → still succeeds)
   - Test: detail page shows "Active" status when this app is preferred
   - Test: detail page shows "Overridden" status when another app is preferred
   - Use test pattern from `test_app_admin.py`: FastAPI TestClient with `dependency_overrides[get_current_user]` returning mock owner user, mock app_registry/app_manager on app.state.

6. **Verify no regressions**: `python -m pytest backend/tests/ -x --timeout=30`

## Must-Haves

- [ ] Admin detail page shows renderer declarations with accurate status (active/default/overridden)
- [ ] Set endpoint creates/updates `AppRendererPref` row correctly
- [ ] Clear endpoint removes `AppRendererPref` row (idempotent)
- [ ] Placeholder in detail.html fully replaced with real renderer section
- [ ] Tests covering: renderer display, set, clear, upsert, idempotent clear, status states

## Verification

- `cd /home/james/Code/SemPKM/.gsd/worktrees/M009 && python -m pytest backend/tests/test_admin_renderers.py -v` — all tests pass
- `cd /home/james/Code/SemPKM/.gsd/worktrees/M009 && python -m pytest backend/tests/ -x --timeout=30` — zero regressions
- `grep -c "renderer" backend/app/apps/admin_router.py` → ≥5 (endpoints + logic)
- `grep -c "coming soon\|placeholder\|TODO" backend/app/templates/admin/apps/detail.html` → 0 for renderer section

## Inputs

- `backend/app/apps/admin_router.py` — `app_detail()` at ~line 120. S05 added task management endpoints and enriched the detail context. New renderer endpoints and context go here.
- `backend/app/templates/admin/apps/detail.html` — placeholder at ~line 273 for renderer assignments. S05 added task history section. Renderer section replaces the placeholder.
- `backend/app/apps/models.py` — `AppRendererPref` model with composite PK `(type_iri, mode)` and `app_id` column. Created in S01 migration.
- `backend/tests/test_app_admin.py` — reference test pattern for admin endpoints (mock user override, app.state mocks).
- T03's `AppRegistry.get_renderer()` and `_get_renderer_override()` — these use `AppRendererPref` for dispatch. The admin endpoints here manage the same table.

## Expected Output

- `backend/app/apps/admin_router.py` — enriched `app_detail()` context + 2 new endpoints (set, clear)
- `backend/app/templates/admin/apps/detail.html` — real renderer section replacing placeholder
- `backend/tests/test_admin_renderers.py` — ≥8 tests covering all renderer admin scenarios

## Observability Impact

- **New log signals:** Logger `app.apps.admin_router` at INFO logs renderer preference set/clear events with type_iri, mode, app_id, and user_id. DEBUG level logs no-op clears (when row doesn't exist).
- **Inspection surface:** `SELECT * FROM app_renderer_prefs` shows all active renderer preferences. Admin detail page at `/admin/apps/{app_id}` shows real-time status (Active/Default/Overridden) for each declared objectRenderer.
- **Failure visibility:** Set endpoint returns 404 if app not found. Clear endpoint is idempotent — always succeeds. Template shows "Overridden by {app_id}" when another app holds the preference.
- **Admin audit trail:** All set/clear operations logged with user_id for accountability.
