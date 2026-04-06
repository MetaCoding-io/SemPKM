---
id: T01
parent: S01
milestone: M051
key_files:
  - frontend/static/js/dropdown-dismiss.js
  - backend/app/templates/base.html
key_decisions:
  - Used mousedown instead of click for dismiss — fires before focus shift so dropdown clears before click target receives focus
  - Guard checks .suggestions-dropdown, .reference-field, and .tag-autocomplete-field to avoid false dismissals on legitimate interactions
duration: 
verification_result: passed
completed_at: 2026-04-06T00:46:48.218Z
blocker_discovered: false
---

# T01: Created dropdown-dismiss.js with document-level mousedown and Escape handlers that dismiss all open .suggestions-dropdown elements on click-outside or Escape key

**Created dropdown-dismiss.js with document-level mousedown and Escape handlers that dismiss all open .suggestions-dropdown elements on click-outside or Escape key**

## What Happened

Created `frontend/static/js/dropdown-dismiss.js` as an IIFE with two document-level listeners: (1) mousedown — dismisses all non-empty `.suggestions-dropdown` elements when click target is outside `.suggestions-dropdown`, `.reference-field`, and `.tag-autocomplete-field` wrappers; (2) keydown Escape — clears all open dropdowns without preventDefault so Escape still bubbles for modals. Exports `SemPKM.dismissAllDropdowns` for programmatic use. Added script tag to `base.html` between `column-prefs.js` and `sempkm-shims.js`.

## Verification

Verified all 6 behavior scenarios in-browser: click-outside dismiss for reference and tag fields, Escape dismiss for both, suggestion selection still works (mousedown guard recognizes click inside .suggestions-dropdown), and htmx re-population works after dismiss. File-level checks: rg confirms export and script tag, node syntax check passes, HTTP 200 from nginx.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `rg 'dismissAllDropdowns' frontend/static/js/dropdown-dismiss.js` | 0 | ✅ pass | 100ms |
| 2 | `rg 'dropdown-dismiss' backend/app/templates/base.html` | 0 | ✅ pass | 100ms |
| 3 | `node -c frontend/static/js/dropdown-dismiss.js` | 0 | ✅ pass | 200ms |
| 4 | `curl -s -o /dev/null -w '%{http_code}' http://localhost:3901/js/dropdown-dismiss.js` | 0 | ✅ pass | 300ms |
| 5 | `Browser: click-outside + Escape dismiss for reference and tag fields; suggestion selection; htmx re-population` | 0 | ✅ pass | 15000ms |

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/js/dropdown-dismiss.js`
- `backend/app/templates/base.html`
