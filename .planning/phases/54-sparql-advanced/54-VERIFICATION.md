---
phase: 54-sparql-advanced
verified: 2026-03-10T07:26:19Z
status: passed
score: 9/9 must-haves verified
---

# Phase 54: SPARQL Advanced Verification Report

**Phase Goal:** Users can share queries with collaborators and promote saved queries into browsable views in the nav tree
**Verified:** 2026-03-10T07:26:19Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Success Criteria (from ROADMAP.md)

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | User can share a saved query with another user who can view and run it (read-only) | VERIFIED | `SharedQueryAccess` model + `PUT /api/sparql/saved/{id}/shares` endpoint fully implemented; share picker UI wired to PUT on checkbox change |
| 2 | User can promote a saved query to a named view that appears in the nav tree alongside model-defined views | VERIFIED | `PromotedQueryView` model + `POST /api/sparql/saved/{id}/promote`; MY VIEWS section in workspace.html loads via htmx from `/browser/my-views` |
| 3 | Named query views execute the saved SPARQL and render results using the standard view infrastructure | VERIFIED | `get_view_spec_by_iri()` resolves `urn:sempkm:user-view:*` IRIs from SQLite; `execute_table_query()` has `source_model == "user"` branch skipping `?s`-dedup; table/card/graph view endpoints all pass `user_id`/`db` |

**Score:** 3/3 success criteria verified

### Observable Truths (Plan 54-01 Must-Haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Owner can share a saved query with another non-guest user | VERIFIED | `PUT /api/sparql/saved/{query_id}/shares` replaces share list, filters self, owner-only check present |
| 2 | Shared queries appear in recipient's Saved dropdown under 'Shared with Me' section | VERIFIED | `GET /api/sparql/saved?include_shared=true` returns `{my_queries, shared_with_me}`; `loadSaved()` in sparql-console.js renders both sections with section headers and divider |
| 3 | Recipient can load a shared query into the editor and run it | VERIFIED | `.sparql-shared-item` click handler calls `setEditorContent(qt)` with the shared query text |
| 4 | Recipient can fork a shared query as their own via 'Save as my own' | VERIFIED | `forkSharedQuery()` calls `POST /api/sparql/saved/{id}/fork`; endpoint creates `SavedSparqlQuery` named `"Copy of {name}"` |
| 5 | Owner can unshare a query by unchecking a user in the share picker | VERIFIED | Checkbox `change` handler immediately `PUT`s full checked list; unchecking sends updated list without that user |
| 6 | Shared query shows 'Updated' badge when query changed since recipient last viewed it | VERIFIED | `is_updated` computed in `saved_query_list` endpoint (`updated_at > last_viewed_at`, null treated as always updated); `sparql-updated-badge` span rendered conditionally |

### Observable Truths (Plan 54-02 Must-Haves)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can promote a saved query to a named view via the Saved dropdown or results area | VERIFIED | Promote button (`.sparql-promote-btn`) opens `promote-dialog` via `openPromoteDialog()`; "Save as View" button renders in results info area when `currentSavedQueryId` is set |
| 2 | Promoted views appear in a 'My Views' section in the nav tree below VIEWS | VERIFIED | `section-my-views` div in workspace.html with `hx-get="/browser/my-views"` htmx load; section renders after `section-views` |
| 3 | Clicking a promoted view in the nav tree renders results using existing table/cards/graph infrastructure | VERIFIED | `my_views.html` calls `openViewTab(spec_iri, label, renderer_type)` which is `window.openViewTab` from workspace.js line 2493; view routes call `get_view_spec_by_iri(iri, user_id, db)` which resolves user-view URIs |
| 4 | User can demote a promoted view back to just a saved query | VERIFIED | `demoteView()` in my_views.html inline script calls `DELETE /api/sparql/saved/{query_id}/promote`; then `htmx.ajax('GET', '/browser/my-views', '#my-views-tree')` refreshes list |
| 5 | Promoted views are private to the creator (other users do not see them) | VERIFIED | `get_user_promoted_view_specs()` filters by `PromotedQueryView.user_id == user_id`; `get_view_spec_by_iri()` for user-view IRIs also queries by user |
| 6 | Auto-detected columns from SELECT variables appear as table headers | VERIFIED | `_extract_select_var_names()` at service.py:53 parses SELECT clause with regex; columns populated on ViewSpec and used in `execute_table_query` |

**Score:** 9/9 truths verified

### Required Artifacts

| Artifact | Status | Evidence |
|----------|--------|----------|
| `backend/app/sparql/models.py` | VERIFIED | `SharedQueryAccess` (line 53) and `PromotedQueryView` (line 76) classes present with all required fields |
| `backend/migrations/versions/008_sharing_promotion.py` | VERIFIED | Creates `shared_query_access` and `promoted_query_views` tables with indexes, `down_revision = "007"` |
| `backend/app/sparql/router.py` | VERIFIED | 9 new endpoints: list-users, get/put shares, mark-viewed, fork, promote (POST), demote (DELETE), promotion status (GET) |
| `backend/app/sparql/schemas.py` | VERIFIED | `ShareableUserOut`, `SharedQueryOut`, `ShareUpdateRequest` imported at router.py:34-43 |
| `backend/app/views/service.py` | VERIFIED | `_extract_select_var_names` (line 53), `get_user_promoted_view_specs` (line 271), extended `get_view_spec_by_iri` (line 216), `source_model=="user"` branch in `execute_table_query` (line 431) |
| `backend/app/views/router.py` | VERIFIED | All three renderers (table/card/graph) pass `user_id=user.id, db=db` to `get_view_spec_by_iri`; source_model passed to template context |
| `backend/app/browser/router.py` | VERIFIED | `GET /browser/my-views` endpoint at line 1914 calls `get_user_promoted_view_specs` and builds `query_id_map` for demote |
| `backend/app/templates/browser/workspace.html` | VERIFIED | `section-my-views` div with htmx lazy load at line 57; `promote_dialog.html` included at line 166 |
| `backend/app/templates/browser/my_views.html` | VERIFIED | Renders tree leaves with `openViewTab()` calls and `demoteView()` onclick; inline script defines `window.demoteView` |
| `backend/app/templates/browser/promote_dialog.html` | VERIFIED | `<dialog id="promote-dialog">` with name field, renderer picker (table/card/graph radios), graph warning div |
| `backend/app/templates/browser/table_view.html` | VERIFIED | `source_model == 'user'` branch at line 32 renders URI values as clickable `<a>` links rather than IRI pills |
| `frontend/static/js/sparql-console.js` | VERIFIED | `loadSaved()` fetches `include_shared=true`; `toggleSharePicker()` wired; `forkSharedQuery()` wired; `openPromoteDialog()` wired to promote btn; `handlePromoteSubmit()` POSTs to promote endpoint; `refreshMyViews()` htmx-refreshes tree |
| `frontend/static/css/workspace.css` | VERIFIED | `.sparql-share-btn`, `.sparql-promote-btn`, `.sparql-fork-btn`, `.sparql-updated-badge`, `.sparql-share-picker`, `#section-my-views` rules, `#promote-dialog` rules all present |
| `backend/app/templates/browser/sparql_panel.html` | VERIFIED | `data-current-user-id="{{ user.id }}"` on sparql panel container |

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| `sparql-console.js` | `/api/sparql/saved?include_shared=true` | `fetch` in `loadSaved()` (line 556) | WIRED |
| `sparql-console.js` | `/api/sparql/saved/{id}/shares` | `fetch` in `toggleSharePicker()` (lines 703-704, 741) | WIRED |
| `sparql-console.js` | `/api/sparql/saved/{id}/mark-viewed` | `fetch` POST in shared item click handler (line 660) | WIRED |
| `sparql-console.js` | `/api/sparql/saved/{id}/promote` | `fetch` POST in `handlePromoteSubmit()` (line 964) | WIRED |
| `views/service.py` | `sparql/models.py:PromotedQueryView` | `sa_select(PromotedQueryView, SavedSparqlQuery)` in `get_user_promoted_view_specs` | WIRED |
| `views/router.py` | `views/service.py:get_view_spec_by_iri` | Called with `user_id=user.id, db=db` in table/card/graph endpoints | WIRED |
| `workspace.html` | `/browser/my-views` | `hx-get="/browser/my-views"` with `hx-trigger="load"` on section header | WIRED |
| `my_views.html` | `workspace.js:openViewTab` | `onclick="openViewTab(...)"` calls `window.openViewTab` exposed at workspace.js:2493 | WIRED |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| SPARQL-04 | 54-01 | User can share a saved query with other users (read-only) | SATISFIED | `SharedQueryAccess` model, share/unshare/list-users/mark-viewed/fork endpoints, share picker UI with instant checkbox toggle, "Shared with Me" dropdown section |
| SPARQL-07 | 54-02 | User can promote a saved query to a named view browsable in the nav tree | SATISFIED | `PromotedQueryView` model, promote/demote/promotion-status endpoints, ViewSpecService user-view resolution, MY VIEWS nav tree section, promote dialog, demote action |

**Requirement SPARQL-08** appears in the REQUIREMENTS.md traceability table mapped to Phase 54 with status "Pending". It is NOT claimed by any plan's `requirements` field in this phase and was not implemented. This is an **ORPHANED** requirement for this phase — it was anticipated but intentionally deferred (no plan claimed it). No gap is created since the plan scopes exclude it.

### Anti-Patterns Found

No anti-patterns found. Scanned:
- `backend/app/sparql/router.py` — no TODOs, no stub returns
- `backend/app/views/service.py` — no TODOs, no stub returns
- `frontend/static/js/sparql-console.js` — no placeholder handlers; promote button click opens real dialog (not empty handler)
- `backend/app/templates/browser/my_views.html` — functional demote with fetch + htmx refresh
- `backend/app/templates/browser/promote_dialog.html` — complete form with renderer picker

### Human Verification Required

#### 1. Share Flow End-to-End

**Test:** As user A, save a SPARQL query, click the share icon in the Saved dropdown, check user B. As user B, open Saved dropdown.
**Expected:** "Shared with Me" section appears with the query name and "from user A" label. Updated badge dot is visible.
**Why human:** Multi-user flow; requires two authenticated sessions.

#### 2. Promoted View Renders Correctly

**Test:** Save a query like `SELECT ?title ?date WHERE { ?s dcterms:title ?title }`, promote it as a Table view. Click it in MY VIEWS.
**Expected:** Table renders with "Title" and "Date" column headers (auto-detected from SELECT variables). No `?s` column appears. Rows are not deduplicated by subject.
**Why human:** Query execution against live triplestore and visual table rendering cannot be verified statically.

#### 3. "Save as View" Button Appears After Executing a Saved Query

**Test:** Load a saved query from the dropdown (sets currentSavedQueryId), click Run.
**Expected:** "Save as View" button appears next to the row count in the results info area.
**Why human:** UI state tracking (`currentSavedQueryId`) requires runtime verification.

#### 4. Demote Removes View From Nav Tree but Preserves Saved Query

**Test:** Promote a query, then click the pin-off (demote) button on the MY VIEWS entry.
**Expected:** Entry disappears from MY VIEWS. Query still appears in Saved dropdown under "My Queries".
**Why human:** Two-panel state change across nav tree and SPARQL panel requires browser interaction.

#### 5. Other Users Cannot See Promoted Views

**Test:** As user A, promote a query. Log in as user B and open the workspace.
**Expected:** MY VIEWS section for user B shows "No promoted views yet" (or is empty). User A's promoted view does not appear.
**Why human:** Multi-user isolation requires two authenticated sessions.

---

## Notes

- **SPARQL-08** (prevent SPARQL writes) appears in the traceability table mapped to Phase 54 with "Pending" status, but no plan in this phase claimed it. It was intentionally deferred. The plans correctly scope only SPARQL-04 and SPARQL-07.
- The promote button in Plan 54-01 was rendered as a placeholder in the plan description ("placeholder click handler that does nothing"), but Plan 54-02 correctly wired it to `openPromoteDialog()`. The final codebase has it fully wired — no stub remains.

---

_Verified: 2026-03-10T07:26:19Z_
_Verifier: Claude (gsd-verifier)_
