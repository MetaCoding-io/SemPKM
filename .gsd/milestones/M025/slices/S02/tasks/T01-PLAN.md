---
estimated_steps: 8
estimated_files: 1
---

# T01: Write seed-demo-data.py with model install, cross-model edges, and markdown bodies

**Slice:** S02 — Sample data generation script
**Milestone:** M025

## Description

Write the seed script that transforms a bare demo stack into a richly populated demo instance. The script runs inside the Docker container via `docker compose exec api python /app/scripts/seed-demo-data.py` and uses app modules directly — bypassing HTTP auth entirely. It has 4 phases: install models, create cross-model edges, set markdown bodies, and verify the result.

The script must be idempotent: safe to run multiple times without creating duplicates or erroring on already-installed models. Each phase reports progress to stdout.

**Critical constraints from research:**
- The script runs **inside the container** where `DEMO_MODE=true` returns a guest user. It must NOT use the HTTP API (which blocks POST at nginx). Instead, it imports `TriplestoreClient`, `EventStore`, `PrefixRegistry`, `ModelService` directly.
- `basic-pkm` auto-installs during app startup via `ensure_starter_model()`. The script only needs to install `crm`, `zettelkasten`, and `research`.
- Model installation automatically materializes all seed data (61 objects total across 4 models). The script does NOT create these objects — they come free with model install.
- Edge creation requires **full IRIs**, not compact IRIs. Namespaces: `urn:sempkm:model:basic-pkm:`, `urn:sempkm:model:crm:`, `urn:sempkm:model:zettelkasten:`, `urn:sempkm:model:research:`.
- The `_resolve_predicate()` function in `commands/handlers/object_create.py` handles `urn:` and `dcterms:` prefix resolution via `COMMON_PREFIXES`. Edge create handler uses this.
- `EventStore.commit()` accepts `list[Operation]`, `performed_by`, `performed_by_role`. The `Operation` dataclass needs `operation_type`, `affected_iris`, `description`, `data_triples`, `materialize_inserts`, `materialize_deletes`.

## Steps

1. **Create `scripts/seed-demo-data.py`** with the standard Python script structure:
   - `#!/usr/bin/env python3` shebang
   - Module docstring explaining purpose and usage
   - `import asyncio` and app module imports at the top
   - `async def main()` as the entry point
   - `asyncio.run(main())` at the bottom

2. **Implement service initialization** in `main()`:
   ```python
   from app.config import settings
   from app.triplestore.client import TriplestoreClient
   from app.events.store import EventStore, Operation
   from app.services.models import ModelService
   from app.services.prefixes import PrefixRegistry
   from app.models.registry import is_model_installed
   from app.triplestore.setup import ensure_repository
   import httpx
   ```
   - Create `TriplestoreClient(settings.triplestore_url, settings.repository_id)`
   - Ensure repository exists (same pattern as `main.py` lifespan)
   - Create `PrefixRegistry()`, `EventStore(client)`, `ModelService(client, event_store, prefix_registry)`

3. **Phase 1: Install models** — For each of `["crm", "zettelkasten", "research"]`:
   - Check `await is_model_installed(client, model_id)` first
   - If not installed, call `await model_service.install(Path(f"/app/models/{model_id}"))` 
   - Print status per model (installed vs skipped)
   - basic-pkm should already be installed by app startup, but verify and warn if not

4. **Phase 2: Create cross-model edges** — Define ~12 edges as a list of dicts:
   ```python
   CROSS_MODEL_EDGES = [
       {"source": "urn:sempkm:model:basic-pkm:seed-person-alice", 
        "target": "urn:sempkm:model:crm:seed-contact-sarah",
        "predicate": "urn:sempkm:model:basic-pkm:knows"},
       # ... (all 12 from research)
   ]
   ```
   - For idempotency, before creating each edge, run a SPARQL ASK query checking if an edge with the same source+target+predicate already exists:
     ```sparql
     ASK { GRAPH <urn:sempkm:current> {
       ?edge a <urn:sempkm:Edge> ;
             <urn:sempkm:source> <{source}> ;
             <urn:sempkm:target> <{target}> ;
             <urn:sempkm:predicate> <{predicate}> .
     }}
     ```
   - If not exists, create the edge using `handle_edge_create(EdgeCreateParams(...), settings.base_namespace)` to get an `Operation`, then commit via `event_store.commit([operation])`.
   - Alternatively, build the `Operation` directly using the same triple pattern from `edge_create.py` (import the handler function).

5. **Phase 3: Set markdown bodies** — Define ~8-10 body entries:
   ```python
   MARKDOWN_BODIES = {
       "urn:sempkm:model:basic-pkm:seed-note-architecture": "# Architecture Notes\n\nSemPKM uses...",
       "urn:sempkm:model:basic-pkm:seed-note-graph-viz": "# Graph Visualization Ideas\n\n...",
       # ...
   }
   ```
   - For each, use `handle_body_set(BodySetParams(iri=iri, body=body), settings.base_namespace)` to get an Operation
   - Commit via `event_store.commit([operation])`
   - Idempotency: body.set is inherently idempotent (replaces existing body), so no check needed
   - Content should be rich enough to look good in the demo — 3-5 paragraphs with markdown formatting, lists, links, bold/italic

6. **Phase 4: Verify** — Run SPARQL count queries to validate:
   - Total object count: `SELECT (COUNT(DISTINCT ?s) AS ?c) WHERE { GRAPH <urn:sempkm:current> { ?s a ?t } }` — expect ≥50
   - Cross-model edge count: query edges where source and target have different model namespace prefixes — expect ≥10
   - Print summary table

7. **Add `--verify-only` CLI flag** using `argparse`:
   - When passed, skip phases 1-3 and only run phase 4 (verification)
   - Useful for checking state of an existing demo instance

8. **Handle errors gracefully** — each phase wraps operations in try/except, prints errors per-item but continues with the rest. The script should not abort on a single failure.

## Must-Haves

- [ ] Script installs crm, zettelkasten, research models (basic-pkm already auto-installed)
- [ ] ~12 cross-model edges defined matching the research plan (connecting objects across 4 models)
- [ ] ~8-10 markdown bodies set on key objects with demo-quality content
- [ ] Idempotent: model install checks `is_model_installed()`, edge creation checks SPARQL ASK
- [ ] Phase 4 verification prints object count, model count, edge count
- [ ] `--verify-only` flag skips install/edge/body phases
- [ ] Valid Python that imports correctly when run inside the API container

## Verification

- `python3 -c "import ast; ast.parse(open('scripts/seed-demo-data.py').read())"` — valid Python syntax
- Script contains all 4 phases (install, edges, bodies, verify) with progress output
- Cross-model edges list has ≥10 entries connecting objects from different model namespaces
- Markdown bodies have ≥8 entries with multi-paragraph content

## Inputs

- `models/*/manifest.yaml` — Model IDs and namespaces for constructing full IRIs
- `models/*/seed/*.jsonld` — Seed object IDs for cross-referencing (all `@id` values)
- `backend/app/services/models.py` — `ModelService.install()`, `is_model_installed()` API
- `backend/app/commands/handlers/edge_create.py` — `handle_edge_create()` for edge Operations
- `backend/app/commands/handlers/body_set.py` — `handle_body_set()` for body Operations
- `backend/app/events/store.py` — `EventStore.commit()` for materializing changes
- `backend/app/config.py` — `settings.triplestore_url`, `settings.repository_id`, `settings.base_namespace`
- S01 summary: demo stack runs on ports 3902/8902, nginx blocks all POST, script must use direct imports not HTTP API

## Observability Impact

- **New signals:** Script prints phased progress (`[1/4] Installing models...`, `[2/4] Creating edges...`, etc.) with per-item pass/skip/fail counts and a final summary table showing object count, model count, and edge count.
- **Inspection surface:** `--verify-only` flag re-runs just the verification phase against an existing stack without modifying data — useful for diagnosing state.
- **Failure visibility:** Each phase catches per-item exceptions and prints them inline (with item IRI) but continues processing remaining items. Phase 4 verification always runs, reporting actual vs expected counts so mismatches are immediately visible.
- **How a future agent inspects:** Run `docker compose -f docker-compose.demo.yml exec api python /app/scripts/seed-demo-data.py --verify-only` — the output is the diagnostic surface.

## Expected Output

- `scripts/seed-demo-data.py` — Complete seed script with 4 phases, ~12 edge definitions, ~8-10 body definitions, idempotency checks, CLI args, and graceful error handling
