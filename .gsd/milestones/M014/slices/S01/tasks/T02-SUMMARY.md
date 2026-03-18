---
id: T02
parent: S01
milestone: M014
provides:
  - extension/ directory structure with Chrome MV3 manifest
  - SemPKMClient class (6 API methods with Bearer auth) in shared/api-client.js
  - Storage wrapper (getSettings, saveSettings, getClient) in shared/storage.js
  - Service worker with context menu registration in background/service-worker.js
  - Placeholder icons (16, 32, 48, 128) and stub popup/options pages
key_files:
  - extension/manifest.json
  - extension/shared/api-client.js
  - extension/shared/storage.js
  - extension/background/service-worker.js
  - extension/assets/icon-16.png
  - extension/assets/icon-32.png
  - extension/assets/icon-48.png
  - extension/assets/icon-128.png
  - extension/popup/popup.html
  - extension/popup/popup.js
  - extension/popup/popup.css
  - extension/options/options.html
  - extension/options/options.js
  - extension/options/options.css
key_decisions:
  - ES modules throughout — manifest uses "type": "module" for service worker, popup/options use <script type="module"> for consistent import/export
  - SemPKMError custom error class carries HTTP status + parsed detail for structured error handling in UI layers
  - storage.js exports getClient() that returns null when unconfigured rather than constructing a broken client
patterns_established:
  - "All extension API calls go through SemPKMClient._request() which attaches Bearer auth and handles errors uniformly"
  - "Use ES module import/export for all extension JS files — no global scripts, no bundler needed"
  - "chrome.storage.sync with fallback to chrome.storage.local via _storageArea() helper"
observability_surfaces:
  - "Service worker console: chrome://extensions → extension → 'Inspect views: service worker' shows menu registration and click logs"
  - "SemPKMError.status and .detail fields surface in catch handlers"
  - "chrome.storage.sync.get(null, console.log) in DevTools shows all persisted settings"
duration: 25m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Extension directory scaffold with manifest, shared modules, and service worker

**Created extension/ directory with Chrome MV3 manifest, SemPKMClient API class (6 methods, Bearer auth), storage wrapper, service worker with context menu registration, placeholder icons, and stub popup/options pages**

## What Happened

Built the complete `extension/` directory structure as the foundation for all subsequent browser extension slices (S02–S05). The manifest is Chrome MV3 with `"type": "module"` for ES module service worker imports. The `SemPKMClient` class in `shared/api-client.js` provides all 6 API methods (`connect`, `getTypes`, `getShape`, `createObject`, `createEdge`, `searchObjects`) — each using `fetch()` with `Authorization: Bearer` header through a shared `_request()` method that parses backend error JSON into descriptive `SemPKMError` exceptions. The `storage.js` module wraps `chrome.storage.sync` with defaults for all 6 settings keys and a `getClient()` factory that returns `null` when unconfigured. The service worker registers a "Save to SemPKM" context menu item on `chrome.runtime.onInstalled` with a click listener shell for S03. Generated indigo placeholder icons (white "S" on #4f46e5 background) at 16/32/48/128px using Pillow. Created minimal stub HTML/JS/CSS for popup and options pages so all manifest references resolve.

## Verification

- **Manifest validation:** JSON parses correctly, manifest_version=3, all referenced files (icons, popup, service worker, options page) exist on disk
- **SemPKMClient methods:** Verified all 6 methods (`connect`, `getTypes`, `getShape`, `createObject`, `createEdge`, `searchObjects`) present as async functions
- **Bearer auth:** Confirmed `Authorization: Bearer` header set in `_headers()` method used by all requests
- **Storage exports:** Confirmed `getSettings`, `saveSettings`, `getClient` all exported as async functions
- **Service worker:** Confirmed `chrome.runtime.onInstalled.addListener`, `chrome.contextMenus.create`, menu ID `save-to-sempkm`, context `selection`
- **Icons:** All 4 sizes exist, validated as correct dimensions and PNG format via Pillow
- **JS syntax:** All 5 JS files pass `node --check` validation
- **Backend regression:** 10/10 bearer auth tests pass, 62/62 API surface tests pass

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python3 manifest_validation.py` (inline) | 0 | ✅ pass | <1s |
| 2 | `node --check extension/shared/api-client.js` | 0 | ✅ pass | <1s |
| 3 | `node --check extension/shared/storage.js` | 0 | ✅ pass | <1s |
| 4 | `node --check extension/background/service-worker.js` | 0 | ✅ pass | <1s |
| 5 | `node --check extension/popup/popup.js` | 0 | ✅ pass | <1s |
| 6 | `node --check extension/options/options.js` | 0 | ✅ pass | <1s |
| 7 | `docker compose exec api python -m pytest tests/test_commands_bearer_auth.py -v` | 0 | ✅ pass (10/10) | 0.82s |
| 8 | `docker compose exec api python -m pytest tests/test_api_surface.py -v` | 0 | ✅ pass (62/62) | 1.72s |

## Diagnostics

- **Service worker console:** `chrome://extensions` → SemPKM Capture → "Inspect views: service worker" — shows `[SemPKM] Context menu "Save to SemPKM" registered` on install and click logs
- **API client errors:** `SemPKMError` carries `.status` (HTTP code) and `.detail` (parsed backend error message) — these surface in popup/options catch handlers
- **Storage inspection:** Run `chrome.storage.sync.get(null, console.log)` in extension DevTools to see all persisted settings
- **Icon verification:** `python3 -c "from PIL import Image; [print(Image.open(f'extension/assets/icon-{s}.png').size) for s in [16,32,48,128]]"`

## Deviations

None — implemented exactly as planned.

## Known Issues

- **Manual Chrome sideload verification deferred:** The extension files are structurally validated (manifest, JS syntax, icon format) but live Chrome sideload testing requires manual interaction at `chrome://extensions`. This is expected — the slice plan calls for manual verification at the end of the full slice.
- **pytest not pre-installed in Docker container:** Had to install pytest/pytest-asyncio into the venv via `ensurepip` before running tests. This is a transient container state issue, not a codebase problem.

## Files Created/Modified

- `extension/manifest.json` — Chrome MV3 manifest with permissions, host_permissions, action, background (module service worker), icons, options_page
- `extension/shared/api-client.js` — SemPKMClient class with 6 API methods + SemPKMError class
- `extension/shared/storage.js` — Settings persistence wrapper (getSettings, saveSettings, getClient)
- `extension/background/service-worker.js` — Context menu registration on install + click listener shell
- `extension/assets/icon-16.png` — 16×16 placeholder icon (indigo #4f46e5 with white "S")
- `extension/assets/icon-32.png` — 32×32 placeholder icon
- `extension/assets/icon-48.png` — 48×48 placeholder icon
- `extension/assets/icon-128.png` — 128×128 placeholder icon
- `extension/popup/popup.html` — Minimal popup HTML shell with module script
- `extension/popup/popup.js` — Popup stub (console.log)
- `extension/popup/popup.css` — Popup stub styles (400px width, centered layout)
- `extension/options/options.html` — Minimal options HTML shell with module script
- `extension/options/options.js` — Options stub (console.log)
- `extension/options/options.css` — Options stub styles (600px centered layout)
- `.gsd/milestones/M014/slices/S01/tasks/T02-PLAN.md` — Added Observability Impact section
