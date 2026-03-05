# Phase 37: Global Lint Data Model & API - Context

**Gathered:** 2026-03-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Per-object, per-result SHACL validation detail stored in a queryable format with paginated API endpoints for listing results. Results update automatically after each EventStore.commit() via AsyncValidationQueue. Per-object lint panel migrated to use the new data layer. Global lint dashboard UI is Phase 38 (separate).

</domain>

<decisions>
## Implementation Decisions

### Storage approach
- Triplestore-native — all validation result data stays in RDF4J, consistent with the rest of SemPKM's architecture
- Per-run named graphs — each validation run gets its own named graph for structured results (natural history boundary)
- Keep all runs — full audit trail, never delete. Future "Tidy" admin panel will handle cleanup (see Deferred Ideas)
- Store both raw and structured — raw pyshacl report graph preserved for fidelity, structured result triples stored alongside for querying

### API response shape
- Layered detail — default response is human-readable (object label, severity, message, property path label); `?detail=full` query param adds raw SHACL metadata (focus_node IRI, source_shape, constraint_component)
- Inline label resolution — API returns `object_label`, `object_type_label` resolved server-side alongside IRIs. One request gets everything the UI needs
- Offset-based pagination — `?page=1&per_page=50`, simple and familiar
- Minimum viable filters — `?severity=Violation&object_type=<iri>` plus pagination. Search/sort deferred to Phase 38 when dashboard UI needs them

### Result lifecycle
- Latest by default, optional `?run_id=<iri>` for historical run queries
- Basic diff endpoint — `GET /api/lint/diff` returns `new_issues[]` and `resolved_issues[]` comparing latest vs previous run
- Dedicated `GET /api/lint/status` endpoint for lightweight polling (timestamp, counts, conforms)
- Track source model explicitly per result (which Mental Model contributed the shape)
- On model uninstall: keep results, mark as orphaned (source shape no longer installed)
- Tag trigger source on each run — 'user_edit', 'inference', 'manual', etc.

### API namespace
- New `/api/lint/*` namespace — clean separation from existing validation endpoints
- Endpoints: `/api/lint/results`, `/api/lint/status`, `/api/lint/diff`, `/api/lint/stream`
- Remove old `/api/validation/latest` and `/api/validation/{event_id}` endpoints entirely

### Backward compatibility
- Migrate per-object lint panel to query new structured results (filtered by focus_node). One source of truth
- Replace 10s polling with SSE push — server sends event when validation run completes
- Single global SSE stream (`/api/lint/stream`) — broadcasts 'validation_complete' events. Both global dashboard (Phase 38) and per-object panel subscribe and filter client-side

### Claude's Discretion
- Structured result triple schema design (predicates, datatypes, naming)
- SPARQL query optimization for filtered result retrieval
- SSE implementation details (reconnection, heartbeat)
- How orphaned results are visually distinguished (Phase 38 UI concern, but data model should support it)
- Diff algorithm for comparing runs (matching strategy for "same" vs "new" vs "resolved" results)

</decisions>

<specifics>
## Specific Ideas

- SSE upgrade from polling is a meaningful UX improvement — validation results appear instantly instead of up to 10s delay
- Diff endpoint enables Phase 38 to show "3 new issues, 2 resolved since last run" in the dashboard
- Source model tracking enables future per-model lint health views
- Trigger source tagging lets users understand why results changed (was it their edit, or an inference run?)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ValidationResult` dataclass (`backend/app/validation/report.py`): Already has `focus_node`, `severity`, `path`, `message`, `source_shape`, `constraint_component` — directly maps to structured result triples
- `ValidationReport.from_pyshacl()`: Parses raw pyshacl report graph via SPARQL — can be extended to also write structured triples
- `AsyncValidationQueue` (`backend/app/validation/queue.py`): Already fires after each EventStore.commit(), has `on_complete` callback hook — SSE broadcast can plug in here
- `_rdf_term_to_sparql()` and `_turtle_to_ntriples()` helpers in `validation.py` for SPARQL INSERT DATA

### Established Patterns
- Named graph per data category: `urn:sempkm:current`, `urn:sempkm:validations`, `urn:sempkm:inferred` — new lint graphs follow this pattern
- Summary triples via `to_summary_triples()` method on report dataclass
- FastAPI router with `APIRouter(prefix="/api")` — new lint router follows same pattern
- `get_current_user` dependency for auth on all API endpoints
- Existing SSE pattern: LLM streaming proxy uses SSE (`backend/app/services/llm.py`)

### Integration Points
- `AsyncValidationQueue._worker()` — after validation completes, write structured results + broadcast SSE
- `backend/app/validation/router.py` — will be replaced by new `/api/lint/*` router
- `backend/app/templates/browser/lint_panel.html` — htmx partial to migrate from polling to SSE + new data source
- `backend/app/dependencies.py` — wire up new lint service/router
- `backend/app/main.py` — register new router, remove old validation router

</code_context>

<deferred>
## Deferred Ideas

- **"Tidy" admin panel** — Future admin page for triplestore cleanup options: prune old validation runs, clear inferred triples, compact graphs. Separate phase.
- Search/sort filters on lint results — Phase 38 when dashboard UI needs them
- Per-model lint health breakdown view — future enhancement leveraging source_model tracking

</deferred>

---

*Phase: 37-global-lint-data-model-api*
*Context gathered: 2026-03-05*
