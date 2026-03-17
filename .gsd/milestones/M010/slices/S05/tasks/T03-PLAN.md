---
estimated_steps: 7
estimated_files: 5
---

# T03: Add settings manifest declarations, route, template, and tests

**Slice:** S05 — OPML import + app settings
**Milestone:** M010

## Description

Add user-configurable app settings to the RSS Reader. The platform's `AppSettingDef` manifest schema and the SDK's `SettingsClient` already provide the infrastructure — this task declares settings in the manifest, creates a settings page template, and wires GET/POST routes for reading and writing settings.

Two settings are defined:
- `articlesPerPage` (number, default "50") — how many articles to show per feed page
- `markReadOnOpen` (toggle, default "true") — whether opening an article marks it as read

Poll interval is intentionally NOT an app setting — it's already configurable via the admin UI's task configuration (`configurable: true` on the poll-feeds task in the manifest).

## Steps

1. **Add settings declarations to `apps/rss-reader/manifest.yaml`**:
   - Add `settings: true` under `permissions:` (alongside existing `commands`, `sparql`, `backgroundTasks`, `network`)
   - Add top-level `settings:` array with two entries:
     ```yaml
     settings:
       - key: "articlesPerPage"
         label: "Articles per page"
         description: "Number of articles shown per feed page"
         inputType: "number"
         default: "50"
       - key: "markReadOnOpen"
         label: "Mark read on open"
         description: "Automatically mark articles as read when opened"
         inputType: "toggle"
         default: "true"
     ```
   - Validate the manifest still parses: `cd backend && .venv/bin/python -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('../apps/rss-reader/manifest.yaml'); print(f'Settings: {len(m.settings)}')" `

2. **Create GET `/_fragments/settings` route** in `app.py`:
   - Read current values via `ctx.settings.get("articlesPerPage")` and `ctx.settings.get("markReadOnOpen")`
   - If a value is None, use the default from the manifest (hardcode defaults: `"50"` and `"true"`)
   - Render `settings.html` with template context: `{"articles_per_page": value, "mark_read_on_open": value}`

3. **Create POST `/_fragments/settings` route** in `app.py`:
   - Read form values: `form = await request.form()`
   - `articles_per_page = form.get("articlesPerPage", "50")` — validate it's a positive integer string, clamp to range 10-200
   - `mark_read_on_open = "true" if form.get("markReadOnOpen") else "false"` — checkboxes send value only when checked
   - Save via `await ctx.settings.set("articlesPerPage", articles_per_page)` and `await ctx.settings.set("markReadOnOpen", mark_read_on_open)`
   - Return success HTML fragment: `<div class="rss-success">Settings saved</div>`

4. **Create `apps/rss-reader/frontend/templates/settings.html`**:
   ```html
   <div id="rss-settings" class="rss-subscribe-form">
     <h3>Reader Settings</h3>
     <form hx-post="/_fragments/settings"
           hx-target="#settings-result"
           hx-swap="innerHTML">
       <div class="form-group">
         <label for="articles-per-page">Articles per page</label>
         <input type="number" id="articles-per-page" name="articlesPerPage"
                value="{{ articles_per_page }}" min="10" max="200" class="form-input">
       </div>
       <div class="form-group">
         <label for="mark-read-on-open">
           <input type="checkbox" id="mark-read-on-open" name="markReadOnOpen"
                  {% if mark_read_on_open == "true" %}checked{% endif %}>
           Mark articles as read when opened
         </label>
       </div>
       <div class="form-actions">
         <button type="submit" class="btn btn-primary">Save Settings</button>
       </div>
     </form>
     <div id="settings-result"></div>
     <p class="rss-settings-note">
       Poll interval is configured in Admin &gt; Applications &gt; RSS Reader.
     </p>
   </div>
   ```

5. **Add settings gear button to `feed-sidebar.html`** — add to the sidebar header area (`.rss-feed-sidebar-header`):
   ```html
   <div class="rss-feed-sidebar-header">
     <h3>Feeds</h3>
     <button class="rss-sidebar-icon-btn"
             hx-get="/_fragments/settings"
             hx-target="#rss-reading-pane"
             hx-swap="innerHTML"
             title="Reader Settings">
       <i data-lucide="settings"></i>
     </button>
   </div>
   ```
   This replaces the existing simple `<h3>Feeds</h3>` header. Make the header a flex row with the title and gear icon.

6. **Create `backend/tests/test_rss_settings.py`** with ≥8 tests:
   - Use mock ctx pattern: mock `ctx.settings` as an object with `get` (AsyncMock returning None or a value) and `set` (AsyncMock).
   - Import app module via `importlib.util.spec_from_file_location` pattern.
   - Test cases:
     - Manifest validates with settings declared (parse manifest, check `len(settings) == 2`)
     - Manifest settings have correct keys, labels, inputTypes, defaults
     - GET settings returns defaults when ctx.settings.get returns None
     - GET settings returns saved values when ctx.settings.get returns a value
     - POST settings calls ctx.settings.set with correct key/value pairs
     - POST settings with markReadOnOpen unchecked → saves "false"
     - POST settings with markReadOnOpen checked → saves "true"
     - POST settings validates articlesPerPage is reasonable (not negative, not over 200)
   - **Alternative approach (simpler):** Extract the settings logic into testable helper functions (e.g., `get_settings_context(ctx)` and `save_settings(ctx, form_data)`) and test those directly.

7. **Verify everything:**
   ```bash
   cd backend && .venv/bin/python -m pytest tests/test_rss_settings.py -v
   cd backend && .venv/bin/python -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('../apps/rss-reader/manifest.yaml'); print(f'OK: {len(m.settings)} settings, permissions.settings={m.permissions.settings}')"
   python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"
   cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py tests/test_opml_import.py -v
   ```

## Must-Haves

- [ ] Manifest declares `permissions.settings: true` and 2 settings (articlesPerPage, markReadOnOpen)
- [ ] Manifest still validates via `parse_app_manifest()`
- [ ] GET `/_fragments/settings` returns form with current or default values
- [ ] POST `/_fragments/settings` saves values via `ctx.settings.set()`
- [ ] Settings template renders number input and checkbox correctly
- [ ] Gear icon in feed sidebar header opens settings page
- [ ] ≥8 settings tests pass
- [ ] Zero regressions in all existing test suites

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rss_settings.py -v` — ≥8 tests pass
- `cd backend && .venv/bin/python -c "from app.apps.manifest import parse_app_manifest; parse_app_manifest('../apps/rss-reader/manifest.yaml')"` — no error
- `python3 -c "import ast; ast.parse(open('apps/rss-reader/app.py').read())"` — syntax OK
- `cd backend && .venv/bin/python -m pytest tests/test_rss_feed_parser.py tests/test_feed_service.py tests/test_opml_import.py -v` — zero regressions

## Inputs

- `apps/rss-reader/manifest.yaml` — current manifest without settings declarations
- `backend/app/apps/manifest.py` — `AppSettingDef` schema (key pattern: `^[a-zA-Z][a-zA-Z0-9]*$`, inputTypes: text/password/toggle/select/number, `validate_settings_permission` cross-validator)
- `backend/sdk/sempkm_app_sdk/clients/settings.py` — `SettingsClient.get(key) -> str|None`, `SettingsClient.set(key, value)` — keys auto-prefixed with `settings:`
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — current sidebar template to add gear icon
- `apps/rss-reader/frontend/templates/subscribe-dialog.html` — reference for form styling patterns
- `backend/tests/test_feed_service.py` — reference for mock ctx patterns

## Observability Impact

- **Settings round-trip:** GET `/_fragments/settings` returns current values in form field `value` attributes — inspectable without JS. POST returns `<div class="rss-success">Settings saved</div>` or `<div class="rss-error">` with descriptive text.
- **Manifest validation:** `parse_app_manifest()` raises `ValidationError` if `permissions.settings` is false but settings are declared — the `validate_settings_permission` cross-validator catches misconfigurations at manifest load time.
- **Settings persistence:** Values saved via `ctx.settings.set(key, value)` are auto-prefixed with `settings:` in the state graph. Read back via `ctx.settings.get(key)` — returns `None` when unset, triggering default fallback in the route handler.
- **Logger:** Settings route errors are logged via `logger.warning("Settings error: ...")` — check app logs for `Settings` prefix.
- **Failure visibility:** Invalid articlesPerPage (non-integer, out of range) is clamped to 10-200 range and saved. All error paths return `<div class="rss-error">` with descriptive text.

## Expected Output

- `apps/rss-reader/manifest.yaml` — modified with `permissions.settings: true` + 2 settings definitions
- `apps/rss-reader/app.py` — modified with GET/POST settings routes
- `apps/rss-reader/frontend/templates/settings.html` — new settings form template
- `apps/rss-reader/frontend/templates/feed-sidebar.html` — modified with gear icon in header
- `backend/tests/test_rss_settings.py` — new test file with ≥8 tests
