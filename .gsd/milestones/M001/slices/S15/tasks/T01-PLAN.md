# T01: 15-settings-system-and-node-type-icons 01

**Slice:** S15 — **Milestone:** M001

## Description

Build the settings infrastructure layer: database model, service, FastAPI endpoints, client JS module, and workspace keyboard/tab integration. This plan establishes the full settings pipeline — from layered resolution to DOM event dispatch — with dark mode as the sole initial registered setting.

Purpose: Every other settings consumer (Phase 17 LLM config, future features) depends on this infrastructure. Phase 15-02 builds the UI on top of this foundation.
Output: Working settings API, client settings cache, Ctrl+, shortcut that opens a settings tab, and manifest schema extended for model-contributed settings and icons.

## Must-Haves

- [ ] "GET /browser/settings/data returns a JSON dict of resolved setting keys to values for the current user"
- [ ] "PUT /browser/settings/{key} upserts a user_settings row and returns the key/value"
- [ ] "DELETE /browser/settings/{key} removes a user override and returns the resolved default"
- [ ] "GET /browser/settings renders the settings_page.html template (even if minimal stub)"
- [ ] "Ctrl+, in workspace opens a 'special:settings' tab in the active editor group"
- [ ] "User menu Settings link opens the settings tab (no longer .disabled)"
- [ ] "ManifestSchema accepts optional settings and icons fields without breaking existing manifest parsing"
- [ ] "SettingsService resolves layered order: system defaults < model manifest defaults < user DB overrides"

## Files

- `backend/app/auth/models.py`
- `backend/migrations/versions/002_user_settings.py`
- `backend/app/services/settings.py`
- `backend/app/models/manifest.py`
- `backend/app/browser/router.py`
- `frontend/static/js/settings.js`
- `frontend/static/js/workspace.js`
- `frontend/static/js/workspace-layout.js`
- `backend/app/templates/components/_sidebar.html`
