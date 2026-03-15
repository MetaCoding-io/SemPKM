# M005/S02 — Research: Operations Log & PROV-O Foundation

**Date:** 2026-03-14  
**Status:** Complete

## Summary

The operations log introduces SemPKM's first production use of PROV-O vocabulary, storing structured `prov:Activity` entries in a dedicated `urn:sempkm:ops-log` named graph. The core deliverable is an `OperationsLogService` with a `log_activity()` method, called from model install/remove, inference runs, and validation runs — the three system activities that currently log only to Docker stdout.

The approach is low-risk because every building block already exists: the `PROV` namespace is registered in `namespaces.py`, `prov:startedAtTime` is already used in `QueryService` for query execution timestamps (S01 precedent), the `TriplestoreClient` has all needed SPARQL methods, and the admin UI has an established template pattern with sidebar navigation. The primary design question — single shared graph vs per-entry graphs — is resolved in favor of a single `urn:sempkm:ops-log` graph, matching the `urn:sempkm:queries` pattern from S01.

The operations log establishes PROV-O usage patterns that S06 (PROV-O Alignment Design) will audit. By keeping to the PROV-O "Starting Point" terms only (`prov:Activity`, `prov:wasAssociatedWith`, `prov:startedAtTime`, `prov:endedAtTime`), we get W3C compliance without vocabulary overhead.

## Recommendation

Build an `OperationsLogService` as a new service module at `backend/app/services/ops_log.py` following the existing service singleton pattern (instantiate in `main.py` lifespan, inject via `dependencies.py`). Store all entries in `urn:sempkm:ops-log` named graph. Create an admin UI page at `/admin/ops-log` with the sidebar navigation entry under the Admin section.

Use PROV-O "Starting Point" terms only:
- `prov:Activity` as the `rdf:type`
- `prov:startedAtTime` for when the activity started
- `prov:endedAtTime` for when the activity completed
- `prov:wasAssociatedWith` for the actor (user IRI or `urn:sempkm:system`)
- `prov:used` for related resources (model IRI, etc.)

Extend with two SemPKM-specific predicates:
- `sempkm:activityType` — machine-readable sub-type (e.g., `model.install`, `inference.run`, `validation.run`)
- `rdfs:label` — human-readable description

IRI pattern: `urn:sempkm:ops-log:{uuid}` for each activity entry.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| PROV-O namespace | `app.rdf.namespaces.PROV` | Already registered; `prov:startedAtTime` already used in QueryService |
| IRI minting | `uuid.uuid4()` pattern from `app.rdf.iri` | Same pattern as events, queries — just different prefix |
| SPARQL writes | `TriplestoreClient.update()` | INSERT DATA to named graph — same pattern as QueryService, EventStore |
| SPARQL reads | `TriplestoreClient.query()` | SELECT with pagination — same pattern as EventQueryService |
| Admin UI templates | `admin/index.html`, `admin/models.html` | Extends `base.html`, `dashboard-layout` class, htmx partial rendering |
| Service injection | `dependencies.py` DI pattern | Singleton on `app.state`, FastAPI `Depends()` |
| System actor IRI | `urn:sempkm:system` from `events/models.py` | Already defined as `SYSTEM_ACTOR_IRI` |
| Timestamp formatting | `datetime.now(timezone.utc).isoformat()` | Same pattern used everywhere in EventStore/QueryService |

## Existing Code and Patterns

### Services to Instrument

- `backend/app/services/models.py` — `ModelService.install()` (line 232) and `ModelService.remove()` (line 395). Both return result objects with `success` flag and timing. Instrument after success/failure to log the activity with duration.
- `backend/app/inference/service.py` — `InferenceService.run_inference()` (line 74). Already has `run_timestamp` and logs an event via `_log_inference_event()` (line 588). Instrument alongside the existing event log.
- `backend/app/validation/queue.py` — `AsyncValidationQueue._worker()`. Logs validation completion at line ~120. Add ops log entry after validation completes.

### Patterns to Follow

- `backend/app/sparql/query_service.py` — **Primary reference pattern.** Single `urn:sempkm:queries` graph for all queries. Uses raw SPARQL strings (not rdflib objects) for INSERT DATA and SELECT. Uses `_dt()` helper for xsd:dateTime formatting. Already uses `prov:startedAtTime` (line 33). Follow this pattern exactly.
- `backend/app/events/query.py` — `EventQueryService.list_events()`. Cursor-paginated SPARQL with `ORDER BY DESC(?timestamp) LIMIT N+1` pattern for next-page detection. Reuse for ops log pagination.
- `backend/app/events/models.py` — `SYSTEM_ACTOR_IRI = URIRef("urn:sempkm:system")`. Use this for system-initiated activities (model auto-install, validation queue runs).
- `backend/app/dependencies.py` — DI pattern for all services. Add `get_ops_log_service()`.
- `backend/app/main.py` lifespan — Service instantiation pattern: `ops_log_service = OperationsLogService(client)` → `app.state.ops_log_service = ops_log_service`.

### Admin UI Patterns to Follow

- `backend/app/admin/router.py` — Admin routes with `require_role("owner")`, htmx partial rendering, `templates_response()` helper. New `/admin/ops-log` endpoint follows this pattern.
- `backend/app/templates/admin/index.html` — Dashboard cards layout. Add an "Operations Log" card linking to `/admin/ops-log`.
- `backend/app/templates/components/_sidebar.html` — Admin group has Mental Models, Users (disabled), Teams (disabled), Webhooks. Add Operations Log nav link after Webhooks.

## RDF Data Model

```turtle
@prefix prov: <http://www.w3.org/ns/prov#> .
@prefix sempkm: <urn:sempkm:> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Model install activity
<urn:sempkm:ops-log:a1b2c3d4> a prov:Activity ;
    sempkm:activityType "model.install" ;
    rdfs:label "Installed model 'basic-pkm' v1.2.0" ;
    prov:startedAtTime "2026-03-14T10:30:00Z"^^xsd:dateTime ;
    prov:endedAtTime "2026-03-14T10:30:02Z"^^xsd:dateTime ;
    prov:wasAssociatedWith <urn:sempkm:user:owner-uuid> ;
    prov:used <urn:sempkm:model:basic-pkm> .

# Inference run (system-initiated)
<urn:sempkm:ops-log:e5f6g7h8> a prov:Activity ;
    sempkm:activityType "inference.run" ;
    rdfs:label "Inference: 42 triples inferred (38 new, 2 dismissed, 2 promoted)" ;
    prov:startedAtTime "2026-03-14T10:35:00Z"^^xsd:dateTime ;
    prov:endedAtTime "2026-03-14T10:35:05Z"^^xsd:dateTime ;
    prov:wasAssociatedWith <urn:sempkm:user:owner-uuid> .

# Validation run (system/queue)
<urn:sempkm:ops-log:i9j0k1l2> a prov:Activity ;
    sempkm:activityType "validation.run" ;
    rdfs:label "Validation: conforms=true, 0 violations, 1 warning" ;
    prov:startedAtTime "2026-03-14T10:35:06Z"^^xsd:dateTime ;
    prov:endedAtTime "2026-03-14T10:35:07Z"^^xsd:dateTime ;
    prov:wasAssociatedWith <urn:sempkm:system> .

# Failed model install
<urn:sempkm:ops-log:m3n4o5p6> a prov:Activity ;
    sempkm:activityType "model.install" ;
    rdfs:label "Failed to install model 'bad-model': Manifest error" ;
    sempkm:status "failed" ;
    sempkm:errorMessage "Manifest error: missing modelId field" ;
    prov:startedAtTime "2026-03-14T10:40:00Z"^^xsd:dateTime ;
    prov:endedAtTime "2026-03-14T10:40:00Z"^^xsd:dateTime ;
    prov:wasAssociatedWith <urn:sempkm:user:owner-uuid> .
```

## Graph Organization

**Single graph: `urn:sempkm:ops-log`**

Rationale:
- Matches `urn:sempkm:queries` pattern from S01 (same team, same codebase)
- Log entries are simple metadata records — no data triples to isolate
- Single graph simplifies querying (no `GRAPH ?g` scanning)
- Low volume: model installs, inference runs, validation runs — maybe 10-50 entries/day max
- Filtering by `sempkm:activityType` or `prov:wasAssociatedWith` is trivial in a single graph

## Service API

```python
class OperationsLogService:
    """RDF-backed operations log using PROV-O vocabulary."""

    def __init__(self, client: TriplestoreClient) -> None:
        self._client = client

    async def log_activity(
        self,
        activity_type: str,           # e.g. "model.install"
        label: str,                    # Human-readable description
        actor: str | None = None,      # User IRI or None (→ system)
        used: list[str] | None = None, # Related resource IRIs
        status: str = "success",       # "success" or "failed"
        error_message: str | None = None,
        started_at: str | None = None, # ISO timestamp, defaults to now
        ended_at: str | None = None,   # ISO timestamp, defaults to now
    ) -> str:
        """Log a PROV-O activity entry. Returns the activity IRI."""

    async def list_activities(
        self,
        cursor: str | None = None,     # Cursor timestamp for pagination
        activity_type: str | None = None,  # Filter by type
        limit: int = 50,
    ) -> tuple[list[dict], str | None]:
        """Return paginated activities in reverse chronological order."""

    async def get_activity(self, activity_iri: str) -> dict | None:
        """Return details for a single activity."""

    async def count_activities(self) -> int:
        """Return total number of logged activities."""
```

## Activity Types

| Activity Type | Emitted By | When | Related Resources |
|---------------|-----------|------|-------------------|
| `model.install` | `ModelService.install()` | After install success/failure | `urn:sempkm:model:{id}` |
| `model.remove` | `ModelService.remove()` | After remove success/failure | `urn:sempkm:model:{id}` |
| `inference.run` | `InferenceService.run_inference()` | After inference completes | (none) |
| `validation.run` | `AsyncValidationQueue._worker()` | After validation completes | (none) |
| `model.auto-install` | `ensure_starter_model()` | On startup auto-install | `urn:sempkm:model:{id}` |

Future candidates (not in S02 scope):
- `import.obsidian` — Obsidian vault import
- `ontology.create-class` — user class creation
- `federation.sync` — federation sync runs

## Integration Points

### 1. ModelService (highest priority)

In `backend/app/services/models.py`, instrument `install()` and `remove()`:

```python
# In install() — after success
await self._ops_log.log_activity(
    activity_type="model.install",
    label=f"Installed model '{model_id}' v{manifest.version}",
    actor=actor_iri,  # Need to thread user IRI through
    used=[f"urn:sempkm:model:{model_id}"],
)
```

**Challenge:** `ModelService.install()` currently has no reference to the calling user. The admin router calls `model_service.install(Path(path))` without passing user context. Two options:
- Option A: Pass `performed_by: str | None` parameter to `install()` / `remove()`
- Option B: Inject `OperationsLogService` into the admin router and log there instead of in the service

**Recommendation: Option B** — log in the router, not the service. The router already has the `user` from `require_role("owner")`. This avoids threading user context through every service method and is consistent with how `EventStore.commit()` receives `performed_by` from the router layer.

### 2. InferenceService

In `backend/app/inference/service.py`, `_log_inference_event()` already logs via EventStore. Add ops log alongside:

```python
await self._ops_log.log_activity(
    activity_type="inference.run",
    label=description,
    actor=user_iri,
)
```

**Challenge:** `InferenceService` also doesn't receive user context — it's called from `inference/router.py` which does have the user. Same solution: log in the router.

### 3. ValidationQueue

In `backend/app/validation/queue.py`, the `_worker()` method has no user context (validation is triggered asynchronously). Use `urn:sempkm:system` as actor.

**Challenge:** The validation queue fires frequently (after every EventStore commit). Logging every validation run would create noise. Options:
- Log all validation runs (comprehensive but noisy)
- Log only validations that find violations (useful but incomplete)
- Log with coalescing note (e.g., "Validation run (3 coalesced)")

**Recommendation:** Log all validation runs. The ops log is for observability — users need to see that validation is happening even when it passes. Volume is manageable because validation coalesces (many events → one validation run).

### 4. Admin Router Integration

The admin router at `backend/app/admin/router.py` already handles model install/remove. Add ops log calls in `admin_models_install()` and `admin_models_remove()`.

## Admin UI Design

### Sidebar Navigation

Add to the Admin group in `_sidebar.html`, after Webhooks:

```html
<a href="/admin/ops-log" class="nav-link" data-tooltip="Operations Log"
   hx-get="/admin/ops-log" hx-target="#app-content" hx-swap="innerHTML" hx-push-url="true">
    <i data-lucide="activity" class="nav-icon"></i>
    <span class="nav-label">Operations Log</span>
</a>
```

### Page Layout

Follow the `admin/models.html` pattern:
- Page title "Operations Log"
- Lead text explaining what the log captures
- Filter bar: activity type dropdown + date range
- Reverse-chronological table with columns: Time, Activity, Actor, Status, Duration
- htmx pagination (load more button or infinite scroll)
- Click a row to expand details (related resources, error messages)

### Template Structure

```
backend/app/templates/admin/ops_log.html  — main page
```

Single template with expandable rows via htmx, no separate detail page needed.

## Constraints

- **No new Python dependencies** — everything uses existing `TriplestoreClient` and `rdflib` namespace objects
- **PROV namespace already registered** — `PROV = Namespace("http://www.w3.org/ns/prov#")` in `namespaces.py`, `"prov": str(PROV)` in `COMMON_PREFIXES`
- **Single write path for ops log** — direct SPARQL INSERT DATA, not EventStore. The ops log records _about_ system operations; it is not itself an event-sourced data stream
- **Owner role required** — ops log is admin/debug functionality, same access level as Event Console and Mental Models
- **Hot-reload safe** — service code is volume-mounted in Docker; template changes need no rebuild

## Common Pitfalls

- **Don't use EventStore for ops log entries** — EventStore creates per-event named graphs with materialization into `urn:sempkm:current`. The ops log is metadata _about_ operations, not data that belongs in the current state graph. Direct SPARQL INSERT DATA to `urn:sempkm:ops-log` is the correct pattern (same as QueryService writes to `urn:sempkm:queries`).
- **Don't type user IRIs as `prov:Agent`** — adding `rdf:type prov:Agent` to user IRIs would leak into other queries. Use `prov:wasAssociatedWith` without asserting the Agent type on the user resource. PROV-O doesn't require explicit Agent typing when using `prov:wasAssociatedWith`.
- **Don't thread user context through service methods** — log in the router layer where the user is already available via `require_role()`. This avoids changing service signatures and is consistent with existing patterns.
- **Don't forget to handle system-initiated activities** — model auto-install at startup has no user. Use `SYSTEM_ACTOR_IRI` (`urn:sempkm:system`) from `events/models.py`.
- **Don't paginate with OFFSET** — use cursor-based pagination (timestamp cursor) matching the `EventQueryService.list_events()` pattern. OFFSET-based pagination is slow on large result sets.

## Open Risks

- **Log volume over time** — if validation runs are logged (one per EventStore commit), the graph could grow to thousands of entries in heavy-use scenarios. Mitigation: implement a retention cap (e.g., keep last 1000 entries, delete oldest on insert). Can defer retention to a future slice if volume proves manageable.
- **User IRI threading for inference** — `InferenceService.run_inference()` is called from a router that has user context, but the service method doesn't accept it. Logging from the router is clean but means the service itself doesn't know its actor. Acceptable for S02; S06 (PROV-O Alignment) can revisit if needed.
- **Concurrent writes to single graph** — multiple simultaneous activities (e.g., validation + import) could write to `urn:sempkm:ops-log` concurrently. RDF4J handles concurrent graph writes safely at the statement level, but INSERT DATA to the same graph is atomic per request. No transaction needed for individual log entries.
- **PROV-O vocabulary subset may prove too minimal for S06** — we're using only Starting Point terms. If S06 finds we need Qualified patterns (e.g., `prov:qualifiedAssociation` to record roles), the data model would need extension. Low risk: the Starting Point terms are explicitly designed to be sufficient for basic provenance.

## Requirements Mapping

This slice has no Active requirements listed in `REQUIREMENTS.md` yet. The following requirements should be created:

| Proposed ID | Description | Class |
|-------------|-------------|-------|
| LOG-01 | Operations log stores timestamped PROV-O Activity entries in the triplestore | core-capability |
| LOG-02 | Operations log captures model install, model remove, inference run, and validation run | core-capability |
| LOG-03 | Admin UI renders operations log with filtering by activity type | admin/support |

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| PROV-O / RDF provenance | (none found) | No relevant skill — domain is W3C standard, well-documented |
| RDF triplestore / SPARQL | `letta-ai/skills@sparql-university` | Available (38 installs) — not needed, existing codebase has extensive SPARQL patterns |
| FastAPI | `thebushidocollective/han@fastapi-async-patterns` | Available (404 installs) — not needed, codebase already uses FastAPI patterns extensively |

No skills recommended for installation — all patterns are well-established in the existing codebase.

## Sources

- PROV-O Starting Point terms (`prov:Activity`, `prov:wasAssociatedWith`, `prov:startedAtTime`, `prov:endedAtTime`) provide complete coverage for operations log entries (source: [PROV-O: The PROV Ontology](https://www.w3.org/TR/prov-o/))
- `prov:startedAtTime` is already used in the codebase at `backend/app/sparql/query_service.py:33` for query execution timestamps (source: codebase exploration)
- PROV namespace registered at `backend/app/rdf/namespaces.py:22` with `COMMON_PREFIXES` entry (source: codebase exploration)
- `SYSTEM_ACTOR_IRI` defined at `backend/app/events/models.py:26` for system-initiated operations (source: codebase exploration)
- Single-graph approach for shared data validated by S01's `urn:sempkm:queries` pattern in `QueryService` (source: codebase exploration)
