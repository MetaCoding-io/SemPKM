# S03: Lint Filter System (Suppress, Dismiss, Presets) — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

S03 builds a lint filter system with three capabilities: suppress by rule type (hide all results from a SHACL source shape), dismiss individual results (specific object × rule combination), and named filter presets (save/restore sets of suppressions). This is a standard CRUD subsystem with SQLite persistence, REST API endpoints, and htmx UI integration.

The existing `LintService` already exposes `source_shape` on every result item — this is the stable identifier needed for both suppressions and dismissals. The service queries SPARQL for results and returns Pydantic models. Python post-filtering (exclude suppressed/dismissed after SPARQL returns) is the right approach per D279. The established patterns from `PersonaService` (async session factory, dataclass read models, JSON API + htmx browser routes) and `UserFavorite` (simple FK + IRI model) provide clear templates to follow.

## Recommendation

**Build in this order: DB models + migration → filter service CRUD → extend LintService filtering → API endpoints → lint panel UI (dismiss buttons, suppress controls) → lint dashboard UI (filter indicators) → lint settings page/section.**

The DB layer and service CRUD are independent of the UI. The LintService extension is a surgical change — add optional `suppressed_rules` and `dismissed_pairs` parameters to `get_results()` and `get_results_for_object()`, then filter in Python after the SPARQL query returns. UI work splits naturally into three areas: per-object lint panel (dismiss buttons), global lint dashboard (suppress controls, preset selector), and a settings management section.

## Implementation Landscape

### Key Files

- `backend/app/lint/service.py` — `LintService` with `get_results()` and `get_results_for_object()`. Both already return `source_shape` per result. **Must be extended** to accept optional suppression/dismissal filter lists and exclude matching results in Python post-processing. The `get_results()` count query must also exclude filtered results for correct pagination.

- `backend/app/lint/router.py` — REST API at `/api/lint/` with results, status, diff, stream endpoints. **Must be extended** with new endpoints for suppress/dismiss/preset CRUD. Must also wire the user's active suppressions/dismissals into `get_results()` calls.

- `backend/app/lint/models.py` — Pydantic response models. **Must add** request/response models for suppress, dismiss, and preset operations.

- `backend/app/lint/filter_service.py` — **New file.** CRUD service for suppressions, dismissals, and presets following the `PersonaService` pattern (async session factory, dataclass read models).

- `backend/app/lint/filter_models.py` — **New file.** SQLAlchemy ORM models for `lint_suppressions`, `lint_dismissals`, `lint_presets` tables following `UserFavorite` and `Persona` patterns.

- `backend/migrations/versions/015_lint_filters.py` — **New file.** Alembic migration creating 3 tables. Next sequential number after `014_app_tables.py`.

- `backend/app/templates/browser/lint_panel.html` — Per-object right-pane lint panel. **Must add** dismiss buttons per result item (small × or "dismiss" link). Each result already has `source_shape` available via the template context.

- `backend/app/templates/browser/lint_dashboard.html` — Global lint dashboard in bottom panel. **Must add** suppress controls (per-rule-type toggle or button), preset selector dropdown, suppression indicators on filtered results. Sidebar already has severity/type/search/sort filters — suppress and preset controls fit here.

- `backend/app/main.py` — Wires services into `app.state`. **Must add** `lint_filter_service` instantiation with session factory, similar to `persona_service`.

- `backend/app/dependencies.py` — FastAPI dependency injection. **Must add** `get_lint_filter_service` dependency getter.

- `backend/app/db/base.py` — `DeclarativeBase` for all ORM models. No changes needed — new models import `Base` from here.

### Existing Patterns to Follow

**SQLAlchemy model pattern** (`backend/app/favorites/models.py`):
- UUID primary key, `user_id` FK to `users.id` with CASCADE
- `String(2048)` for IRI columns
- `DateTime(timezone=True)` with `server_default=func.now()`
- `UniqueConstraint` for natural key dedup

**Service pattern** (`backend/app/persona/service.py`):
- Constructor takes `session_factory` (async context manager)
- All methods are `async`, use `async with self._session_factory() as session:`
- Dataclass read models for API responses
- Authorization by `user_id` match on all operations

**Router pattern** (`backend/app/persona/router.py`):
- JSON API routes at `/api/lint/` prefix
- Browser routes at `/browser/lint-*` for htmx partials
- `_get_service(request)` helper from `request.app.state`
- `get_current_user` dependency for auth

### SQLAlchemy Models (3 tables)

```python
# lint_suppressions — suppress all results from a rule type
class LintSuppression(Base):
    __tablename__ = "lint_suppressions"
    id: UUID PK
    user_id: UUID FK users.id CASCADE
    rule_source_iri: String(2048)  # sh:sourceShape IRI
    created_at: DateTime
    UniqueConstraint("user_id", "rule_source_iri")

# lint_dismissals — dismiss one object×rule combination
class LintDismissal(Base):
    __tablename__ = "lint_dismissals"
    id: UUID PK
    user_id: UUID FK users.id CASCADE
    object_iri: String(2048)      # focus node IRI
    rule_source_iri: String(2048)  # sh:sourceShape IRI
    created_at: DateTime
    UniqueConstraint("user_id", "object_iri", "rule_source_iri")

# lint_presets — named filter preset (list of suppressed rules)
class LintPreset(Base):
    __tablename__ = "lint_presets"
    id: UUID PK
    user_id: UUID FK users.id CASCADE
    name: String(255)
    suppressed_rules_json: Text  # JSON array of rule IRIs
    created_at: DateTime
    updated_at: DateTime
    UniqueConstraint("user_id", "name")
```

### API Endpoints

New endpoints on `/api/lint/`:
- `POST /api/lint/suppress` — body: `{rule_source_iri}` → add suppression
- `DELETE /api/lint/suppress/{id}` — remove one suppression
- `GET /api/lint/suppressions` — list active suppressions for user
- `DELETE /api/lint/suppressions` — clear all suppressions
- `POST /api/lint/dismiss` — body: `{object_iri, rule_source_iri}` → dismiss
- `DELETE /api/lint/dismiss/{id}` — un-dismiss
- `GET /api/lint/dismissals` — list active dismissals for user
- `DELETE /api/lint/dismissals` — clear all dismissals
- `POST /api/lint/presets` — body: `{name, suppressed_rules: [...]}` → create
- `GET /api/lint/presets` — list presets
- `PUT /api/lint/presets/{id}` — update preset name or rules
- `DELETE /api/lint/presets/{id}` — delete preset
- `POST /api/lint/presets/{id}/apply` — apply preset (replace user's suppressions with preset's list)

### LintService Filtering Extension

The core filtering logic is Python post-processing in `get_results()` and `get_results_for_object()`:

```python
# In get_results(), after SPARQL returns results:
if suppressed_rules:
    items = [i for i in items if i.source_shape not in suppressed_rules]
if dismissed_pairs:
    items = [i for i in items if (i.focus_node, i.source_shape) not in dismissed_pairs]
```

**Important nuance:** For `get_results()` with pagination, the count query and result query both need post-filtering. Two approaches:
1. **Over-fetch + Python filter + re-paginate** — simpler, works for typical result sets (50-200 results). Fetch all, filter, slice.
2. **Two-pass** — first get all result fingerprints, filter, then paginate the IDs. More complex.

Recommendation: **Over-fetch approach** for v1. The lint dashboard already fetches per-page (max 200). With typical result sets under 200, fetching all and filtering in Python is acceptable. If results grow beyond 200, pagination may show fewer items per page — acceptable for v1.

For `get_results_for_object()` there's no pagination — simply filter the returned list.

### UI Changes

**Lint panel (per-object, right pane):**
- Add a small dismiss button (×) next to each warning/info result
- Dismiss button calls `POST /api/lint/dismiss` via fetch(), then re-fetches the lint panel via htmx
- Dismissed results disappear immediately
- Show a small "N dismissed" indicator if any dismissals exist for this object

**Lint dashboard (global, bottom panel):**
- Add a "suppress" button/icon in each result row (or on the severity column)
- Add a preset selector dropdown in the sidebar filters area
- Add "Manage Filters" link to the lint settings section
- Show suppression indicators (e.g., "3 rules suppressed" badge)

**Lint settings (new section/page):**
- Accessible from lint dashboard sidebar or admin area
- List all active suppressions with rule name and remove button
- List all active dismissals grouped by object with remove button
- Preset management: list, create, rename, delete
- "Clear all suppressions" and "Clear all dismissals" bulk actions

### Build Order

1. **SQLAlchemy models + Alembic migration** — `filter_models.py` + `015_lint_filters.py`. Zero dependencies, pure schema.
2. **LintFilterService CRUD** — `filter_service.py` with all suppress/dismiss/preset operations. Unit-testable without Docker.
3. **Wire into main.py + dependencies.py** — register service on `app.state`.
4. **API endpoints** — extend `router.py` with new CRUD endpoints. Test with curl.
5. **Extend LintService** — add filtering parameters to `get_results()` and `get_results_for_object()`. Wire user's filters into router calls.
6. **Lint panel UI** — dismiss buttons on lint_panel.html + JS handler.
7. **Lint dashboard UI** — suppress controls, preset selector, filter indicators.
8. **Lint settings UI** — management page/section for suppressions, dismissals, presets.

### Verification Approach

**Unit tests (no Docker):**
- LintFilterService CRUD: create/list/delete suppressions, dismissals, presets. Apply preset.
- LintService filtering: mock SPARQL results, verify suppressed rules excluded, dismissed pairs excluded.
- Preset apply: verify suppressions match preset's list after apply.

**Integration (Docker):**
- Create objects with known lint issues → see warnings in lint panel
- Dismiss a specific warning → that warning disappears, others remain
- Suppress a rule type → all results for that rule disappear
- Save preset → switch away → switch back → same suppressions restored
- Clear all → previously hidden results reappear
- Lint settings page shows all active filters with management controls

## Constraints

- Lint filter storage must be in SQLite (not RDF) per D279 — user preferences, not knowledge graph data
- Server-side Python filtering per D279 — SPARQL results filtered after query returns
- Additive suppression model per D280 — presets store what to hide, not what to show
- Frontend is htmx + vanilla JS — no React/Vue for filter UI
- `source_shape` IRI is the stable identifier for rule types — already exposed by LintService
- Pagination with filtering: over-fetch approach acceptable for v1 result volumes

## Common Pitfalls

- **Pagination count mismatch** — If `get_results()` filters after SPARQL pagination, the total count in the response header won't match the actual returned items. Must either (a) over-fetch and re-paginate in Python, or (b) adjust the count query to exclude filtered items. Over-fetch is simpler for v1.

- **source_shape may be empty** — Some validation results may have no `sh:sourceShape` value (e.g., core SHACL constraint violations). Suppressions/dismissals with empty `source_shape` should be rejected at the API level. The `LintResultItem.source_shape` field is `Optional[str]` and defaults to `None`.

- **Preset apply is a replace, not merge** — Applying a preset should replace all current suppressions with the preset's list, not merge. This matches the "switch to a different view" mental model. The UI should make this clear.

- **SSE refresh after dismiss/suppress** — After a dismiss or suppress action, the lint panel/dashboard should re-fetch. Use the existing `htmx.ajax()` pattern from the SSE handler in `lint_panel.html` for refresh.
