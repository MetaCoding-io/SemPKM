# S02: Sample Data Generation Script — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

The 4 Mental Models (basic-pkm, crm, zettelkasten, research) already ship **61 seed objects** in their JSON-LD seed files — well above the 30-50 target. The seed script's job is therefore: (1) install the 3 non-default models (crm, zettelkasten, research — basic-pkm auto-installs at startup), (2) create ~15 cross-model edges linking objects across model boundaries (CRM Contact who is a basic-pkm Person, Research Paper cited in a Zettelkasten LiteratureNote, etc.), (3) set markdown bodies on ~8-10 key objects for visual richness in the demo, and (4) verify the setup via SPARQL counts and validation-trigger checks.

The critical constraint is auth: the demo nginx blocks all POST requests, and `DEMO_MODE=true` returns a `guest` user that fails `require_role("owner")` checks on model install and `require_role_or_api("owner", "member")` on the Command API. The seed script must therefore run **before** DEMO_MODE is activated — either against the API port 8902 with a real authenticated user, or as an internal Python script executed inside the container using `docker compose exec`.

## Recommendation

**Write a standalone Python script (`scripts/seed-demo-data.py`)** that uses `httpx` to call the API at `http://localhost:8902` (direct API port, bypassing nginx). The script runs as part of a two-phase deployment: (1) start the demo stack without DEMO_MODE, run the seed script, (2) restart the API with DEMO_MODE enabled. The seed script handles its own auth by reading the setup token from the container and completing first-run setup to create an owner user, then uses session cookies for all API calls. This keeps the script self-contained and testable without modifying the application code.

**Why not run inside the container?** Running via `docker compose exec api python scripts/seed-demo-data.py` with direct service imports would require the script to duplicate the entire lifespan setup (TriplestoreClient, EventStore, ModelService, prefix registry, etc.) and fight async context issues. The HTTP approach reuses the running app's services and is simpler.

**Why not just install models and rely on seed data?** The existing seed data has **zero cross-model edges** — each model's seed objects only reference other objects within the same model. Without cross-model edges, the graph view shows 4 disconnected clusters instead of one interconnected knowledge graph. The edges are what make the demo visually compelling.

## Implementation Landscape

### Key Files

- `scripts/seed-demo-data.py` — **New.** The seed script. Uses `httpx` to call model install and command APIs. Structured as: (1) setup auth, (2) install models, (3) create cross-model edges, (4) set markdown bodies, (5) verify counts.
- `docker-compose.demo.yml` — **Exists (S01).** Demo stack config. The seed script targets port 8902 (API direct) since port 3902 (nginx) blocks POST. The deployment flow will need a wrapper script that starts without DEMO_MODE, seeds, restarts with DEMO_MODE.
- `backend/app/models/router.py` — **Read-only.** `POST /api/models/install` accepts `{"path": "/app/models/<model_id>"}` and requires `require_role("owner")`.
- `backend/app/commands/router.py` — **Read-only.** `POST /api/commands` accepts single or batch command JSON, requires `require_role_or_api("owner", "member")`. Supports `object.create`, `object.patch`, `body.set`, `edge.create`.
- `backend/app/commands/schemas.py` — **Read-only.** Command schema reference: `ObjectCreateParams(type, slug, properties)`, `BodySetParams(iri, body)`, `EdgeCreateParams(source, target, predicate)`.
- `models/*/seed/*.jsonld` — **Read-only.** Existing seed data (21 + 12 + 12 + 16 = 61 objects). Seed IRIs follow the pattern `{namespace_prefix}:seed-{type}-{slug}`.
- `models/*/manifest.yaml` — **Read-only.** Model IDs: `basic-pkm`, `crm`, `zettelkasten`, `research`. Paths inside container: `/app/models/{model_id}`.
- `models/*/rules/*.ttl` — **Read-only.** SHACL-AF validation rules. Overdue task: `bpkm:taskStatus IN ("todo","in-progress","blocked") AND dueDate < today`. Stale contact: `NOT EXISTS { ?interaction crm:withContact $this }`. Unprocessed fleeting note: `NOT EXISTS { $this zk:processedInto ?x }`.

### Existing Seed Data Summary

| Model | Objects | Types | Validation Triggers |
|-------|---------|-------|-------------------|
| basic-pkm | 21 | Project(2), Person(3), Note(3), Concept(3), Task(4), Milestone(2), Event(4) | `seed-task-fix-validation`: dueDate=2026-03-10, status=todo → overdue |
| crm | 12 | Company(3), Contact(4), Interaction(3), Deal(2) | `seed-contact-marcus`: no interaction → stale contact |
| zettelkasten | 12 | Source(3), FleetingNote(2), LiteratureNote(3), PermanentNote(3), StructureNote(1) | `seed-fleeting-unprocessed`: no processedInto → unprocessed |
| research | 16 | Paper(3), Claim(5), Evidence(5), ResearchQuestion(2), Argument(1) | Various unsupported/contested claims |
| **Total** | **61** | **26 distinct types** | **All 3 required validation warnings covered** |

### Cross-Model Edge Plan

These edges connect objects across model boundaries to create a unified knowledge graph:

| Source (Model) | Target (Model) | Predicate | Narrative |
|---|---|---|---|
| bpkm:seed-person-alice | crm:seed-contact-sarah | `bpkm:knows` | Alice knows Sarah (colleague from Acme) |
| bpkm:seed-person-bob | crm:seed-contact-priya | `bpkm:knows` | Bob knows Priya (design collaboration) |
| bpkm:seed-note-architecture | res:seed-paper-kg-survey | `dcterms:references` | Architecture note references KG survey paper |
| bpkm:seed-concept-knowledge-management | res:seed-rq-pkm-effectiveness | `dcterms:relation` | KM concept relates to PKM research question |
| bpkm:seed-concept-semantic-web | res:seed-paper-rdf-scaling | `dcterms:references` | Semantic Web concept references RDF scaling paper |
| bpkm:seed-project-sempkm | crm:seed-deal-platform | `dcterms:relation` | SemPKM project relates to platform deal |
| zk:seed-litnote-ahrens-slip | res:seed-claim-pkm-adoption | `dcterms:references` | Lit note about slip-box references PKM adoption claim |
| zk:seed-perm-cognitive-load | bpkm:seed-concept-knowledge-management | `dcterms:relation` | Cognitive load note relates to KM concept |
| zk:seed-source-networked | res:seed-paper-pkm-tools | `dcterms:references` | Networked Thought article references PKM tools paper |
| crm:seed-company-acme | bpkm:seed-project-sempkm | `dcterms:relation` | Acme Corp relates to SemPKM project (partnership) |
| res:seed-evidence-survey | zk:seed-perm-confirmation-bias | `dcterms:references` | Survey evidence references confirmation bias note |
| bpkm:seed-note-graph-viz | zk:seed-structure-case | `dcterms:references` | Graph viz idea references Zettelkasten structure note |

~12 cross-model edges creating a dense, interconnected graph.

### Auth Strategy for Seeding

The seed script must authenticate as an `owner` user. In a fresh demo stack:

1. Read the setup token: `docker compose -f docker-compose.demo.yml exec -T api cat /app/data/.setup-token`
2. POST to `/api/auth/setup` with the token to create the first owner user
3. POST to `/api/auth/magic-link/request` + `/api/auth/magic-link/verify` to get a session cookie
4. Use the session cookie for all subsequent API calls

Alternatively, since this is a fresh instance: the setup endpoint creates the first user directly. The script can use that session.

Actually — simplest path: the script runs against port 8902 **without DEMO_MODE**. The deployment flow:

```bash
# 1. Start stack without DEMO_MODE
DEMO_MODE=false docker compose -f docker-compose.demo.yml up -d
# 2. Wait for health
# 3. Run seed script (creates owner user via setup, installs models, seeds data)
python scripts/seed-demo-data.py --api-url http://localhost:8902
# 4. Restart API with DEMO_MODE
docker compose -f docker-compose.demo.yml stop api
DEMO_MODE=true docker compose -f docker-compose.demo.yml up -d api
```

But this is fragile — the `docker-compose.demo.yml` hardcodes `DEMO_MODE: "true"`. Better: the seed script runs first against the API port before demo nginx is started, or the compose file is parameterized.

**Cleanest approach:** Override DEMO_MODE via the deployment wrapper script:

```bash
# Start stack
docker compose -f docker-compose.demo.yml up -d
# Temporarily disable DEMO_MODE for seeding
docker compose -f docker-compose.demo.yml exec api sh -c 'DEMO_MODE=false python /app/scripts/seed-demo-data.py'
```

Wait — that won't work because the running API process already has DEMO_MODE=true. The script would need to call the running API which has DEMO_MODE active (guest role).

**Actual cleanest approach:** The seed script runs **inside the container** using the app's Python modules directly, bypassing HTTP auth entirely. It creates a `TriplestoreClient`, `EventStore`, `ModelService` directly. This is how `ensure_starter_model` works at startup — no auth needed.

### Build Order

1. **T01: Core seed script with model install and idempotency** — Write `scripts/seed-demo-data.py` as an async Python script that imports app modules directly. Install 3 models (crm, zettelkasten, research — basic-pkm auto-installs). Check `is_model_installed()` for idempotency. Run via `docker compose exec api python scripts/seed-demo-data.py`.

2. **T02: Cross-model edges and markdown bodies** — Extend the script to create ~12 cross-model edges via `EventStore.commit()` and set markdown bodies on ~8-10 key objects. Use the `handle_edge_create` and `handle_body_set` handlers directly (or construct Operations manually).

3. **T03: Verification and deployment wrapper** — Add verification phase to script (SPARQL count queries, validation trigger checks). Create a `scripts/deploy-demo.sh` wrapper that orchestrates: start stack → wait health → exec seed → verify. Add unit tests for the seed data definitions.

### Verification Approach

After running the seed script against a fresh demo stack:

1. **Object count:** SPARQL query `SELECT (COUNT(DISTINCT ?s) AS ?c) WHERE { GRAPH <urn:sempkm:current> { ?s a ?t } }` returns ≥ 50
2. **Model install:** `GET /api/models` returns 4 models (basic-pkm, crm, zettelkasten, research)
3. **Cross-model edges visible:** SPARQL for edges where source and target have different model prefixes returns ≥ 10
4. **Validation warnings fire:** `GET /browser/lint` shows warnings for overdue task, stale contact, unprocessed note
5. **Explorer shows objects:** Navigate to `/browser/` and see objects from all 4 models in the By Type tree
6. **Graph view shows connections:** Open Graph View and see interconnected nodes across model boundaries

Verification commands:
```bash
# Check installed models
curl http://localhost:8902/api/models | python3 -m json.tool

# Count objects (via SPARQL — needs auth, use browser or docker exec)
docker compose -f docker-compose.demo.yml exec api python -c "
import asyncio
from app.triplestore.client import TriplestoreClient
from app.config import settings
async def check():
    c = TriplestoreClient(settings.triplestore_url, settings.repository_id)
    r = await c.query('SELECT (COUNT(DISTINCT ?s) AS ?c) WHERE { GRAPH <urn:sempkm:current> { ?s a ?t } }')
    print(r)
asyncio.run(check())
"
```

## Constraints

- **Seed script must bypass HTTP auth** — Running via `docker compose exec api python` with direct module imports is the only clean path. The HTTP API requires `owner` role for model install and `owner|member` for commands; the demo guest user has `guest`.
- **Models directory is at `/app/models/` inside the container** — The script passes `Path("/app/models/{model_id}")` to `ModelService.install()`.
- **basic-pkm auto-installs on startup** — The lifespan calls `ensure_starter_model()` which installs basic-pkm if no models exist. The seed script should handle this (skip if already installed).
- **DashboardSpec requires user_id FK** — Creating a demo dashboard needs a real user in SQLite, but DEMO_MODE uses a transient user not in the DB. Dashboard creation is deferred to S03 (which needs the dashboard spec defined).
- **Script must be mounted into the container** — `docker-compose.demo.yml` doesn't currently mount `./scripts/`. Need to add a volume mount or use `docker compose cp`.

## Common Pitfalls

- **Double-installing models** — `ModelService.install()` returns an error if the model is already installed. The script must check `is_model_installed()` first. The existing `ensure_starter_model` pattern is the reference.
- **Seed data already loaded by model install** — When a model is installed, its seed data (`seed/*.jsonld`) is automatically materialized via EventStore. The script does NOT need to create the 61 seed objects — they come free with model installation. The script only needs to create the **cross-model edges** and **markdown bodies**.
- **Edge creation requires full IRIs** — `edge.create` expects full IRIs for source/target/predicate (e.g., `urn:sempkm:model:basic-pkm:seed-person-alice`), not compact IRIs (e.g., `bpkm:seed-person-alice`). The script must expand prefixes.
- **Async context required** — `ModelService.install()` and `EventStore.commit()` are async. The script needs `asyncio.run()` or an async main.
- **RDF4J cold start** — First request after container start takes 5-10s. The script should wait for the health check before proceeding.

## Open Risks

- **Volume mount for scripts/** — The `docker-compose.demo.yml` doesn't mount `./scripts/` into the container. Either add it to the compose file or use `docker compose exec -T api python -c "$(cat scripts/seed-demo-data.py)"` to pipe the script in. Adding a volume mount is cleaner.
- **Idempotency edge cases** — If the script is run twice, model install is idempotent (check first), but edge/body creation would create duplicates. Need a check: query for existing cross-model edges before creating.

## Sources

- `backend/app/services/models.py` — `ModelService.install()` and `ensure_starter_model()` patterns
- `backend/app/commands/handlers/edge_create.py` — Edge creation: `handle_edge_create(EdgeCreateParams, base_namespace)`
- `backend/app/commands/handlers/body_set.py` — Body setting: `handle_body_set(BodySetParams, base_namespace)`
- `backend/app/events/store.py` — `EventStore.commit(operations, performed_by, performed_by_role)`
- `models/*/seed/*.jsonld` — Existing seed IRIs for cross-referencing
- `models/*/rules/*.ttl` — SHACL-AF validation rules defining trigger conditions
