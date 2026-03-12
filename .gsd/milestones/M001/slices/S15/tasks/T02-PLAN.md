# T02: 15-settings-system-and-node-type-icons 02

**Slice:** S15 — **Milestone:** M001

## Description

Build the full Settings page UI with a two-column VS Code-style layout, in-place search filter, all four input types, Modified indicators, per-setting and per-category reset, and wire dark mode as the first real settings consumer.

Purpose: SETT-01 requires a working settings UI with search and current values. SETT-03 requires that changes dispatch the sempkm:setting-changed event. This plan delivers the complete visual and behavioral layer on top of the infrastructure from Plan 15-01.
Output: A fully functional Settings page that users can navigate, change settings, and see immediate effect (dark mode toggle), plus the settings.css stylesheet.

## Must-Haves

- [ ] "Settings page renders with a two-column layout: category sidebar on the left, settings panel on the right"
- [ ] "Clicking a category in the sidebar switches the right panel to that category's settings"
- [ ] "Typing in the search bar hides non-matching settings rows; categories with all hidden rows collapse from the sidebar"
- [ ] "The core.theme setting renders as a select dropdown with options light/dark/system"
- [ ] "Changing the theme dropdown triggers sempkm:setting-changed immediately (no Save button)"
- [ ] "Settings modified from their default show a 'Modified' badge and a Reset button for that setting"
- [ ] "Reset button reverts the setting to its default and removes the Modified badge"
- [ ] "A Reset all to defaults button per category resets all overrides in that category"
- [ ] "Dark mode responds to sempkm:setting-changed with key='core.theme' by calling setTheme()"
- [ ] "Ctrl+, opens the Settings tab from any page (inherited from Plan 15-01)"

## Files

- `backend/app/templates/browser/settings_page.html`
- `backend/app/templates/browser/_setting_input.html`
- `frontend/static/css/settings.css`
- `backend/app/templates/base.html`
- `frontend/static/js/theme.js`
