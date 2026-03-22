# S05 Research: Federated SPARQL Console

## Summary

This slice is **light work on an already-built foundation**. The SPARQL console already has SERVICE clause detection, mirror allowlist fetching, endpoint validation, and mirror button UI with success/warning/error states — all implemented and styled. The gap is two features: (1) endpoint URL autocomplete when typing `SERVICE <...>` in the CodeMirror editor, and (2) an admin UI for managing the federation endpoint allowlist dynamically (currently env-var only).

## Requirements

The roadmap references these M033-specific requirements for S05:
- **FED-01** through **FED-03** (from boundary map): SERVICE detection, endpoint validation UI, mirror button, endpoint autocomplete, admin allowlist management

Note: The existing FED-01–FED-09 in REQUIREMENTS.md are all validated federation-sync requirements from prior milestones (M002/S06 era) — they are NOT the same as the M033 SPARQL console UX requirements.

## Recommendation

Follow the existing code patterns exactly. Three tasks:

1. **Endpoint autocomplete in CodeMirror** — extend `sparqlCompletions()` to suggest allowlisted endpoint URLs when the cursor is inside a `SERVICE <...>` pattern. Small, self-contained JS change.
2. **Admin federation endpoint management** — new admin page + API endpoints for CRUD on the allowlist. Store in `data/.federation-endpoints.json` alongside instance config. Merge with env var entries at load time.
3. **Polish + verification** — SERVICE clause info banner in the editor area (pre-execution), tests, CSS refinements.

## Implementation Landscape

### What Already Exists (No Work Needed)

| Component | File | Status |
|-----------|------|--------|
| `detectServiceEndpoints(query)` | `sparql-console.js:206–225` | ✅ Complete — regex extraction, handles SILENT, strips string literals |
| `fetchMirrorAllowlist()` | `sparql-console.js:233–248` | ✅ Complete — cached fetch from `/api/sparql/mirror/endpoints` |
| `isEndpointAllowed(url)` | `sparql-console.js:253–256` | ✅ Complete — checks cached allowlist |
| `handleMirrorClick(btn, query, endpoint)` | `sparql-console.js:288–341` | ✅ Complete — POST to mirror API, progress states, error handling |
| Mirror button rendering | `sparql-console.js:260–283` (inside `executeQuery()`) | ✅ Complete — appears post-execution when SERVICE detected, shows warning if endpoint not in allowlist |
| Mirror button CSS | `workspace.css` | ✅ Complete — `.sparql-mirror-btn`, `.mirror-warning`, `.mirror-success`, `.mirror-error`, dark theme variants |
| `MirrorService` | `backend/app/sparql/mirror.py` | ✅ Complete — 277 lines, provenance tracking, batch storage, stats |
| `mirror_router` | `backend/app/sparql/mirror_router.py` | ✅ Complete — POST /mirror, GET /endpoints, GET /stats, DELETE |
| `federation_allowed_endpoints` config | `backend/app/config.py:69` | ✅ Complete — comma-separated env var, `get_allowed_endpoints()` parser |
| Mirror service tests | `backend/tests/test_mirror_service.py` | ✅ Complete — 476 lines |
| Federation discovery tests | `backend/tests/test_federation_discovery.py` | ✅ Complete — 145 lines |

### What Needs Building

#### 1. Endpoint URL Autocomplete (sparql-console.js)

**Current state:** `sparqlCompletions()` at line ~150 handles keywords, prefixed names, PREFIX declarations, and variables. No awareness of SERVICE clause context.

**What to add:** When the cursor is positioned inside or just after `SERVICE <`, suggest allowlisted endpoint URLs. Detection approach:
- Check if the text before cursor matches `SERVICE\s+(?:SILENT\s+)?<[^>]*$` (incomplete SERVICE URI)
- If yes, filter `mirrorAllowlistCache` entries matching the partial URL typed so far
- Return completions with type `'url'` and the `database` Lucide icon in the detail field

**Key constraint:** The allowlist is fetched lazily. Need to trigger `fetchMirrorAllowlist()` at editor init time (currently only called post-execution). Add a call in `initSparqlConsole()` after `fetchVocabulary()`.

**Files:** `frontend/static/js/sparql-console.js` only.

#### 2. Admin Federation Endpoint Management

**Current state:** Allowlist is read from `settings.federation_allowed_endpoints` (env var). No admin UI. No CRUD API. The `GET /api/sparql/mirror/endpoints` returns the list but there's no write path.

**Storage decision:** Store in `data/.federation-endpoints.json` (similar to `data/.instance-config.json`). This:
- Survives container rebuilds (Docker volume-mounted `data/`)
- Is independent of the database (no migration needed)
- Follows the instance config precedent
- Merges with env var: `env var entries ∪ persisted entries` = effective allowlist

**New backend files:**
- `backend/app/sparql/federation_config.py` — load/save/merge logic for the endpoints JSON file
- Three new routes in `mirror_router.py`:
  - `POST /api/sparql/mirror/endpoints` — add an endpoint (owner-only)
  - `DELETE /api/sparql/mirror/endpoints/{encoded_url}` — remove an endpoint (owner-only)
  - Existing `GET /api/sparql/mirror/endpoints` updated to return merged list + indicate which came from env var (non-removable)

**New frontend files:**
- `backend/app/templates/admin/federation.html` — admin page with endpoint list, add form, remove buttons
- Route in `backend/app/admin/router.py` — `GET /admin/federation`

**Admin index update:** Add a "Federation" card to `backend/app/templates/admin/index.html`.

#### 3. Pre-execution SERVICE Info Banner

**Current state:** SERVICE clause feedback only appears *after* query execution (mirror button in results info). The user gets no feedback while editing.

**What to add:** After the editor content changes (debounced ~500ms), run `detectServiceEndpoints()` on current text. If endpoints found, show a subtle info bar below the editor with:
- Endpoint URL(s) detected
- Allowlist status per endpoint (✓ allowed / ⚠ not in allowlist)
- Link to admin federation page for owner role

**Constraint:** Don't block typing. Use `EditorView.updateListener` or a debounced content change handler.

**Files:** `frontend/static/js/sparql-console.js`, `frontend/static/css/workspace.css`.

### Integration Points

- `settings.get_allowed_endpoints()` is called from `MirrorService.validate_endpoint()` — after this slice, that method should also check the persisted file
- `mirrorAllowlistCache` in sparql-console.js should be invalidated when the admin updates the allowlist (reload on next console activation, or use a cache-busting query param)
- The SPARQL admin page (`admin/sparql.html`) uses Yasgui — it's separate from the workspace console and does NOT need federation UI (admin can use the workspace console)

### Patterns to Follow

- **Admin page template:** Follow `admin/webhooks.html` for layout. Admin card in `index.html` follows the existing pattern (h2, p, a.btn-primary with htmx).
- **File persistence:** Follow `instance_config.py` pattern — Pydantic model, `load_X()` / `save_X()`, atomic write via temp file + `os.replace()`.
- **CodeMirror autocomplete:** Existing `sparqlCompletions()` function handles context detection by examining `word.text` and cursor position. Extend with a new detection branch for SERVICE URIs.
- **API route protection:** Use `require_role("owner")` (existing pattern in mirror_router.py).
- **Lucide icons in flex containers:** Per CLAUDE.md rules, any icons in the admin page buttons must use CSS sizing with `flex-shrink: 0`, not inline styles.

### Verification Strategy

- **Unit tests:** Test the federation config load/save/merge logic (env var + file merging, edge cases with empty/duplicate entries)
- **API tests:** Test POST/DELETE endpoints for adding/removing, verify GET returns merged list
- **Manual browser verification:** Open SPARQL console, type `SERVICE <`, confirm autocomplete dropdown shows allowlisted endpoints. Open admin federation page, add/remove endpoints, verify changes reflected in console.

### Risk Assessment

**Risk: Very Low.** All infrastructure exists. The work is:
- ~30 lines of JS for autocomplete
- ~100 lines of Python for federation config persistence
- ~80 lines of Jinja2 for admin template
- ~30 lines of CSS for info banner and admin page
- ~40 lines for new API routes
- Tests

No new libraries. No novel architecture. No cross-cutting concerns. Follows established patterns exactly.
