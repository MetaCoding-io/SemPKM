# Phase 53: SPARQL Power User - Context

**Gathered:** 2026-03-09
**Status:** Ready for planning

<domain>
## Phase Boundary

Power users get a productive SPARQL workflow with persistent server-side history, saved/named queries, ontology-aware autocomplete, and rich IRI pill display in results. This phase replaces the existing Yasgui-based SPARQL console with a custom-built interface using CodeMirror 6. Query sharing and nav tree promotion are separate phases (Phase 54).

</domain>

<decisions>
## Implementation Decisions

### SPARQL Console Location & Architecture
- **Replace Yasgui entirely** with a custom-built SPARQL interface using CodeMirror 6 (already used for the Markdown body editor in `editor.js`)
- **Single location:** workspace bottom panel, new SPARQL tab alongside Event Log, Inference, etc.
- **Remove the admin `/admin/sparql` page** — the sidebar nav link should point to the workspace with the SPARQL panel auto-opened
- **Role gating carries forward from Phase 52:** guest has no SPARQL tab, member queries current graph only, owner has full access

### Panel Layout
- **Hybrid side-by-side + cell history layout:**
  - Top section: editor on the left, current results table on the right (side-by-side split)
  - Bottom section: scrollable cell history showing previous query+result pairs from this session
  - Cell history items show query snippet + row count, collapsed by default, expandable on click
- **Cell history is session-only** — cleared on page reload. Server-side history (dropdown) is the persistent record
- **Toolbar above editor:** Run, Save, History dropdown, Saved dropdown buttons

### Query History
- **Server-side persistence** — every query execution saves to server-side history (replaces Yasgui's localStorage-only approach)
- **Auto-save on every execution** — duplicate consecutive queries are deduplicated (only timestamp updates)
- **History dropdown** in toolbar shows recent queries with relative timestamp + first-line preview
- **100 most recent** queries kept per user, older entries pruned automatically
- Click a history entry to load it into the editor

### Saved Queries
- **Separate toolbar dropdown** from history (two distinct buttons: History and Saved)
- **Save button** in toolbar prompts for name + optional description, saves current editor query
- **Star from history** — each history dropdown entry has a star icon; clicking it prompts for a name and promotes it to saved
- Saved queries stored server-side, accessible from any device after login

### IRI Pill Design
- **Icon + label chip** — compact rounded chip with type icon (from IconService/Mental Model manifest) on left, resolved label on right
- **Object IRIs only** — only SemPKM objects get pill treatment. Vocabulary IRIs (rdf:type, dcterms:title, owl:Class) render as compact QNames in plain text
- **Backend batch resolve** — after query execution, backend collects unique object IRIs from results, batch-resolves labels+types via LabelService, returns enriched result data. No frontend flicker.
- **Click opens workspace tab** — clicking a pill calls `openTab(iri, label)`, standard workspace behavior
- **Hover shows full IRI** as tooltip

### Ontology Autocomplete
- **Always-on (aggressive)** — suggestions appear as the user types any token, not just after prefix colons
- **Full SPARQL awareness** — suggests PREFIX declarations, classes, predicates from installed Mental Models, SPARQL keywords (SELECT, WHERE, FILTER, OPTIONAL, etc.), and previously-used variable names
- **Type badges in dropdown** — each suggestion shows a badge: C for class, P for predicate, D for datatype, K for keyword. Helps distinguish `bpkm:Note` (class) from `bpkm:name` (predicate)
- **API endpoint, cached client-side** — new endpoint returns all prefixes, classes, and predicates from installed Mental Models. Editor fetches once on load, caches in memory, refreshes when models change

### Claude's Discretion
- Exact CodeMirror 6 SPARQL language package choice (e.g., `@codemirror/lang-sparql` or custom grammar)
- Split ratio between editor and results panes
- Cell history expansion animation and styling
- How to detect model changes for autocomplete cache invalidation
- Result table styling (borders, row hover, column widths)
- Keyboard shortcut for running queries (Ctrl+Enter is standard)

</decisions>

<specifics>
## Specific Ideas

- "Take inspiration from Neo4j Browser and how its interface works, similar to Jupyter notebooks using cells" — the hybrid layout with session cell history below the active editor/results captures this
- User does not like Yasgui's look — the custom-built approach should feel native to SemPKM's design language
- CodeMirror 6 is already in the codebase (`editor.js` imports from `esm.sh/@codemirror/view@6`) — reuse the same CDN pattern

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `frontend/static/js/editor.js`: CodeMirror 6 Markdown editor — reference implementation for CM6 integration pattern (ESM imports from esm.sh CDN)
- `backend/app/services/labels.py`: LabelService with `resolve_batch()` — use for batch IRI label resolution in SPARQL results
- `backend/app/sparql/client.py`: `inject_prefixes()`, `scope_to_current_graph()`, `check_member_query_safety()` — existing SPARQL processing pipeline
- `backend/app/sparql/router.py`: `_enforce_sparql_role()` — role gating already implemented (Phase 52)
- `backend/app/templates/admin/sparql.html`: Current Yasgui implementation with `isSemPKMObjectIri()` and `shortenSemPkmIri()` — logic to port to custom implementation
- `frontend/static/js/workspace.js`: `openTab(iri, label)` — standard function for opening workspace tabs from IRI clicks
- IconService + Mental Model manifest `icon` declarations — existing per-type icon resolution

### Established Patterns
- Bottom panel tab system in `workspace.js`: `initPanelTabs()`, `panelState`, `_applyPanelState()` — follow this pattern for the SPARQL tab
- CM6 loaded via ESM from `esm.sh` CDN — no npm/bundler step
- Backend services stored on `app.state.*` during lifespan startup, injected via FastAPI dependencies
- Auth: SQLAlchemy models for user-scoped data (sessions, settings) — same pattern for query history/saved queries

### Integration Points
- `workspace.html`: Add SPARQL tab button to `.panel-tab-bar` (conditionally hidden for guests via template logic)
- `workspace.js`: Extend `_applyPanelState()` for SPARQL tab initialization (lazy-load CM6 on first open)
- `sparql/router.py`: New endpoints for history CRUD and saved queries CRUD
- `theme.css`: Dark mode overrides for CM6 SPARQL editor (replace Yasgui dark mode rules)
- New SQLAlchemy models for `SparqlQueryHistory` and `SavedSparqlQuery` (user-scoped, in existing SQLite/PostgreSQL)
- New API endpoint for ontology vocabulary (prefixes, classes, predicates from model graphs)

</code_context>

<deferred>
## Deferred Ideas

- **AI Query Helper** — A button (lightbulb/copilot icon) that opens a dialog where users describe what they want to query in natural language, and the connected LLM generates SPARQL. The LLM infrastructure exists (Fernet-encrypted key, SSE streaming proxy). Could be its own phase or added to a future SPARQL enhancement.
- **Query sharing** — Phase 54 (SPARQL Advanced)
- **Promoted queries as nav tree views** — Phase 54 (SPARQL Advanced)

</deferred>

---

*Phase: 53-sparql-power-user*
*Context gathered: 2026-03-09*
