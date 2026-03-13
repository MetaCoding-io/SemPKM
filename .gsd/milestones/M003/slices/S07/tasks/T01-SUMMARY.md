---
id: T01
parent: S07
milestone: M003
provides:
  - gist 14.0.0 bundled and loaded into triplestore at startup
  - OntologyService with batched INSERT DATA and ASK version check
  - rdfs:subClassOf alignment triples in basic-pkm and ppv ontologies
  - gist namespace registered in prefix system (COMMON_PREFIXES + PrefixRegistry)
key_files:
  - backend/ontologies/gist/gistCore14.0.0.ttl
  - backend/app/ontology/service.py
  - backend/app/main.py
  - models/basic-pkm/ontology/basic-pkm.jsonld
  - models/ppv/ontology/ppv.jsonld
key_decisions:
  - Copied _rdf_term_to_sparql and _build_insert_data_sparql into ontology/service.py (local copy, not import from services/models.py) to avoid circular dependency — function is small and stable
  - gist ontology file path in Docker is /app/ontologies via new volume mount in docker-compose.yml
patterns_established:
  - OntologyService pattern: ASK version check → rdflib parse → batch split → transactional INSERT DATA
  - Ontology files live at backend/ontologies/<name>/ with LICENSE attribution
observability_surfaces:
  - logger.info "Loaded gist 14.0.0: N triples in X.Xs" on fresh load
  - logger.info "gist already loaded, skipping" on subsequent startup
  - logger.error "Failed to load gist" with traceback on failure
  - SPARQL inspection: ASK { GRAPH <urn:sempkm:ontology:gist> { ?s ?p ?o } }
  - SPARQL count: SELECT (COUNT(*) as ?c) WHERE { GRAPH <urn:sempkm:ontology:gist> { ?s ?p ?o } }
duration: 25m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Bundle gist 14.0.0 and build ontology service with startup loader

**Bundled gist 14.0.0 (2345 triples) with OntologyService, batched INSERT DATA loader, ASK version check, alignment triples in basic-pkm/ppv, and gist prefix registration.**

## What Happened

1. Downloaded `gistCore.ttl` from gist v14.0.0 release (semanticarts/gist GitHub, `ontologies/gistCore.ttl`). Placed at `backend/ontologies/gist/gistCore14.0.0.ttl` (3438 lines, 2345 triples, 187 classes, 452 BNodes). Added CC BY 4.0 LICENSE file.

2. Created `backend/app/ontology/service.py` with `OntologyService`:
   - `is_gist_loaded()` — ASK query checking for gistCore as owl:Ontology in the gist graph
   - `ensure_gist_loaded(gist_path)` — idempotent loader: version check → rdflib parse → batch split (≤500) → transactional INSERT DATA
   - Local copies of `_rdf_term_to_sparql()` and `_build_insert_data_sparql()` (adapted for batch triples list instead of rdflib Graph)
   - Constants: `GIST_GRAPH`, `USER_TYPES_GRAPH`, `GIST_ONTOLOGY_IRI`, `GIST_NS`, `BATCH_SIZE`

3. Added gist alignment triples to basic-pkm.jsonld: Project→gist:Task, Person→gist:Person, Note→gist:FormattedContent, Concept→gist:KnowledgeConcept. Added gist namespace to @context.

4. Added gist alignment triple to ppv.jsonld: Project→gist:Task. Added gist namespace to @context.

5. Wired `ensure_gist_loaded()` into `main.py` lifespan after `ensure_starter_model()`. Stored `ontology_service` on `app.state`. Added try/except to prevent gist load failure from blocking startup (logs error, TBox queries will be incomplete but app still starts).

6. Added `./backend/ontologies:/app/ontologies:ro` volume mount to docker-compose.yml for the api service.

7. Added gist namespace to `COMMON_PREFIXES` in `rdf/namespaces.py`, `GIST` Namespace object, and `PrefixRegistry.BUILTIN`.

8. Wrote 16 unit tests covering batch splitting (5 tests), INSERT DATA generation (5 tests), term serialization (5 tests), and ASK query format (1 test).

## Verification

- `cd backend && python -m pytest tests/test_ontology_service.py -v` — **16/16 passed**
- `cd backend && python -m pytest tests/ -v` — **256/256 passed** (no regressions)
- `docker compose up -d --build api` → logs show `Loaded gist 14.0.0: 2345 triples in 1.2s` ✓
- `docker compose restart api` → logs show `gist already loaded, skipping` ✓
- Direct SPARQL count query: `SELECT (COUNT(*) as ?c) WHERE { GRAPH <urn:sempkm:ontology:gist> { ?s ?p ?o } }` → **2345** ✓
- JSON-LD validation: basic-pkm has all 4 alignment triples, ppv has Project→gist:Task ✓

### Slice-level verification (partial — T01 is first task):
- ✅ `cd backend && python -m pytest tests/test_ontology_service.py -v` — passes
- ⏳ E2E test `ontology-viewer.spec.ts` — not yet created (T04)
- ⏳ Manual ontology viewer — not yet built (T03)

## Diagnostics

- **Check gist loaded:** `docker compose exec api curl -s "http://triplestore:8080/rdf4j-server/repositories/sempkm" -H "Accept: application/sparql-results+json" --data-urlencode "query=ASK { GRAPH <urn:sempkm:ontology:gist> { ?s ?p ?o } }"`
- **Count triples:** same URL with `SELECT (COUNT(*) as ?c) WHERE { GRAPH <urn:sempkm:ontology:gist> { ?s ?p ?o } }` → expect 2345
- **Startup logs:** `docker compose logs api | grep -i gist`
- **Failure mode:** if gist file missing → FileNotFoundError logged, startup continues without gist data

## Deviations

- gistCore.ttl is at `ontologies/gistCore.ttl` in the GitHub repo (not root level) — adjusted download URL accordingly
- gist has 2345 triples (not estimated ~3500) and 187 classes (not ~96 as estimated in the research) — 96 was likely just the named classes; the total includes OWL restrictions and other class expressions

## Known Issues

None.

## Files Created/Modified

- `backend/ontologies/gist/gistCore14.0.0.ttl` — bundled gist 14.0.0 ontology (3438 lines)
- `backend/ontologies/gist/LICENSE` — CC BY 4.0 attribution to Semantic Arts
- `backend/app/ontology/__init__.py` — empty module init
- `backend/app/ontology/service.py` — OntologyService with ensure_gist_loaded, batch splitting, version check
- `backend/app/main.py` — modified: import OntologyService, wire ensure_gist_loaded into lifespan
- `models/basic-pkm/ontology/basic-pkm.jsonld` — modified: gist namespace + 4 rdfs:subClassOf alignments
- `models/ppv/ontology/ppv.jsonld` — modified: gist namespace + 1 rdfs:subClassOf alignment
- `backend/app/rdf/namespaces.py` — modified: added GIST namespace and prefix
- `backend/app/services/prefixes.py` — modified: added gist to PrefixRegistry.BUILTIN
- `docker-compose.yml` — modified: added ontologies volume mount
- `backend/tests/test_ontology_service.py` — 16 unit tests for batch splitting, INSERT DATA, term serialization
