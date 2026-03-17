# M012: Workspace & Event Log Polish

**Vision:** Three UX improvements that make daily SemPKM usage smoother: event log fields gain autocomplete and helptext matching the quality of object SHACL forms, body content changes store incremental diffs instead of full replacements, and a persona system lets users switch between named workspace configurations for different purposes.

## Success Criteria

- User opens event log detail, predicate columns show human-readable labels (e.g., "Title" not "dcterms:title" or "title")
- User hovers over a predicate in event log detail and sees helptext tooltip from SHACL annotations
- User types in event log filter fields and gets autocomplete suggestions for operation types, predicates, and objects
- User edits an existing note body (changes one paragraph), the event log shows a diff view highlighting only the changed paragraph in green/red — not the full body text
- First-time body set (no prior body) still uses `body.set` and displays as full text in event log
- User creates two named personas with different dockview layouts, switches between them, and layouts restore correctly
- Persona selector appears in user popover menu in the sidebar
- Personas are available via Ctrl+K command palette
- Default persona is auto-created on first use, capturing current workspace state
- Personas persist across Docker restarts (stored in SQLite)

## Key Risks / Unknowns

- **Dockview `fromJSON()` reliability** — Layout restore can fail if panel types change between save and restore. This is the main technical risk for personas.
- **Body.diff backward compatibility** — Existing `body.set` events must continue to render correctly alongside new `body.diff` events. The event log viewer must detect and handle both operation types.
- **Persona state capture scope** — Dockview layout JSON can be 5-50KB. Auto-saving on every layout change would create excessive writes. Must save only on explicit actions.

## Proof Strategy

- **Dockview `fromJSON()` reliability** → retire in S03 by building real persona switch with try/catch fallback to default layout, proving it handles both valid and invalid layout JSON gracefully
- **Body.diff backward compatibility** → retire in S02 by implementing both `body.set` and `body.diff` rendering paths and verifying both in unit tests and browser

## Verification Classes

- Contract verification: pytest unit tests for label resolution, helptext extraction, autocomplete SPARQL builders, diff computation, persona CRUD service
- Integration verification: browser tests verifying event log renders labels/helptext, autocomplete dropdowns appear, diff highlighting works, persona switch restores layouts
- Operational verification: personas persist across Docker restarts (SQLite storage + Alembic migration)
- UAT / human verification: event log readability improvement is subjective — labels should be more readable than raw IRIs

## Milestone Definition of Done

This milestone is complete only when all are true:

- Event log detail view shows human-readable predicate labels via LabelService
- Event log predicates have helptext tooltips from SHACL sh:description / sempkm:editHelpText
- Event log filter fields have working autocomplete for types, predicates, and objects
- Body save computes and stores incremental diffs when prior body exists
- Event log renders both body.set (full text) and body.diff (incremental diff) events correctly
- Persona CRUD works (create, rename, delete, switch)
- Persona switch restores dockview layout, sidebar panel positions, and explorer mode
- Persona selector in user popover menu and Ctrl+K command palette
- E2E Playwright tests cover all new features
- User guide docs updated for event log improvements and personas
- Success criteria re-checked against live Docker behavior

## Requirement Coverage

### New Requirements (to be registered)

| ID | Slice | Description |
|----|-------|-------------|
| EVTLOG-01 | S01 | Predicate/type/object labels resolve to human-readable text in event log |
| EVTLOG-02 | S01 | Helptext tooltips on event log predicates from SHACL annotations |
| EVTLOG-03 | S01 | Autocomplete for event log filter fields (operation type, predicate, object) |
| BDIFF-01 | S02 | Body changes store incremental diffs instead of full replacements |
| BDIFF-02 | S02 | Event log renders body.diff events with addition/deletion highlighting |
| BDIFF-03 | S02 | Existing body.set events continue to display correctly (backward compat) |
| PERSONA-01 | S03 | Named personas with CRUD (create, rename, delete) |
| PERSONA-02 | S03 | Persona switching restores dockview layout, sidebar positions, explorer mode |
| PERSONA-03 | S03 | Persona selector in user popover menu |
| PERSONA-04 | S03 | Persona switching via Ctrl+K command palette |
| PERSONA-05 | S03 | Default persona created on first use |

- Covers: EVTLOG-01, EVTLOG-02, EVTLOG-03, BDIFF-01, BDIFF-02, BDIFF-03, PERSONA-01, PERSONA-02, PERSONA-03, PERSONA-04, PERSONA-05
- Partially covers: none
- Leaves for later: Persona settings overrides (deferred — layout-only personas for v1)
- Orphan risks: none

### Standing Requirements

- E2E tests: S04 provides trailing E2E coverage; each feature slice includes browser verification
- User guide docs: S04 provides trailing docs coverage

## Slices

- [ ] **S01: Event Log Polish — Labels, Helptext & Autocomplete** `risk:low` `depends:[]`
  > After this: User opens event log and sees human-readable predicate labels, helptext tooltips on hover, and autocomplete suggestions when filtering by type/predicate/object

- [ ] **S02: Body.Diff — Incremental Storage & Rendering** `risk:medium` `depends:[]`
  > After this: User edits an existing note body and the event log shows only the changed lines highlighted in green/red, not the full body text replacement

- [ ] **S03: Workspace Personas** `risk:high` `depends:[]`
  > After this: User creates named personas with different workspace layouts, switches between them via sidebar menu or Ctrl+K, and layouts restore correctly including dockview panels, sidebar positions, and explorer mode

- [ ] **S04: E2E Tests & User Guide** `risk:low` `depends:[S01,S02,S03]`
  > After this: All new features have Playwright E2E test coverage and user guide documentation; event log improvements documented in existing event log guide page, personas documented in new guide page

## Boundary Map

### S01 (Event Log Polish)

Produces:
- `ShapesService.get_helptext_for_predicates(iris)` method returning `{predicate_iri: helptext}`
- Predicate label resolution in `event_detail()` and `event_log()` router via `LabelService.resolve_batch()`
- `predicate_labels` and `predicate_helptext` dicts passed to event log templates
- Three suggestion endpoints: `GET /browser/events/suggest-types`, `GET /browser/events/suggest-predicates?q=`, `GET /browser/events/suggest-objects?q=`
- htmx autocomplete UI in event log filter area

Consumes:
- nothing (first slice, extends existing event log infrastructure)

### S02 (Body.Diff)

Produces:
- `body.diff` operation type in command schemas
- `handle_body_diff()` handler computing and storing unified diff
- Modified `save_object_body()` endpoint that emits `body.diff` when existing body present
- `EventQueryService.get_event_detail()` handling `body.diff` events (reading stored diff directly)
- Template rendering for `body.diff` events reusing existing diff line CSS

Consumes:
- nothing (independent of S01, extends existing body.set infrastructure)

### S03 (Workspace Personas)

Produces:
- `Persona` SQLAlchemy model with Alembic migration `013_personas.py`
- `PersonaService` with CRUD + activate + get_active
- REST API: `GET/POST /api/personas`, `PUT/DELETE /api/personas/{id}`, `POST /api/personas/{id}/activate`
- Persona selector in `_sidebar.html` user popover menu
- Command palette entries for persona switching
- Frontend persona switch logic: restore dockview layout + sidebar positions + explorer mode
- Default persona auto-creation on first workspace load

Consumes:
- nothing (independent of S01/S02, extends existing workspace infrastructure)

### S03 → S04

Produces:
- All three feature slices complete, ready for E2E test and docs coverage

### S04 (E2E Tests & User Guide)

Produces:
- Playwright E2E tests covering event log labels, autocomplete, body.diff rendering, persona CRUD/switch
- Updated `docs/guide/15-event-log.md` with label/helptext/autocomplete features
- New `docs/guide/30-personas.md` covering persona creation, switching, management
- README TOC and navigation chain updates

Consumes:
- S01 event log polish features (labels, helptext, autocomplete)
- S02 body.diff features (diff storage and rendering)
- S03 persona features (CRUD, switch, command palette)
