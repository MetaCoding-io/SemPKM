# S05 — Model Schema Refresh — Research

**Date:** 2026-03-14  

## Summary

The `refresh_artifacts` endpoint replaces a model's shapes, views, ontology, and rules graphs in the triplestore with freshly-loaded content from disk, without touching user data (`urn:sempkm:current`), seed data, or the model registry entry. This is a clean, low-risk operation because:

1. **Nothing else writes to artifact graphs** — only `ModelService.install()` writes to `urn:sempkm:model:{id}:shapes`, `…:views`, `…:ontology`, and `…:rules`. No user actions, inference, or federation touch them. They are purely model-authored read-only data.
2. **The `ensure_starter_model` auto-upgrade path already does 90% of this** — it calls `clear_model_graphs()` + `unregister_model()` + `install()`. Refresh is simpler: CLEAR the artifact graphs, re-load from disk, skip seed re-materialization, skip re-registration (model is already registered).
3. **Cache invalidation patterns exist** — `ViewSpecService.invalidate_cache()` is called after every install/remove. `ShapesService` fetches fresh from the triplestore on every call (no cache). `IconService` reads from disk on cache miss.

The primary recommendation is to add a `refresh_artifacts()` method to `ModelService` that: clears the 4 artifact graphs (ontology, shapes, views, rules), re-loads them from disk via `load_archive()`, writes them back via the existing `_build_insert_data_sparql()` helper, and invalidates the ViewSpec cache. An admin router endpoint and a "Refresh" button on the model detail page complete the feature.

## Recommendation

**Approach: Clear-and-reload in a transaction.** Use RDF4J transactions (already proven in `install()`) to atomically CLEAR + INSERT DATA for each artifact graph. This avoids any window where the graphs are empty. If the re-load fails (bad JSON-LD on disk), the transaction rolls back and the old graphs remain intact.

**No seed re-materialization.** Seed data lives in `urn:sempkm:current` via EventStore. Refreshing artifacts must NOT re-run seed — that would duplicate objects. The only exception is if a model adds new seed data, but that's a separate "upgrade" concern for a future milestone.

**Version metadata stays unchanged.** The registry entry (`urn:sempkm:models`) is not updated. Refreshing doesn't change the model version — it just reloads the current disk content. The `ensure_starter_model` upgrade path (which does bump versions) is a separate mechanism.

## Don't Hand-Roll

| Problem | Existing Solution | Why Use It |
|---------|------------------|------------|
| Clearing model graphs | `clear_model_graphs()` in `registry.py` | Already handles all 5 named graphs with `CLEAR SILENT GRAPH` |
| Loading RDF from disk | `load_archive()` in `loader.py` | Handles JSON-LD + Turtle, remote context checks, all entrypoints |
| Building INSERT DATA | `_build_insert_data_sparql()` in `models.py` | Proper triple-by-triple serialization, handles BNodes/Literals/URIRefs |
| Transaction management | `begin_transaction` / `commit_transaction` / `rollback_transaction` on `TriplestoreClient` | Proven in `install()` — atomic multi-graph writes |
| Cache invalidation | `ViewSpecService.invalidate_cache()` | Existing pattern used after install/remove |
| PROV-O ops logging | `OperationsLogService.log_activity()` | Fire-and-forget pattern established in S02 (D079, D082) |

## Existing Code and Patterns

- `backend/app/services/models.py` — `ModelService.install()` is the reference for the full graph-write pipeline. The refresh method follows the same structure but skips steps 2 (duplicate check), 4 (validation), 8 (seed materialization), and 10 (prefix registration).
- `backend/app/services/models.py` — `ensure_starter_model()` already does clear + reinstall for version upgrades. Refresh is a lighter version of this — no unregister, no seed.
- `backend/app/models/registry.py` — `ModelGraphs` dataclass provides `ontology`, `shapes`, `views`, `rules` properties. The `all_graphs` property includes `seed` — refresh must use a custom list excluding seed.
- `backend/app/models/registry.py` — `clear_model_graphs()` clears all 5 graphs. Refresh needs to clear only 4 (excluding seed). Either add a parameter or build custom CLEAR queries.
- `backend/app/models/loader.py` — `load_archive()` returns `ModelArchive` with all graphs. Refresh calls this but ignores the `seed` field.
- `backend/app/admin/router.py` — `admin_models_install()` and `admin_models_remove()` show the pattern for ops log integration, cache invalidation, and htmx response.
- `backend/app/templates/admin/models.html` — Model list table with action buttons (Inference, Remove). Refresh button goes here next to existing buttons.
- `backend/app/templates/admin/model_detail.html` — Model detail page header. Could also house a Refresh button for better discoverability.

## Constraints

- **Models directory is mounted read-only** (`./models:/app/models:ro` in docker-compose.yml). The endpoint reads from disk — it cannot modify model files. This is correct behavior for refresh.
- **Model must already be installed.** The endpoint requires the model to exist in the registry. It uses the model_id to find the disk path (`/app/models/{model_id}/`).
- **Artifact graphs must not contain user data.** Only ontology, shapes, views, and rules are refreshed. Seed graph is user data (materialized via EventStore). The `urn:sempkm:models` registry graph is metadata.
- **Triple count per graph is manageable.** Largest artifact graph (basic-pkm shapes) has ~435 triples — well within a single INSERT DATA. No batching needed.
- **IconService reads from manifest.yaml on disk, not from the triplestore.** Icon changes from disk are automatically picked up on cache miss. No explicit cache invalidation needed for icons.

## Common Pitfalls

- **Don't re-materialize seed data** — Seed objects already exist in `urn:sempkm:current`. Re-running seed would create duplicates (new EventStore operations with new IRIs or collisions). The `load_archive()` return includes `.seed` — the refresh method must explicitly ignore it.
- **Don't clear the seed graph** — `clear_model_graphs()` clears ALL 5 graphs including seed. Refresh must use a custom list of graphs to clear: `[ontology, shapes, views, rules]`. Either modify `clear_model_graphs()` to accept an `exclude` parameter or build the CLEAR queries inline.
- **Don't forget ViewSpec cache invalidation** — After refreshing views, the `ViewSpecService` TTLCache has stale data. Must call `invalidate_cache()` on `request.app.state.view_spec_service`. The admin router has access to this via the `Request` object.
- **Don't update the registry version** — The refresh endpoint reloads from disk. If the disk manifest has a different version, should we update the registry? **No** — the version in the registry records what was installed. Version upgrades go through `ensure_starter_model` or remove+install. Refresh is about picking up content changes within the same version.
- **Model path assumption** — The endpoint assumes models live at `/app/models/{model_id}/`. This is true in Docker (volume mount) but could differ in other environments. Use a constant or config value, not a hardcoded string. Other code uses `/app/models` (see `main.py`, `inference/service.py`, `admin/router.py`).
- **Transaction rollback on partial failure** — If CLEAR succeeds but INSERT fails, the graphs are empty. Using transactions prevents this — the entire operation either completes or rolls back.

## Open Risks

- **Model not on disk** — If the model archive directory doesn't exist on disk (e.g., was removed but still registered in the triplestore), `load_archive()` will throw `FileNotFoundError`. The endpoint should catch this and return a clear error.
- **JSON-LD parse errors on disk** — If the model files are malformed, `load_archive()` will throw. With transaction rollback, the old graphs remain intact. The error should be surfaced to the user.
- **Inferred triples may become stale** — If ontology changes affect inference (e.g., new `rdfs:subClassOf` declarations), the inferred graph (`urn:sempkm:inferred`) may be stale after refresh. The current code doesn't auto-re-run inference. This is acceptable — the user can click "Run Inference" manually. But worth noting in the UI ("You may want to re-run inference after refreshing artifacts").
- **Concurrent requests** — Two simultaneous refresh requests could race. Low risk since this is an admin-only action. No mitigation needed for MVP.

## Implementation Shape

### Service Layer — `ModelService.refresh_artifacts()`

```python
@dataclass
class RefreshResult:
    success: bool
    model_id: str
    graphs_refreshed: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

async def refresh_artifacts(self, model_id: str) -> RefreshResult:
    # 1. Verify model is installed (registry check)
    # 2. Find model dir on disk (/app/models/{model_id})
    # 3. Parse manifest + load archive
    # 4. Begin transaction
    # 5. CLEAR ontology, shapes, views, rules graphs (NOT seed)
    # 6. INSERT DATA for each non-empty artifact graph
    # 7. Commit transaction
    # 8. Return success with list of refreshed graphs
```

### Router Layer — `POST /admin/models/{model_id}/refresh-artifacts`

- Requires `owner` role
- Calls `model_service.refresh_artifacts(model_id)`
- Invalidates ViewSpec cache on success
- Logs to ops log (fire-and-forget, D082)
- Returns updated model detail or model table partial for htmx swap

### Template Layer — "Refresh" button

Two placement options:
1. **Model list table** — Add a "Refresh" button in the Actions column next to "Inference" and "Remove"
2. **Model detail header** — Add a "Refresh" button in the header next to the version pill

**Recommendation: Both.** The list table button is convenient for quick refreshes; the detail page button is discoverable when you're already reviewing the model. Both use `hx-post` with htmx.

### Unit Tests

- Test `refresh_artifacts()` with mock triplestore: verify CLEAR for 4 graphs (not seed), INSERT DATA for each graph
- Test error case: model not installed → returns error
- Test error case: model dir not on disk → returns error
- Test that transaction is rolled back on INSERT failure

## Skills Discovered

| Technology | Skill | Status |
|------------|-------|--------|
| FastAPI | — | No specific skill needed (well-understood in codebase) |
| RDF4J | — | No specific skill needed (TriplestoreClient abstracts it) |
| htmx | — | No specific skill needed (existing patterns cover it) |

No external skills are needed — this slice reuses exclusively existing patterns and infrastructure.

## Sources

- `backend/app/services/models.py` — `ModelService.install()` pipeline (lines 160-260), `ensure_starter_model()` (lines 1000-1042)
- `backend/app/models/registry.py` — `ModelGraphs`, `clear_model_graphs()`, graph IRI conventions
- `backend/app/models/loader.py` — `load_archive()`, `ModelArchive` dataclass
- `backend/app/admin/router.py` — install/remove endpoints, ops log integration pattern
- `backend/app/templates/admin/models.html` — model list template with action buttons
- `backend/app/templates/admin/model_detail.html` — model detail page header
- `docker-compose.yml` — `./models:/app/models:ro` volume mount
