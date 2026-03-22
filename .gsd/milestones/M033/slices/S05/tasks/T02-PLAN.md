---
estimated_steps: 4
estimated_files: 2
skills_used: []
---

# T02: SERVICE endpoint autocomplete and info banner

**Slice:** S05 — Federated SPARQL Console
**Milestone:** M033

## Description

Extend the SPARQL console with two pre-execution assistance features: (1) endpoint URL autocomplete when typing inside `SERVICE <...>` patterns, and (2) a debounced info banner below the editor showing detected SERVICE endpoints and their allowlist status.

The console already has `detectServiceEndpoints()`, `fetchMirrorAllowlist()`, `isEndpointAllowed()`, and the post-execution mirror button UI. This task adds the pre-execution typing assistance that makes those features discoverable before running a query.

## Steps

1. **Fetch allowlist at console init.** In `initSparqlConsole()` (line ~1652 of `sparql-console.js`), add `fetchMirrorAllowlist();` after the existing `fetchVocabulary();` call. This ensures the allowlist cache is warm before the user types anything. Currently `fetchMirrorAllowlist()` is only called post-execution.

2. **Add SERVICE URI autocomplete branch to `sparqlCompletions()`.** The existing function (line ~133) handles keywords, prefixed names, PREFIX declarations, and variables. Add a new detection branch:
   - Get the full line text up to the cursor position from `context.state.doc.lineAt(context.pos)`
   - Check if it matches the pattern `SERVICE\s+(?:SILENT\s+)?<([^>]*)$` (cursor inside an incomplete SERVICE URI)
   - If yes, extract the partial URL typed so far
   - Filter `mirrorAllowlistCache` entries: if cache is an array of objects `{url, source, removable}` (new format from T01), use `.url`; if array of strings (old format/fallback), use directly. Match entries whose URL starts with the partial text (case-insensitive).
   - Return completions with `from:` set to the position of the `<` character + 1, each option having `label: url`, `type: 'url'`, `detail: '⛓'` (chain emoji as the type indicator)
   - The `validFor` regex should be `/^[^\s>]*/` (anything except whitespace or `>`)
   - **Important:** Return early from this branch — don't fall through to keyword completions when inside a SERVICE URI

3. **Add debounced SERVICE info banner.** After `createEditor()` in `initSparqlConsole()`:
   - Create a `div.sparql-service-info` element and insert it after the `.codemirror-container` (or after the editor's root element)
   - Set up an `EditorView.updateListener.of(update => { ... })` extension (add to the extensions array in `createEditor()`), debounced at 500ms
   - On content change, run `detectServiceEndpoints()` on the current document text
   - If no endpoints detected, hide the banner (`display: none`)
   - If endpoints found, show the banner with per-endpoint status:
     - For each endpoint: show the URL, then a status indicator — ✓ if `isEndpointAllowed(url)` is true (checking cache; if cache is object format, adapt), or ⚠ if not allowed
     - If user is owner role (check `document.body.dataset.userRole === 'owner'` or similar existing pattern), show a small link to `/admin/federation`
   - **Cache invalidation:** When the banner detects the allowlist cache hasn't been fetched yet (still null), trigger `fetchMirrorAllowlist()` and re-render when the promise resolves

4. **Add CSS for the info banner** in `frontend/static/css/workspace.css`:
   - `.sparql-service-info` — subtle info bar: small font, muted background (`var(--color-surface-raised)` or similar), border-top, padding 6px 12px, flex row with gap
   - `.sparql-service-info .endpoint-status` — inline-flex items with the endpoint URL and status icon
   - `.sparql-service-info .endpoint-allowed` — green/success color for the ✓
   - `.sparql-service-info .endpoint-blocked` — warning/amber color for the ⚠
   - `.sparql-service-info a` — small link style for the admin link
   - Dark theme overrides: `[data-theme="dark"] .sparql-service-info` with appropriate dark colors
   - Ensure the banner doesn't add layout shift — use `display: none` when empty, not `visibility: hidden`

## Must-Haves

- [ ] Allowlist cache is warm before user starts typing (fetched at init)
- [ ] Autocomplete triggers inside `SERVICE <...>` with allowlisted endpoint URLs
- [ ] Autocomplete returns early — doesn't mix endpoint URLs with keyword suggestions
- [ ] Info banner appears within ~500ms of typing a SERVICE clause
- [ ] Info banner shows per-endpoint allowlist status (✓/⚠)
- [ ] Info banner hides when no SERVICE endpoints in query
- [ ] CSS follows dark/light theme patterns, no layout shift

## Verification

- Manual browser test: Open SPARQL console, type `SERVICE <` — autocomplete dropdown appears with allowlisted endpoints
- Type a full `SERVICE <https://dbpedia.org/sparql>` — info banner appears below editor showing the endpoint with ✓ or ⚠
- Delete the SERVICE clause — banner disappears
- Both light and dark themes render correctly

## Inputs

- `frontend/static/js/sparql-console.js` — existing autocomplete, SERVICE detection, allowlist fetch functions
- `frontend/static/css/workspace.css` — existing mirror button CSS, theme variables
- T01 output: `backend/app/sparql/mirror_router.py` — updated GET endpoint returns `{url, source, removable}` objects (but the JS should handle both old string format and new object format gracefully)

## Expected Output

- `frontend/static/js/sparql-console.js` — updated with autocomplete branch, info banner, early allowlist fetch
- `frontend/static/css/workspace.css` — updated with `.sparql-service-info` styles

## Observability Impact

- **New signal:** The `.sparql-service-info` banner is a live diagnostic surface — it shows which SERVICE endpoints are detected in the current query and whether each is in the allowlist (✓ or ⚠). This is visible to the user without running the query.
- **Cache warm-up:** `fetchMirrorAllowlist()` now runs at console init, so the allowlist cache is populated immediately. Any fetch failure is logged to console via `console.warn()`.
- **Autocomplete inspection:** SERVICE URI completions use type `'url'` and detail `'⛓'` — these are distinguishable from keyword/variable/class completions in the CodeMirror dropdown.
- **Failure visibility:** If the allowlist fetch fails, the info banner shows ⚠ for all endpoints (cache is empty = nothing allowed). The autocomplete silently returns no suggestions when the cache is empty.
