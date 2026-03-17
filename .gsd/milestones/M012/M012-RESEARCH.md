# M012: Workspace & Event Log Polish — Research

**Date:** 2026-03-17
**Status:** Complete

## Summary

M012 covers three independent workstreams: (1) event log polish (label resolution, helptext, autocomplete), (2) body.diff incremental storage, and (3) a persona system for switching workspace configurations. The codebase is well-prepared for all three. The event log already resolves affected-object labels via `LabelService.resolve_batch()` but shows raw IRI local-name extractions for predicates (e.g., `pred_iri.split('/')[-1].split('#')[-1]`). The body diff viewer already exists using Python's `difflib.unified_diff()` — what's missing is storing diffs instead of full replacements. The named layout system (`SemPKMLayouts` in `named-layouts.js`) already saves/restores dockview JSON to localStorage — personas extend this by associating layouts with named configurations persisted server-side.

The biggest risk is the persona system's scope. Dockview's `fromJSON()` can fail if panel types have changed, and the current layout includes transient state (open tabs, panel positions) that may not cleanly restore. The other two workstreams are straightforward extensions of existing patterns with minimal risk.

## Recommendation

**Slice order: Event Log Polish → Body.Diff → Personas.** Event log polish is the lowest-risk, highest-value work — it uses established patterns (LabelService, ShapesService, tag-autocomplete) and improves daily usability immediately. Body.diff is a contained backend change with a clear acceptance test. Personas are the most complex and benefit from shipping last — they touch frontend (dockview, sidebar, command palette), backend (new SQLite table), and need graceful fallback for layout restore failures.

**Approach highlights:**
- **Event log labels:** Extend `EventQueryService.get_event_detail()` to return label-enriched data. Resolve predicate IRIs via `LabelService` in the router layer (same pattern as affected-object label resolution in `event_log()`). Template changes only — replace `pred_iri.split(...)` with looked-up labels.
- **Event log helptext:** Query `sh:description` and `sempkm:editHelpText` from `ShapesService` for predicates appearing in events. Render as title attributes or tooltip popovers.
- **Event log autocomplete:** Adapt the proven tag-autocomplete pattern (htmx `hx-trigger="keyup changed delay:300ms"` → suggestion endpoint → dropdown). Three endpoints: types, predicates, and objects.
- **Body.diff:** New `body.diff` operation type storing unified diff text. Handler computes diff from current body (queried from materialized state) vs new body. Event log viewer already renders diffs — just needs to detect `body.diff` operation type alongside existing `body.set`.
- **Personas:** New `Persona` SQLite model + Alembic migration. Backend CRUD API. Frontend: persona selector in user popover menu, command palette entries. Each persona stores dockview layout JSON + sidebar panel positions + explorer mode. SettingsService extended with persona-scoped overrides.

## Implementation Landscape

### Key Files

**Event Log Polish:**
- `backend/app/events/query.py` (556 lines) — `EventQueryService` with `list_events()`, `get_event_detail()`, `_compute_body_diff()`. The detail query returns raw predicate IRIs in `data_triples`, `new_values`, `before_values`. **Change:** Add label resolution data to `EventDetail` return.
- `backend/app/browser/events.py` (192 lines) — Router with `event_log()`, `event_detail()`, `undo_event()`. Already uses `LabelService` for affected-IRI labels. **Change:** Extend to resolve predicate labels and helptext, pass to templates.
- `backend/app/templates/browser/event_log.html` — Timeline list. Shows operation badges, affected-object links (labeled), raw user IRIs (resolved via `user_names`). Filter dropdown has hardcoded operation types. **Change:** Add autocomplete inputs for type/predicate/object filters.
- `backend/app/templates/browser/event_detail.html` — Diff panel. Uses `pred_iri.split('/')[-1].split('#')[-1]` for predicate display. **Change:** Use pre-resolved labels, add title/tooltip for helptext.
- `backend/app/services/labels.py` — `LabelService` with SPARQL COALESCE batch resolution and TTL cache. Resolves IRIs to labels via `dcterms:title > rdfs:label > skos:prefLabel > schema:name > foaf:name > QName`. Already used in event log for affected objects. **Reuse as-is** for predicate label resolution.
- `backend/app/services/shapes.py` (322 lines) — `ShapesService` with `_extract_property_shape()` which already reads `sh:description` and `sempkm:editHelpText`. **Change:** Expose a method to look up helptext by predicate IRI.
- `backend/app/browser/search.py` — Contains `tag_suggestions()` endpoint and `build_tag_suggestions_sparql()`. **Pattern to follow** for event log autocomplete endpoints.
- `frontend/static/css/workspace.css` — Lines 3870–4210: event log styles including `.diff-line-add`, `.diff-line-remove`, `.diff-pred-label`. Already has green/red diff coloring. **Extend** for autocomplete dropdown styling.

**Body.Diff:**
- `backend/app/commands/handlers/body_set.py` (56 lines) — `handle_body_set()` creates `Operation` with `operation_type="body.set"`. **Change:** Add companion `handle_body_diff()` that stores unified diff string instead of full body.
- `backend/app/commands/schemas.py` — `BodySetParams` with `iri`, `body`, `predicate`. **Change:** Add `BodyDiffParams` with `iri`, `diff` (or compute diff server-side from `old_body` + `new_body`).
- `backend/app/browser/objects.py:375` — `save_object_body()` endpoint builds `BodySetParams` and commits via EventStore. **Change:** Optionally compute diff here (compare current body from materialized state with new body), and if body exists, emit `body.diff` instead of `body.set`.
- `backend/app/events/query.py` — `get_event_detail()` already handles `body.set` → `_compute_body_diff()` by querying the previous body value. For `body.diff`, the diff is stored in the event graph directly — just read it. `_compute_body_diff()` stays for backward compat with old `body.set` events.
- `backend/app/events/store.py` (365 lines) — `EventStore.commit()` is operation-type-agnostic. No changes needed — `body.diff` is just another operation type string.

**Personas:**
- `backend/app/auth/models.py` — SQLAlchemy models. Contains `UserSetting` (key-value per user). **Change:** Add `Persona` model (id, user_id, name, layout_json, sidebar_positions, explorer_mode, settings_overrides, is_active, created_at, updated_at).
- `backend/migrations/versions/` — Last migration is `012_workflow_specs.py`. **Change:** Add `013_personas.py`.
- `frontend/static/js/named-layouts.js` (169 lines) — `SemPKMLayouts` saves/restores dockview JSON to localStorage. **Pattern to adapt** — personas persist server-side, but use the same `dv.toJSON()`/`dv.fromJSON()` calls.
- `frontend/static/js/workspace-layout.js` (604 lines) — `initWorkspaceLayout()` restores from `DV_LAYOUT_KEY` in localStorage. `onDidLayoutChange` auto-saves. **Change:** When persona active, save to server instead of (or in addition to) localStorage.
- `frontend/static/js/workspace.js` (4076 lines) — Command palette registration at line 1286+. Layout save/restore commands at line 1425+. Explorer mode at line 2182+. Panel drag-drop positions at line 1991+. **Change:** Add persona commands, wire persona switch to restore layout + sidebar + explorer mode.
- `backend/app/templates/components/_sidebar.html` — User popover menu (line 140+) with Settings, Layouts, Theme, Clear & Reload, Log out. **Change:** Add persona selector between Settings and Layouts.
- `backend/app/canvas/service.py` — `CanvasService` pattern: JSON doc storage in `user_settings` table via `_upsert_setting()`. **Pattern to follow** for persona JSON storage (but with a dedicated table, since personas have their own lifecycle).
- `backend/app/services/settings.py` — `SettingsService` with layered resolution (system < model < user). **Change:** Add persona layer between model and user (system < model < persona < user).

### Build Order

**Phase 1: Event Log Label Resolution & Helptext (lowest risk, immediate value)**
1. Extend `event_detail()` router to resolve predicate labels via `LabelService.resolve_batch()` — same pattern as affected-IRI resolution already in `event_log()`
2. Add `ShapesService.get_helptext_for_predicates(iris)` method that returns `{predicate_iri: helptext}` by scanning all PropertyShapes
3. Pass `predicate_labels` and `predicate_helptext` dicts to `event_detail.html` template
4. Update template to use resolved labels and helptext tooltips instead of raw IRI splitting
5. Also resolve predicate labels in the event log list view (operation type is already human-readable; the affected-object links need no change since they already use labels)

**Phase 2: Event Log Autocomplete (extends Phase 1)**
1. Create three suggestion endpoints: `GET /browser/events/suggest-types` (distinct `sempkm:operationType` values), `GET /browser/events/suggest-predicates?q=` (distinct predicates from recent events), `GET /browser/events/suggest-objects?q=` (label search via LabelService)
2. Replace the static `<select>` operation filter with an htmx autocomplete input following the tag-suggestions pattern
3. Add autocomplete for object filter (currently a link-based filter from clicking an affected object)

**Phase 3: Body.Diff (contained backend change)**
1. Add `body.diff` operation type to `commands/schemas.py` and a handler
2. Modify `save_object_body()` in `objects.py` to compute diff when an existing body is present
3. Update `EventQueryService.get_event_detail()` to handle `body.diff` events (read stored diff directly instead of computing from before/after values)
4. Update `event_detail.html` to render `body.diff` events (reuse existing diff line rendering)
5. Ensure backward compat: old `body.set` events still display correctly via the existing `_compute_body_diff()` path

**Phase 4: Personas (most complex, benefits from others shipping first)**
1. Alembic migration `013_personas.py` creating `personas` table
2. Backend `PersonaService` with CRUD + switch + active-persona resolution
3. Backend API endpoints: `GET/POST /api/personas`, `PUT/DELETE /api/personas/{id}`, `POST /api/personas/{id}/activate`
4. Frontend: persona selector in user popover, command palette entries
5. Frontend: on persona switch, restore dockview layout + sidebar positions + explorer mode
6. Integration with SettingsService for persona-scoped setting overrides

**Phase 5: E2E Tests + User Guide Docs (trailing coverage)**
1. Playwright tests for event log labels, autocomplete, body.diff, persona CRUD/switch
2. Update `docs/guide/15-event-log.md` with new features
3. New `docs/guide/30-personas.md` covering persona creation, switching, and management

### Verification Approach

**Event Log Polish:**
- Unit tests: `test_event_log_labels.py` — mock LabelService/ShapesService, verify label resolution in EventDetail
- Unit tests: `test_event_suggestions.py` — test suggestion endpoint SPARQL builders
- Browser: open event log, verify predicates show human labels (e.g., "Title" not "dcterms/title"), hover shows helptext
- Browser: type in autocomplete, verify suggestions appear

**Body.Diff:**
- Unit tests: `test_body_diff.py` — test diff computation, handler, and event detail rendering for both `body.set` and `body.diff` events
- Browser: edit an object's body (change one paragraph), open event log, expand diff — should show only changed lines in green/red, not full text

**Personas:**
- Unit tests: `test_persona_service.py` — CRUD, activation, settings overlay
- Browser: create two personas with different layouts, switch between them, verify layout restores
- E2E: Playwright test covering persona create → switch → verify layout state

## Constraints

- **htmx + vanilla JS only** — No React, no component frameworks. Autocomplete must use htmx patterns (see tag-suggestions pattern in `search.py`).
- **Event graphs are immutable** — Cannot retroactively change `body.set` events to `body.diff`. New events get the new type; old events use existing rendering path.
- **SQLite for persona storage** — Same layer as auth/settings. Must use Alembic migration.
- **Dockview `fromJSON()` failure** — Can throw if panel types changed. Must have graceful fallback (reset to default layout, show toast).
- **LabelService TTL cache is 300s** — Predicate labels will be cached. No cache invalidation issue since predicate IRIs are stable (they come from ontologies).
- **Body body predicate** — Body content uses `sempkm:body` by default but can use model-specific predicates (see `BodySetParams.predicate`). Diff computation must handle both.
- **Current layout auto-save to localStorage** — `workspace-layout.js` line 308 saves to `sempkm_layout_current` on every `onDidLayoutChange`. Persona system must decide whether to also persist server-side on every change (expensive) or only on explicit save/switch.

## Common Pitfalls

- **Predicate labels may not exist** — Not all predicates have `rdfs:label` or `sh:name`. LabelService falls back to QName or IRI local name — this is acceptable and already tested. But event detail currently does its own `split('/')[-1].split('#')[-1]` — must replace with LabelService fallback to get consistent behavior.
- **Body.diff on first body** — If an object has no existing body and a body is set for the first time, there's no diff to compute — this should remain a `body.set` event, not `body.diff`.
- **Body.diff requires reading current state** — To compute a diff, the save endpoint must first query the current body from `urn:sempkm:current`. This adds one SPARQL read per body save. The query is simple (`SELECT ?body WHERE { GRAPH <urn:sempkm:current> { <IRI> sempkm:body ?body } }`) and fast.
- **Persona layout JSON can be large** — A workspace with many open tabs produces a dockview JSON of 5-50KB. Storing in a `Text` column is fine for SQLite. But auto-saving on every layout change would create excessive writes — save on explicit action (persona switch, save button) only.
- **Explorer mode is client-side state** — Stored in `localStorage` key `sempkm_explorer_mode`. Persona restore must set this key and trigger a mode switch (re-fetch explorer tree).
- **Sidebar panel positions are client-side state** — Stored in `localStorage` key `sempkm_panel_positions`. Persona restore must set this key and re-render panel positions.
- **SHACL shapes graph may be large** — `ShapesService._fetch_shapes_graph()` does a full CONSTRUCT of all shapes. For helptext lookup, we only need `sh:path` + `sh:description` + `sempkm:editHelpText`. Consider a targeted SPARQL SELECT instead of the full shapes CONSTRUCT to avoid loading the entire graph just for tooltips.

## Open Risks

- **Dockview `fromJSON()` version skew** — If dockview-core is upgraded between persona save and restore, the JSON format may be incompatible. Mitigation: wrap in try/catch with fallback to default layout (already the pattern in `initWorkspaceLayout()`).
- **Persona-scoped settings complexity** — The context says "possibly settings overrides." If personas override all user settings, the resolution chain becomes 4-layer (system < model < persona < user). This increases complexity. **Recommendation:** Start with layout-only personas (dockview JSON + sidebar positions + explorer mode). Settings overrides can layer on later if needed.
- **Autocomplete performance** — Suggesting objects by label requires searching all labels. If the triplestore has 10K+ objects, the SPARQL query could be slow. Mitigation: use `LIMIT 30` and require minimum 2-character prefix, same as tag suggestions.
- **Body.diff undo complexity** — Undoing a `body.diff` event requires applying the diff in reverse. Python's `difflib` doesn't have a built-in reverse-patch function. Options: (a) store both forward and reverse diff, (b) re-query the body state before the diff event and use `body.set` as the compensating operation (simpler, same approach as current undo for `body.set`).

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Text diffing | Python `difflib.unified_diff()` | Already used in `_compute_body_diff()`. Line-level diffs work well for markdown. |
| Label resolution | `LabelService.resolve_batch()` | Already resolves IRIs to labels with SPARQL COALESCE, TTL caching, QName fallback. |
| SHACL helptext | `ShapesService._extract_property_shape()` → `description` and `helptext` fields | Already parses `sh:description` and `sempkm:editHelpText` from shapes graph. |
| Autocomplete UI | htmx `hx-trigger="keyup changed delay:300ms"` pattern | Proven in tag-suggestions endpoint. No JS autocomplete library needed. |
| JSON doc storage | `CanvasService._upsert_setting()` pattern | Proven for large JSON documents in `user_settings` table. |
| Command palette | `ninja-keys` web component | Already in use. Persona entries follow existing layout save/restore pattern. |
| Layout save/restore | `SemPKMLayouts` module | Already handles `dv.toJSON()`/`dv.fromJSON()` with error handling. |

## Candidate Requirements

The milestone context mentions these user-visible features. These should be formalized as requirements:

| ID | Description | Notes |
|----|------------|-------|
| EVTLOG-01 | Predicate/type/object labels resolve to human-readable text in event log | Replace raw IRI splitting with LabelService |
| EVTLOG-02 | Helptext tooltips on event log predicates from SHACL annotations | Use sh:description / sempkm:editHelpText |
| EVTLOG-03 | Autocomplete for event log filter fields (operation type, predicate, object) | Follow tag-suggestions pattern |
| BDIFF-01 | Body changes store incremental diffs instead of full replacements | New body.diff operation type |
| BDIFF-02 | Event log renders body.diff events with addition/deletion highlighting | Extend existing diff rendering |
| BDIFF-03 | Existing body.set events continue to display correctly (backward compat) | No regression |
| PERSONA-01 | Named personas with CRUD (create, rename, delete) | SQLite storage |
| PERSONA-02 | Persona switching restores dockview layout, sidebar positions, explorer mode | Server-side persistence, client-side application |
| PERSONA-03 | Persona selector in user popover menu | In sidebar footer area |
| PERSONA-04 | Persona switching via Ctrl+K command palette | Follow layout save/restore pattern |
| PERSONA-05 | Default persona created on first use | Auto-migration from current localStorage state |

**Scope recommendation:** PERSONA settings overrides (layering persona settings on top of user settings) should be deferred or optional. Layout + sidebar + explorer mode is the high-value scope. Settings overrides add 4-layer resolution complexity for marginal gain in v1.

## Sources

- Dockview `toJSON()`/`fromJSON()` API is already proven in `workspace-layout.js` and `named-layouts.js`
- Python `difflib.unified_diff()` is already used in `EventQueryService._compute_body_diff()`
- Tag autocomplete pattern: `backend/app/browser/search.py` → `tag_suggestions()` endpoint + `backend/app/templates/browser/tag_suggestions.html`
- CanvasService JSON storage pattern: `backend/app/canvas/service.py` → `_upsert_setting()` with `user_settings` table
- ShapesService helptext extraction: `backend/app/services/shapes.py` → `_extract_property_shape()` reads `sh:description` and `SEMPKM_EDIT_HELPTEXT`
