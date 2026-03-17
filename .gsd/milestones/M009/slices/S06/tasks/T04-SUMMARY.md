---
id: T04
parent: S06
milestone: M009
provides:
  - Admin detail page renderer assignment display with Active/Default/Overridden status
  - POST /admin/apps/{app_id}/renderers/set endpoint for setting preferred renderer
  - POST /admin/apps/{app_id}/renderers/clear endpoint for clearing renderer preference
  - _build_renderer_assignments() async helper for querying AppRendererPref status per manifest declaration
key_files:
  - backend/app/apps/admin_router.py
  - backend/app/templates/admin/apps/detail.html
  - backend/tests/test_admin_renderers.py
key_decisions:
  - Iterate both read and edit modes per objectRenderer declaration (not just read) to show all available fragments
  - Type label extracted from IRI fragment (last segment after / or #) rather than querying triplestore for rdfs:label
  - Used session.get() with composite PK for direct lookup (matching existing upsert patterns in task_interval_update)
  - MockRendererPrefStore in tests simulates async session with in-memory dict keyed by composite PK
patterns_established:
  - Renderer admin pattern: _build_renderer_assignments() queries pref table inside existing detail session block, builds status list passed to template
  - Admin upsert pattern for AppRendererPref matches AppTaskConfig pattern (get → create or update → commit)
observability_surfaces:
  - Logger app.apps.admin_router at INFO logs renderer pref set/clear with type_iri, mode, app_id, user_id
  - Logger app.apps.admin_router at DEBUG logs no-op clears
  - SELECT * FROM app_renderer_prefs shows active preferences
  - Admin detail page /admin/apps/{app_id} shows real-time Active/Default/Overridden status
duration: 18min
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T04: Admin renderer assignment management

**Replaced renderer placeholder in admin app detail page with real UI showing type/mode/status table with set/clear preference controls backed by AppRendererPref table.**

## What Happened

1. **Extended `app_detail()` endpoint** (`admin_router.py`): Added `_build_renderer_assignments()` async helper that iterates manifest `ui.objectRenderers`, checks both read and edit modes for each, and queries `AppRendererPref` table via `session.get()` with composite PK. Returns list of `{type_iri, type_label, mode, status, active_app_id}` dicts. Added `renderer_assignments` and `has_renderers` to template context.

2. **Added two new POST endpoints**:
   - `POST /admin/apps/{app_id}/renderers/set` — upserts AppRendererPref row (create new or update existing app_id). Validates app exists. Redirects back to detail page.
   - `POST /admin/apps/{app_id}/renderers/clear` — deletes AppRendererPref row if present. Idempotent (no error if row doesn't exist). Redirects back to detail page.
   Both endpoints use `require_role("owner")` and log operations at INFO level.

3. **Replaced template placeholder** (`detail.html`): The "Renderer assignments will appear here when configured" text replaced with a real section. When `has_renderers` is true, renders a data table with Type (shortened IRI), Mode, Status (badge: green Active / yellow Default / red Overridden), and Action (set/clear buttons with htmx POST). When false, shows "This app does not declare any object renderers."

4. **Updated existing test** (`test_app_admin.py`): Changed `test_detail_shows_placeholders` to check for new "Renderer Overrides" heading and "does not declare any object renderers" message instead of old placeholder text.

5. **Wrote 13 tests** (`test_admin_renderers.py`): Covers renderer display (5 tests: info shown, no-renderers message, Active/Overridden/Default status), set endpoint (3 tests: create, upsert, default mode), clear endpoint (2 tests: delete, idempotent), role enforcement (2 tests), placeholder removal (1 test).

## Verification

- `python -m pytest backend/tests/test_admin_renderers.py -v` — 13/13 passed
- `python -m pytest backend/tests/test_app_admin.py -v` — 26/26 passed (updated placeholder assertion)
- `python -m pytest backend/tests/ -x --ignore=backend/tests/test_sdk_integration.py -q` — 1194 passed, zero regressions
- `python -m pytest backend/tests/test_right_pane_sections.py backend/tests/test_app_views_commands.py backend/tests/test_renderer_overrides.py backend/tests/test_admin_renderers.py -v` — 61/61 passed (all S06 slice tests)
- `grep -c "renderer" backend/app/apps/admin_router.py` → 18 (≥5 ✓)
- Renderer placeholder fully replaced — no "coming soon" or "will appear here when configured" in renderer section
- `from app.apps.admin_router import app_admin_router` — importable, 11 routes
- All modified .py files pass `ast.parse()` syntax check

### Slice-level verification status (S06):
- ✅ `test_right_pane_sections.py` — 16 passed (T01)
- ✅ `test_app_views_commands.py` — 13 passed (T02)
- ✅ `test_renderer_overrides.py` — 19 passed (T03)
- ✅ `test_admin_renderers.py` — 13 passed (T04)
- ✅ Full suite — 1194 passed, zero regressions

## Diagnostics

- **Renderer pref management logging:** Logger `app.apps.admin_router` at INFO logs set/clear events with type_iri, mode, app_id, and user_id
- **No-op clear logging:** Logger at DEBUG when clear is called but no row exists
- **Database inspection:** `SELECT * FROM app_renderer_prefs` shows all active preferences
- **Admin page inspection:** Visit `/admin/apps/{app_id}` to see real-time status table with Active/Default/Overridden badges per declared objectRenderer
- **404 protection:** Set endpoint returns 404 for unknown app_id

## Deviations

- Plan specified querying only `mode='read'` per renderer. Implementation iterates both `read` and `edit` modes since AppObjectRenderer can declare both and users should be able to manage preferences for each mode independently. This is more complete.
- Updated `test_app_admin.py::test_detail_shows_placeholders` which checked for old placeholder text — not mentioned in plan but necessary to avoid regression.

## Known Issues

- `test_sdk_integration.py` excluded from full regression run (pre-existing `sempkm_app_sdk` module install issue, not introduced by this task).

## Files Created/Modified

- `backend/app/apps/admin_router.py` — added `AppRendererPref` import, `_build_renderer_assignments()` helper, `renderer_set()` and `renderer_clear()` endpoints, enriched `app_detail()` context
- `backend/app/templates/admin/apps/detail.html` — replaced renderer placeholder with real table UI
- `backend/tests/test_admin_renderers.py` — 13 tests covering display, set, clear, role enforcement, placeholder removal
- `backend/tests/test_app_admin.py` — updated placeholder assertion to match new renderer section
- `.gsd/milestones/M009/slices/S06/tasks/T04-PLAN.md` — added Observability Impact section (pre-flight fix)
