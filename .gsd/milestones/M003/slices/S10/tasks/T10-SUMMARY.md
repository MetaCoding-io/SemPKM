---
id: T10
parent: S10
milestone: M003
provides:
  - e2e test for markdown rendering fidelity (headers, bold, code, links, lists) and XSS sanitization (script tags, event handlers stripped by DOMPurify)
  - e2e test for column visibility preferences persistence via ColumnPrefs API and localStorage
  - e2e test for sidebar panel drag-drop reorder position persistence via localStorage key sempkm_panel_positions
  - e2e test for user guide docs navigation (API endpoints + UI tab with link click-through)
key_files:
  - e2e/tests/01-objects/markdown-rendering.spec.ts
  - e2e/tests/02-views/column-preferences.spec.ts
  - e2e/tests/03-navigation/sidebar-panel-reorder.spec.ts
  - e2e/tests/06-settings/docs-navigation.spec.ts
key_decisions:
  - Markdown body is stored via urn:sempkm:body predicate (not dcterms:description) — the read view renders it client-side using renderMarkdownBody() with marked.js + DOMPurify; XSS checks must target .markdown-body not .object-tab (which has legitimate app scripts)
  - Consolidated all 4 test files to 1 test() each (4 total magic links) to fit within the 5/minute rate limit when run together
patterns_established:
  - For markdown rendering e2e tests, use waitForFunction to wait for .markdown-body to have rendered elements (h1/h2/strong/pre) since rendering is async client-side
  - Column preferences use ColumnPrefs API (window.ColumnPrefs) with localStorage key prefix "col-prefs:" — tests verify via the API then raw localStorage
  - Panel positions use localStorage key "sempkm_panel_positions" with {panelName: {zone, order}} format — tests set positions, reload, and verify persistence
observability_surfaces:
  - none
duration: 45m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T10: Markdown rendering, column prefs, sidebar reorder, docs navigation tests

**Rewrote 4 pre-existing broken test files into 4 working test functions covering markdown rendering fidelity with XSS sanitization, column preferences persistence, sidebar panel reorder persistence, and docs navigation — all passing.**

## What Happened

The 4 pre-existing test files had 14 individual test() calls total, which exceeded the 5/minute magic-link rate limit and had incorrect assumptions (e.g., storing markdown body in dcterms:description instead of urn:sempkm:body, checking XSS on the whole .object-tab instead of .markdown-body). Rewrote all files to consolidate into 1 test() each (4 total) with correct test logic.

Key fixes per file:
- **markdown-rendering**: Body must be stored via `urn:sempkm:body` predicate for the read view to render it. XSS sanitization checks target the `.markdown-body` container (not `.object-tab` which has legitimate application `<script>` tags). Added `waitForFunction` to wait for async client-side markdown rendering.
- **column-preferences**: Tests the `ColumnPrefs` API (`saveColumnPrefs`/`getVisibleColumns`) directly, verifies localStorage key format `col-prefs:{typeIri}`, and confirms persistence across page reload.
- **sidebar-panel-reorder**: Verifies `[data-panel-name]` DOM elements exist, tests localStorage `sempkm_panel_positions` key with `{zone, order}` format, confirms persistence across reload, and validates container elements (`#right-content`, `#nav-tree`).
- **docs-navigation**: Combines API endpoint verification (`GET /browser/docs`, `GET /browser/docs/guide/{filename}`) with UI tab opening via `openDocsTab()` and link click-through verification.

## Verification

```
cd e2e && npx playwright test tests/01-objects/markdown-rendering.spec.ts tests/02-views/column-preferences.spec.ts tests/03-navigation/sidebar-panel-reorder.spec.ts tests/06-settings/docs-navigation.spec.ts --project=chromium
```
All 4 tests passed (9.5s total).

Slice-level checks (intermediate — T10 of T12):
- `rg "test.skip(" e2e/tests/ -c -g '*.ts'` — 18 stubs remain (T11/T12 scope, not T10)
- T10's own files have 0 stubs

## Diagnostics

None — test-only task with no production code changes.

## Deviations

- Pre-existing tests stored body as `dcterms:description` — changed to `urn:sempkm:body` which is the actual body predicate used by the object read view
- Pre-existing XSS check queried `.object-tab script` which found 5 legitimate application scripts — scoped to `.markdown-body` (the DOMPurify-sanitized container)

## Known Issues

None.

## Files Created/Modified

- `e2e/tests/01-objects/markdown-rendering.spec.ts` — rewrote: 1 consolidated test covering API create + endpoint verify + UI rendered markdown + XSS sanitization
- `e2e/tests/02-views/column-preferences.spec.ts` — rewrote: 1 test covering ColumnPrefs API, localStorage persistence, reload survival
- `e2e/tests/03-navigation/sidebar-panel-reorder.spec.ts` — rewrote: 1 test covering panel DOM, position storage, reload persistence
- `e2e/tests/06-settings/docs-navigation.spec.ts` — rewrote: 1 test covering docs API endpoints + UI tab + link navigation
