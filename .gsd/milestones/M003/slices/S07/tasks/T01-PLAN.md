---
estimated_steps: 7
estimated_files: 8
---

# T01: Bundle gist 14.0.0 and build ontology service with startup loader

**Slice:** S07 — Ontology Viewer & Gist Foundation
**Milestone:** M003

## Description

Download and bundle gist 14.0.0 (`gistCore.ttl`) into the backend. Create `OntologyService` with batched INSERT DATA loading and version checking. Add `rdfs:subClassOf` alignment triples to basic-pkm and ppv model ontology files. Wire gist loading into application startup. This task establishes the foundation — without gist in the triplestore, no TBox/ABox/RBox queries can return cross-graph results.

## Steps

1. **Download and bundle gistCore.ttl** — Fetch `gistCore.ttl` from gist v14.0.0 release (or use the existing research copy). Place at `backend/ontologies/gist/gistCore14.0.0.ttl`. Add `LICENSE` file with CC BY 4.0 attribution to Semantic Arts. Ensure the file is included in the Docker image via the existing volume mount or Dockerfile COPY.

2. **Create `backend/app/ontology/__init__.py` and `backend/app/ontology/service.py`** — Build `OntologyService` class with:
   - `__init__(self, client: TriplestoreClient)` 
   - `async ensure_gist_loaded(self, gist_path: Path)` — the main startup method:
     - ASK query: `ASK { GRAPH <urn:sempkm:ontology:gist> { <https://w3id.org/semanticarts/ontology/gistCore> a <http://www.w3.org/2002/07/owl#Ontology> } }` — skip load if true
     - If not loaded: parse gist Turtle with rdflib, split triples into batches of ≤500, execute each batch as INSERT DATA within a transaction
     - Log triple count and load duration
   - Use `_build_insert_data_sparql()` pattern from `services/models.py` (copy the helper or import — prefer copy to avoid circular deps since it's a small function)
   - Use `_rdf_term_to_sparql()` for term serialization including BNode handling
   - Constants: `GIST_GRAPH = "urn:sempkm:ontology:gist"`, `GIST_ONTOLOGY_IRI = "https://w3id.org/semanticarts/ontology/gistCore"`, `USER_TYPES_GRAPH = "urn:sempkm:user-types"`, `GIST_NS = "https://w3id.org/semanticarts/ns/ontology/gist/"`

3. **Add alignment triples to basic-pkm ontology** — Edit `models/basic-pkm/ontology/basic-pkm.jsonld`:
   - Add gist namespace to `@context`: `"gist": "https://w3id.org/semanticarts/ns/ontology/gist/"`
   - Add `rdfs:subClassOf` to existing class definitions:
     - `bpkm:Project` → `rdfs:subClassOf gist:Task`
     - `bpkm:Person` → `rdfs:subClassOf gist:Person`
     - `bpkm:Note` → `rdfs:subClassOf gist:FormattedContent`
     - `bpkm:Concept` → `rdfs:subClassOf gist:KnowledgeConcept`

4. **Add alignment triples to ppv ontology** — Edit `models/ppv/ontology/ppv.jsonld`:
   - Add gist namespace to `@context`
   - Add `rdfs:subClassOf` to ppv:Project → `gist:Task` (the closest match; other PPV classes like PillarGroup, Pillar, ValueGoal are too domain-specific for gist alignment)

5. **Wire gist loading into startup** — Edit `backend/app/main.py`:
   - Import OntologyService
   - After `ensure_starter_model()`, create OntologyService and call `ensure_gist_loaded(Path("/app/ontologies/gist/gistCore14.0.0.ttl"))`
   - Store `ontology_service` on `app.state` for later use by TBox/ABox/RBox routes
   - Add the ontologies directory to Docker volume mount in `docker-compose.yml` if not already covered

6. **Add gist prefix to system prefix declarations** — Ensure the gist namespace prefix `gist: <https://w3id.org/semanticarts/ns/ontology/gist/>` is available in SPARQL console autocomplete and prefix registry.

7. **Write unit tests** — Create `backend/tests/test_ontology_service.py`:
   - Test `_split_triples_into_batches()`: 4000 triples → 8 batches of 500
   - Test `_split_triples_into_batches()`: 100 triples → 1 batch of 100
   - Test INSERT DATA generation produces valid SPARQL with GRAPH clause
   - Test version check ASK query format
   - Test BNode serialization in INSERT DATA (gist uses blank nodes for OWL restrictions)

## Must-Haves

- [ ] gistCore14.0.0.ttl bundled at `backend/ontologies/gist/gistCore14.0.0.ttl`
- [ ] CC BY 4.0 LICENSE file with Semantic Arts attribution
- [ ] OntologyService with `ensure_gist_loaded()` using batched INSERT DATA
- [ ] ASK-based version check skips reload on subsequent startups
- [ ] basic-pkm alignment: Project→gist:Task, Person→gist:Person, Note→gist:FormattedContent, Concept→gist:KnowledgeConcept
- [ ] ppv alignment: Project→gist:Task
- [ ] Startup wiring in main.py lifespan
- [ ] Unit tests for batch splitting and INSERT DATA generation

## Verification

- `cd backend && python -m pytest tests/test_ontology_service.py -v` — all tests pass
- `docker compose up -d && docker compose logs backend | grep -i gist` — shows "Loaded gist 14.0.0: N triples in X.Xs" on first start
- `docker compose restart backend && docker compose logs backend | grep -i gist` — shows "gist already loaded, skipping" on subsequent start

## Observability Impact

- Signals added/changed: `logger.info("Loaded gist 14.0.0: %d triples in %.1fs")` on fresh load; `logger.info("gist already loaded, skipping")` on version match; `logger.error("Failed to load gist")` with traceback on failure
- How a future agent inspects this: SPARQL console `ASK { GRAPH <urn:sempkm:ontology:gist> { ?s ?p ?o } }` or `SELECT (COUNT(*) as ?c) WHERE { GRAPH <urn:sempkm:ontology:gist> { ?s ?p ?o } }` to verify triple count
- Failure state exposed: startup log error with exception; gist graph absent from triplestore (ASK returns false)

## Inputs

- `gistCore.ttl` from gist v14.0.0 release (138KB, ~3438 lines, ~96 classes)
- `backend/app/services/models.py` — `_build_insert_data_sparql()` and `_rdf_term_to_sparql()` patterns for INSERT DATA generation
- `backend/app/main.py` — lifespan startup pattern (after `ensure_starter_model()`)
- `models/basic-pkm/ontology/basic-pkm.jsonld` — existing class definitions needing alignment triples
- `models/ppv/ontology/ppv.jsonld` — existing class definitions needing alignment triples
- Research: `.planning/quick/2-research-how-the-gist-ontology-can-be-us/gist-ontology-research.md` § 3.1 Class Alignment Map

## Expected Output

- `backend/ontologies/gist/gistCore14.0.0.ttl` — bundled gist ontology file
- `backend/ontologies/gist/LICENSE` — CC BY 4.0 attribution
- `backend/app/ontology/__init__.py` — empty module init
- `backend/app/ontology/service.py` — OntologyService with ensure_gist_loaded, batch splitting, version check
- `backend/app/main.py` — modified with gist loading in lifespan
- `models/basic-pkm/ontology/basic-pkm.jsonld` — modified with gist alignment triples
- `models/ppv/ontology/ppv.jsonld` — modified with gist alignment triple
- `backend/tests/test_ontology_service.py` — unit tests for batch splitting and INSERT DATA
