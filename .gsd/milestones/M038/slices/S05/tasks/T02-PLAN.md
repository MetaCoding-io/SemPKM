---
estimated_steps: 5
estimated_files: 5
skills_used:
  - test
---

# T02: App wiring — lifecycle hooks, entry status route, JSON suggestion endpoint, today UI buttons

**Slice:** S05 — Context-Driven Adaptation + Mobile
**Milestone:** M038

## Description

Wire the context subscription service (T01) into the app's lifecycle, add the missing entry status mutation route, provide a JSON endpoint for the mobile app, and add action buttons to the today view so users can mark entries as completed/skipped/saved.

The app currently has placeholder `on_startup`/`on_shutdown` hooks (lines 1781-1790 of `app.py`) that just log. The `current_suggestion_fragment()` (line 1725) returns HTML — the mobile app needs a JSON variant. There are no entry status update routes — the today view shows status badges but users can't change them.

## Steps

1. **Import context_service and wire lifecycle hooks** in `apps/media-scheduler/app.py`:
   - Add importlib fallback block for `context_service` (same pattern as podcast_service, plan_service, etc.) importing `start_context_listener`, `stop_context_listener`, `get_context_subscription_status`.
   - Change `on_startup` to async: `async def on_startup(ctx)` → call `start_context_listener(ctx)` and log.
   - Change `on_shutdown` to async: `async def on_shutdown(ctx)` → call `stop_context_listener()` and log.

2. **Add `POST /_fragments/entry/{entry_iri}/status` route** in `app.py`:
   - Accept `entry_iri` path parameter (URL-encoded IRI) and `status` form field.
   - Validate `status` is one of: `completed`, `skipped`, `saved`. Return 400 otherwise.
   - Call `ctx.commands.execute("object.patch", {"iri": entry_iri, "properties": {f"{MS_NS}entryStatus": status}})`.
   - Return the updated entry as a small HTML fragment (status badge + action buttons) for htmx swap.
   - Use `hx-swap="outerHTML"` targeting the `.ms-entry-actions` container.

3. **Add `GET /_fragments/current-suggestion/json` route** in `app.py`:
   - Reuse the same SPARQL logic from `current_suggestion_fragment()` but extend it: query `sourceType`, `enclosureUrl`, `duration` from the linked `mediaItem`.
   - Return JSON: `{"title", "slot_start", "slot_end", "status" ("now"|"next"|"none"), "source_type", "source_title", "enclosure_url", "duration_seconds"}`.
   - Return `{"status": "none"}` when no current/next entry exists.
   - Set `Content-Type: application/json`.

4. **Add action buttons to `today.html`** entry cards:
   - After the `.ms-entry-status` div, add a `.ms-entry-actions` div with three buttons:
     - ✓ Complete: `hx-post="/app/media-scheduler/_fragments/entry/{{ entry.iri | urlencode }}/status"` with `hx-vals='{"status": "completed"}'`
     - → Skip: same pattern with `"skipped"`
     - ♡ Save: same pattern with `"saved"`
   - Buttons use `hx-target="closest .ms-entry-actions"` and `hx-swap="outerHTML"`.
   - Hide action buttons for entries with status `completed`, `skipped`, or `saved` (show a "done" indicator instead).
   - This requires passing `entry.iri` (the entry IRI from SPARQL) through to the template. Update the today fragment route's SPARQL result processing to include `entry_iri` in each entry dict (it's already in the `?entry` binding).
   - Add CSS for `.ms-entry-actions` buttons in `styles.css`: small icon buttons, inline with entry row.

5. **Add ~25 tests** to `backend/tests/test_media_scheduler.py`:
   - Entry status route: valid status updates (completed, skipped, saved), invalid status returns 400, missing entry_iri handling (~8 tests)
   - JSON suggestion endpoint: returns correct shape, "now" vs "next" status, empty plan returns `{"status": "none"}`, includes source_type and enclosure_url (~8 tests)
   - Lifecycle wiring: on_startup calls start_context_listener, on_shutdown calls stop_context_listener (~4 tests)
   - Template assertions: today.html contains action buttons, buttons use correct htmx attributes, entry.iri is passed through (~5 tests)

## Must-Haves

- [ ] `on_startup` spawns context listener via `start_context_listener(ctx)`
- [ ] `on_shutdown` cancels context listener via `stop_context_listener()`
- [ ] `POST /_fragments/entry/{entry_iri}/status` validates status and calls `object.patch`
- [ ] `GET /_fragments/current-suggestion/json` returns valid JSON with all required fields
- [ ] Today view has action buttons (complete/skip/save) per entry with correct htmx wiring
- [ ] All htmx URLs use `/app/media-scheduler/` proxy prefix
- [ ] 25+ new tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_media_scheduler.py -k "status or suggestion_json or lifecycle_context" -v` — all new tests pass
- `python3 -c "import ast; ast.parse(open('apps/media-scheduler/app.py').read())"` — clean parse
- `grep -q "/_fragments/current-suggestion/json" apps/media-scheduler/app.py` — JSON endpoint present
- `grep -q "/_fragments/entry/" apps/media-scheduler/app.py` — entry status route present
- `grep -q "ms-entry-actions" apps/media-scheduler/frontend/templates/today.html` — action buttons present

## Inputs

- `apps/media-scheduler/services/context_service.py` — T01 output: `start_context_listener()`, `stop_context_listener()`, `get_context_subscription_status()`
- `apps/media-scheduler/app.py` — existing 1790-line app with lifecycle hooks at lines 1781-1790, current_suggestion_fragment at line 1725, TODAY_PLAN_SPARQL at line 1390
- `apps/media-scheduler/frontend/templates/today.html` — existing template with plan entries but no action buttons
- `apps/media-scheduler/frontend/static/styles.css` — existing stylesheet
- `backend/tests/test_media_scheduler.py` — existing test file (~366 tests after T01)

## Expected Output

- `apps/media-scheduler/app.py` — modified: new imports, async lifecycle hooks, 2 new routes (~80 lines added)
- `apps/media-scheduler/frontend/templates/today.html` — modified: action buttons added per entry
- `apps/media-scheduler/frontend/static/styles.css` — modified: `.ms-entry-actions` button styles
- `backend/tests/test_media_scheduler.py` — ~25 new test functions appended
