# M012: Workspace & Event Log Polish

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

Three UX improvements that make daily SemPKM usage smoother: (1) Event log form fields gain autocomplete and helptext matching the quality of object SHACL forms, (2) body content changes store incremental diffs instead of full replacements, and (3) a "persona" system lets a single user switch between custom workspace layouts and settings for different purposes (e.g., "Research mode" vs "Project management mode").

## Why This Milestone

**Event log UX is behind object editing.** Object edit forms benefit from SHACL-driven helptext, autocomplete for type/predicate fields, and validated inputs. The event log viewer shows raw IRIs and has no inline help — it's a developer-facing tool in a user-facing position. Users exploring their event history can't easily understand what fields mean or filter effectively.

**Body diffs are wasteful.** Every `body.set` operation stores the complete new body text as a full replacement. For a 2000-word note where the user fixed a typo, the event graph stores 2000 words again. A `body.diff` approach would store only the delta, making event history more readable (users can see *what changed*, not just the full new text) and reducing triplestore storage.

**One-size-fits-all workspace.** Users doing research want different panel layouts, sidebar sections, and settings than when they're doing project management. Currently they must manually rearrange panels each time they switch contexts. A persona system lets them save named workspace configurations and switch instantly.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Browse the event log and see human-readable labels instead of raw IRIs for predicates, types, and objects
- See helptext tooltips on event log fields explaining what each predicate means
- Get autocomplete suggestions when filtering events by type, predicate, or object
- See incremental diffs for body changes in the event log (additions in green, deletions in red) instead of full text dumps
- Create named personas (e.g., "Research", "Project Mgmt", "Writing") each with their own panel layout, sidebar configuration, and settings overrides
- Switch between personas from the user menu or via Ctrl+K command palette
- Have persona-specific dockview layouts that restore when switching

### Entry point / environment

- Entry point: `http://localhost:3000/workspace` (event log panel, workspace layout, user menu)
- Environment: Docker Compose
- Live dependencies involved: RDF4J triplestore, SQLite (persona storage)

## Completion Class

- Contract complete means: event log fields resolve labels via LabelService, helptext renders from SHACL annotations, body.diff operations store and display correctly, personas CRUD works
- Integration complete means: event log autocomplete queries the triplestore for valid values, diffs render correctly in the event log viewer, persona switch restores full dockview layout state
- Operational complete means: personas persist across Docker restarts, body.diff backward-compatible with existing body.set events

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User opens event log, predicate columns show human labels (e.g., "Title" not "dcterms:title")
- User hovers over a predicate in event log and sees helptext
- User filters event log by type with autocomplete dropdown showing available types
- User edits a note body (changes one paragraph), the event log shows a diff view highlighting only the changed paragraph
- User creates two personas with different dockview layouts, switches between them, layouts restore correctly

## Risks and Unknowns

- **Diff algorithm choice** — Need a text diff algorithm that produces clean, readable diffs for markdown content. `difflib` in Python stdlib is an option; a more sophisticated approach might use line-level or word-level diffing.
- **Body.diff backward compatibility** — Existing events use `body.set` with full text. The event log viewer must handle both `body.set` (show full text) and `body.diff` (show diff). The EventStore must support both operation types.
- **Persona storage scope** — Personas need to capture: dockview layout state, sidebar panel positions, explorer mode, possibly settings overrides. The dockview serialization format is complex — need to verify it's reliably serializable/deserializable.
- **Dockview layout restore reliability** — Dockview's `fromJSON()` can fail if panel types have changed since the layout was saved. Need graceful fallback.

## Existing Codebase / Prior Art

- `backend/app/events/query.py` — EventQueryService with SPARQL queries for event listing
- `backend/app/browser/events.py` — Event log UI routes
- `backend/app/templates/browser/events/` — Event log templates (timeline, detail, diff views)
- `backend/app/events/store.py` — EventStore.commit() with operation types
- `backend/app/commands/handlers/` — body_set.py handler
- `frontend/static/js/workspace-layout.js` — Dockview layout management, `toJSON()`/`fromJSON()`
- `backend/app/services/settings.py` — SettingsService (user settings storage)
- `backend/app/canvas/service.py` — CanvasService pattern for JSON document storage in user_settings table

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- New requirements: EVTLOG-01 (autocomplete/labels), EVTLOG-02 (helptext), EVTLOG-03 (body.diff), PERSONA-01 (named personas), PERSONA-02 (persona switching)

## Scope

### In Scope

**Event Log Polish:**
- Predicate/type/object IRI → human-readable label resolution in event log views
- Helptext tooltips on event log fields (sourced from SHACL shape annotations where available)
- Autocomplete for event log filter fields (type filter, predicate filter, object search)
- Inline diff rendering for body changes (addition/deletion highlighting)

**Body Diff:**
- New `body.diff` command type storing incremental text diffs
- Diff computation in the body update handler (compare old vs new, store delta)
- Event log viewer renders diffs with syntax highlighting (green/red)
- Backward compatibility: existing `body.set` events display as before

**Personas:**
- Persona CRUD (create, rename, delete, switch)
- Each persona stores: dockview layout JSON, sidebar panel positions, explorer mode, user settings overrides
- Persona selector in user menu (bottom of sidebar)
- Ctrl+K command palette entries for persona switching
- Default persona created automatically on first use
- Storage in SQLite (user_settings or dedicated table)

### Out of Scope / Non-Goals

- Event log full-text search (separate feature)
- Collaborative personas (shared between users)
- Persona-specific Mental Model selection
- Real-time diff preview during editing (diffs are computed on save)
- CRDT-based collaborative editing

## Technical Constraints

- Event log labels must use LabelService for consistency with rest of app
- Body diffs must be reversible (support undo via compensating events)
- Persona layout JSON must be validated before restore (graceful fallback on schema mismatch)
- Frontend: htmx + vanilla JS (no React)
- SQLite for persona storage (same layer as auth/settings)

## Integration Points

- **LabelService** — resolve IRIs to human labels in event log
- **ShapesService** — source helptext from SHACL sh:description annotations
- **EventStore** — new body.diff operation type
- **EventQueryService** — enhanced queries returning label-enriched results
- **Dockview** — layout serialization/deserialization for persona switching
- **SettingsService** — persona settings overrides layered on top of user settings
- **Command Palette** — persona switching commands

## Open Questions

- **Diff granularity** — Line-level diffs or word-level diffs? Line-level is simpler and works well for markdown. Word-level is more precise but harder to render clearly. Current thinking: line-level for v1.
- **Persona settings scope** — Should personas override all user settings or just layout-related ones? Current thinking: layout (dockview, sidebar, explorer mode) + a subset of display settings (theme, density). Core settings (auth, LLM config) stay global.
- **Body.diff storage format** — Unified diff format? Custom delta encoding? JSON patch? Current thinking: unified diff (standard, readable, well-supported by libraries).
