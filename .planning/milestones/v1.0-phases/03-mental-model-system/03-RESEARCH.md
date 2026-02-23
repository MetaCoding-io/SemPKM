# Phase 3: Mental Model System - Research

**Researched:** 2026-02-21
**Domain:** Mental Model archives (directory-based), manifest validation, OWL/SHACL ontology packaging, named graph management, seed data loading, Basic PKM starter model
**Confidence:** HIGH

## Summary

Phase 3 builds the Mental Model system -- a packaging and installation mechanism that bundles OWL ontologies, SHACL shapes, view specs, and seed data into directory-based archives that can be installed, listed, and removed. The system uses a directory convention (not ZIP) with a `manifest.yaml` at the root describing the model's metadata and entrypoints. All RDF content is serialized as JSON-LD (.jsonld files), loaded via rdflib into in-memory graphs, validated, and then written into model-specific named graphs in the RDF4J triplestore via SPARQL INSERT DATA.

The primary technical challenge is orchestrating a multi-step install pipeline: parse manifest -> validate manifest schema -> load all JSON-LD files -> validate IRI namespacing -> validate cross-file reference integrity -> write to named graphs atomically. The removal flow must check for user data referencing model types before allowing deletion, then CLEAR the model's named graphs. The existing codebase already has all the infrastructure needed -- rdflib for RDF parsing, pyshacl for SHACL validation, TriplestoreClient for SPARQL operations, PrefixRegistry with a `register_model_prefixes()` method waiting for Phase 3, and a ValidationService with an `empty_shapes_loader` placeholder explicitly designed to be replaced by a real shapes loader from installed Mental Models.

A starter Mental Model (Basic PKM) ships with the system at a known path in the repository (`models/basic-pkm/`), auto-installing on first startup when no models are detected. It provides four types -- Projects, People, Notes, and Concepts -- each with 8-15 properties using standard vocabularies (schema.org, FOAF, Dublin Core, SKOS), rich inter-type relationships, SHACL shapes for form generation (sh:property, sh:order, sh:group, sh:name, sh:datatype, sh:class), view specifications stored as RDF, and seed data demonstrating the graph's power.

**Primary recommendation:** Use PyYAML + Pydantic for manifest validation, rdflib Graph.parse(format="json-ld") for loading archive files, SPARQL INSERT DATA with GRAPH clauses for writing to model-specific named graphs, and SPARQL CLEAR GRAPH for removal. The install pipeline should be a single service class (ModelService) that orchestrates the full validate-and-load workflow.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **Starter Model Content**: Fully fleshed out -- each type (Projects, People, Notes, Concepts) gets 8-15 properties covering common use cases. Rich relationships pre-defined: Project hasParticipant Person, Note isAbout Concept, Project hasNote Note, etc. Ship with example seed data (a sample project, a few people, some notes, linked concepts) so the system feels alive on first install. Full view set: each type gets a default table view, a card view, and at least one graph query -- Phase 5 renderers will consume these.
- **Archive Format & Contents**: Directory convention (not ZIP) -- manifest.yaml at root + subdirectories for ontology/, shapes/, views/, seed/. Easy to author and version control. JSON-LD (.jsonld) serialization for all RDF files (ontology, shapes, views, seed data). View specs stored as RDF in the triplestore (not JSON config files) -- everything lives in the graph, consistent and queryable. Starter model shipped in the repo at a known path (e.g., models/basic-pkm/), installed automatically on first startup.
- **Install/Remove Behavior**: Multiple models can be installed simultaneously -- namespace prefixes prevent collisions. Removing a model is blocked if user data exists for that model's types -- warn and require explicit data deletion first. No model upgrades in v1 -- remove and reinstall only (per REQUIREMENTS.md: model migrations are out of scope). Basic PKM auto-installs on first run when no models are detected -- user sees data immediately.
- **Validation & Error UX**: Detailed validation report on failure -- structured list of every error (which file, what rule, what's wrong). Errors block install, warnings allow install to proceed -- critical issues (missing manifest, broken references) vs minor issues (missing descriptions). Model-prefixed IRIs enforced -- all IRIs must use a namespace derived from modelId (e.g., urn:sempkm:model:{modelId}:) to prevent cross-model collisions. Full cross-file reference integrity checks -- shapes must reference ontology classes, views must reference valid types, seed data must conform to shapes.

### Claude's Discretion
- Exact properties for each type in Basic PKM (within the "fully fleshed out" constraint)
- manifest.yaml schema design
- Named graph strategy for model artifacts (how ontology/shapes/views/seed are stored)
- Validation rule severity assignments (which are errors vs warnings)

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MODL-01 | User can install a Mental Model from a .sempkm-model archive via the admin UI | ModelService.install() pipeline: parse manifest.yaml with Pydantic, load JSON-LD files with rdflib, validate IRI namespacing and reference integrity, write to model-specific named graphs via SPARQL INSERT DATA. Admin UI is Phase 4 (ADMN-02); this phase builds the backend service with API endpoints. |
| MODL-02 | User can remove an installed Mental Model via the admin UI | ModelService.remove(): check for user data referencing model types via SPARQL ASK, block if found, otherwise CLEAR GRAPH for each model named graph and remove model registry entry. Admin UI is Phase 4; this phase builds the backend. |
| MODL-03 | User can view a list of installed Mental Models with name, version, and description | Model registry stored as triples in a dedicated named graph (urn:sempkm:models). SPARQL query returns all installed models with metadata. GET /api/models endpoint. |
| MODL-04 | System validates manifest.yaml against schema on install (modelId, version, entrypoints, exports) | Pydantic BaseModel for ManifestSchema with required fields (modelId, version, name, description, namespace, entrypoints). PyYAML safe_load() + model_validate(). Validation errors collected into structured report. |
| MODL-05 | System validates ID uniqueness, namespacing rules, and reference integrity on install | Three-pass validation: (1) IRI namespace check -- all IRIs must start with model namespace prefix, (2) reference integrity -- shapes reference ontology classes, views reference valid types, seed data uses defined types, (3) ID uniqueness -- no IRI collisions with already-installed models. |
| MODL-06 | A starter Mental Model (Basic PKM) ships with the system providing Projects, People, Notes, and Concepts with shapes, views, and seed data | Directory at models/basic-pkm/ with manifest.yaml, ontology/basic-pkm.jsonld (OWL classes + properties using schema.org/FOAF/Dublin Core/SKOS), shapes/basic-pkm.jsonld (SHACL NodeShapes with sh:property/sh:order/sh:group), views/basic-pkm.jsonld (view specs as RDF), seed/basic-pkm.jsonld (example data). Auto-installed on first startup. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| rdflib | >=7.5.0 (existing) | Parse JSON-LD files, manipulate RDF graphs, serialize to N-Triples for SPARQL INSERT | Already in project; built-in JSON-LD parser since v6.0; Graph.parse(format="json-ld") is the standard way to load JSON-LD |
| PyYAML | >=6.0 | Parse manifest.yaml files safely | yaml.safe_load() is the standard Python YAML parser; lightweight, no code execution risk |
| pydantic | >=2.0 (existing via pydantic-settings) | Validate manifest schema with type checking and constraints | Already in project via pydantic-settings; BaseModel.model_validate() provides declarative schema validation with detailed error messages |
| pyshacl | >=0.31.0 (existing) | Validate seed data against shapes during install | Already in project from Phase 2; used to verify seed data conforms to the model's own SHACL shapes |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| httpx | >=0.28 (existing) | Triplestore communication | Already in project via TriplestoreClient |
| pathlib (stdlib) | N/A | Directory traversal for archive loading | Iterate model directory structure, resolve file paths |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Directory convention | ZIP archives (.sempkm-model) | ZIP would need extraction, harder to author/version-control. Directory convention is git-friendly and directly editable. User decision is directory convention. |
| JSON-LD for all RDF | Turtle (.ttl) | Turtle is more human-readable for RDF experts, but JSON-LD is more accessible to web developers and is already used in the project's JSON-LD utilities. User decision is JSON-LD. |
| PyYAML + Pydantic | jsonschema library | jsonschema requires separate schema definition; Pydantic models are more Pythonic, provide better error messages, and are already in the project. |
| SPARQL INSERT DATA (per-file) | RDF4J Graph Store Protocol (PUT) | Graph Store Protocol could upload JSON-LD directly via HTTP PUT with Content-Type: application/ld+json. However, the existing TriplestoreClient uses SPARQL, and INSERT DATA gives more control over error handling within transactions. Consistency with existing patterns wins. |
| Separate named graphs per artifact type | Single named graph per model | Separate graphs (ontology, shapes, views, seed) allow selective loading and querying. Single graph is simpler but loses the ability to query just shapes or just views. Separate graphs recommended. |

**Installation:**
```bash
pip install pyyaml>=6.0
```

Add to `backend/pyproject.toml` dependencies:
```toml
dependencies = [
    # ... existing ...
    "pyyaml>=6.0",
]
```

Note: rdflib, pyshacl, pydantic-settings (which includes pydantic) are already installed. Only PyYAML is new.

## Architecture Patterns

### Recommended Project Structure
```
backend/app/
├── commands/           # (existing) Command handlers
├── events/             # (existing) Event store
├── health/             # (existing) Health endpoint
├── rdf/                # (existing) Namespace, IRI minting, JSON-LD utils
├── sparql/             # (existing) SPARQL query endpoint
├── triplestore/        # (existing) RDF4J client
├── services/           # (existing) Service layer
│   ├── labels.py       # (existing) Label resolution
│   ├── prefixes.py     # (existing) Prefix registry
│   ├── validation.py   # (existing) SHACL validation
│   └── models.py       # NEW: ModelService - install/remove/list Mental Models
├── validation/         # (existing) Validation infrastructure
├── models/             # NEW: Mental Model domain
│   ├── __init__.py
│   ├── manifest.py     # ManifestSchema Pydantic model + parser
│   ├── loader.py       # Load JSON-LD files from archive directory into rdflib Graphs
│   ├── validator.py    # Archive validation (IRI namespacing, reference integrity)
│   ├── registry.py     # Model registry (installed models metadata in triplestore)
│   └── router.py       # API endpoints: POST /api/models/install, DELETE /api/models/{id}, GET /api/models
└── main.py             # (existing) Add models router, wire ModelService

models/                 # Model archives directory (repo root)
└── basic-pkm/          # Starter Mental Model
    ├── manifest.yaml
    ├── ontology/
    │   └── basic-pkm.jsonld
    ├── shapes/
    │   └── basic-pkm.jsonld
    ├── views/
    │   └── basic-pkm.jsonld
    └── seed/
        └── basic-pkm.jsonld
```

### Pattern 1: Manifest Schema Validation with Pydantic

**What:** Define a Pydantic BaseModel for manifest.yaml, use yaml.safe_load() + model_validate() for parsing and validation. Collect all errors into a structured validation report.

**When to use:** First step of every model install pipeline.

**Example:**
```python
# Source: Pydantic v2 docs + PyYAML docs
import yaml
from pathlib import Path
from pydantic import BaseModel, Field, field_validator

class ManifestEntrypoints(BaseModel):
    """Entrypoint file paths relative to model root."""
    ontology: str = "ontology/{modelId}.jsonld"
    shapes: str = "shapes/{modelId}.jsonld"
    views: str = "views/{modelId}.jsonld"
    seed: str | None = "seed/{modelId}.jsonld"

class ManifestSchema(BaseModel):
    """manifest.yaml schema for Mental Model archives."""
    modelId: str = Field(..., pattern=r'^[a-z][a-z0-9-]*$', min_length=2, max_length=64)
    version: str = Field(..., pattern=r'^\d+\.\d+\.\d+$')
    name: str = Field(..., min_length=1, max_length=200)
    description: str = Field(default="", max_length=2000)
    namespace: str = Field(...)  # e.g., "urn:sempkm:model:basic-pkm:"
    prefixes: dict[str, str] = Field(default_factory=dict)
    entrypoints: ManifestEntrypoints = Field(default_factory=ManifestEntrypoints)

    @field_validator("namespace")
    @classmethod
    def validate_namespace(cls, v: str, info) -> str:
        """Namespace must follow the model IRI pattern."""
        model_id = info.data.get("modelId", "")
        expected = f"urn:sempkm:model:{model_id}:"
        if v != expected:
            raise ValueError(f"namespace must be '{expected}', got '{v}'")
        return v

def parse_manifest(model_dir: Path) -> ManifestSchema:
    """Parse and validate manifest.yaml from a model directory."""
    manifest_path = model_dir / "manifest.yaml"
    with open(manifest_path) as f:
        raw = yaml.safe_load(f)
    return ManifestSchema.model_validate(raw)
```

### Pattern 2: Named Graph Strategy for Model Artifacts

**What:** Each installed model's artifacts are stored in separate named graphs, organized by artifact type. This enables selective querying (e.g., fetch all shapes from all models, fetch only one model's ontology) and clean removal.

**When to use:** During model install (write) and for shapes loading, view resolution, and model removal.

**Named graph IRI patterns:**
```
urn:sempkm:model:{modelId}:ontology   - OWL classes and properties
urn:sempkm:model:{modelId}:shapes     - SHACL NodeShapes and PropertyShapes
urn:sempkm:model:{modelId}:views      - View specifications (SPARQL + renderer config)
urn:sempkm:model:{modelId}:seed       - Example seed data
urn:sempkm:models                     - Model registry (installed models metadata)
```

**Example:**
```python
# Source: Architecture decision
from dataclasses import dataclass

@dataclass
class ModelGraphs:
    """Named graph IRIs for a model's artifacts."""
    model_id: str

    @property
    def ontology(self) -> str:
        return f"urn:sempkm:model:{self.model_id}:ontology"

    @property
    def shapes(self) -> str:
        return f"urn:sempkm:model:{self.model_id}:shapes"

    @property
    def views(self) -> str:
        return f"urn:sempkm:model:{self.model_id}:views"

    @property
    def seed(self) -> str:
        return f"urn:sempkm:model:{self.model_id}:seed"

    @property
    def all_graphs(self) -> list[str]:
        return [self.ontology, self.shapes, self.views, self.seed]
```

### Pattern 3: JSON-LD Loading Pipeline

**What:** Load JSON-LD files from the model archive into rdflib Graphs, then serialize to N-Triples for SPARQL INSERT DATA into named graphs. Use rdflib's built-in JSON-LD parser.

**When to use:** During model install, after manifest validation passes.

**Example:**
```python
# Source: rdflib docs (JSON-LD support built-in since v6.0)
from pathlib import Path
from rdflib import Graph

def load_jsonld_file(file_path: Path) -> Graph:
    """Load a JSON-LD file into an rdflib Graph."""
    g = Graph()
    g.parse(str(file_path), format="json-ld")
    return g

async def write_graph_to_named_graph(
    client: TriplestoreClient,
    graph: Graph,
    named_graph_iri: str,
) -> None:
    """Write an rdflib Graph into a named graph via SPARQL INSERT DATA."""
    if len(graph) == 0:
        return

    # Serialize to N-Triples (each line is a complete triple)
    ntriples = graph.serialize(format="nt")

    # Insert into named graph
    sparql = f"INSERT DATA {{ GRAPH <{named_graph_iri}> {{ {ntriples} }} }}"
    await client.update(sparql)
```

### Pattern 4: IRI Namespace Validation

**What:** Verify all IRIs defined in a model's RDF files use the model's namespace prefix. This prevents cross-model IRI collisions and ensures clean removal.

**When to use:** During model install, after loading JSON-LD files but before writing to triplestore.

**Example:**
```python
# Source: Architecture decision (model-prefixed IRIs enforced)
from rdflib import Graph, URIRef, BNode

@dataclass
class ValidationError:
    file: str
    subject: str
    rule: str
    message: str
    severity: str = "error"  # "error" or "warning"

def validate_iri_namespacing(
    graph: Graph,
    model_namespace: str,
    file_name: str,
    allowed_external_namespaces: set[str] | None = None,
) -> list[ValidationError]:
    """Check that all subject IRIs use the model's namespace."""
    errors = []
    allowed = allowed_external_namespaces or {
        "http://www.w3.org/",           # RDF, RDFS, OWL, XSD, SHACL, SKOS
        "http://purl.org/dc/",          # Dublin Core
        "https://schema.org/",          # Schema.org
        "http://xmlns.com/foaf/",       # FOAF
    }

    for s in set(graph.subjects()):
        if isinstance(s, BNode):
            continue
        s_str = str(s)
        # Subject IRIs defined by this model must use model namespace
        if not s_str.startswith(model_namespace):
            # Check if it's an allowed external vocabulary reference
            if not any(s_str.startswith(ns) for ns in allowed):
                errors.append(ValidationError(
                    file=file_name,
                    subject=s_str,
                    rule="iri-namespace",
                    message=f"Subject IRI '{s_str}' does not use model namespace '{model_namespace}'",
                ))
    return errors
```

### Pattern 5: Reference Integrity Validation

**What:** Verify cross-file references: shapes must reference classes defined in the ontology, views must reference valid types, seed data must use types from the ontology.

**When to use:** During model install, after loading all JSON-LD files.

**Example:**
```python
# Source: Architecture decision (full cross-file reference integrity checks)
from rdflib import Graph, URIRef
from rdflib.namespace import RDF, SH

def validate_reference_integrity(
    ontology_graph: Graph,
    shapes_graph: Graph,
    views_graph: Graph,
    seed_graph: Graph,
    model_namespace: str,
) -> list[ValidationError]:
    """Verify cross-file references between model artifacts."""
    errors = []

    # Collect all classes defined in ontology
    ontology_classes = set()
    for cls in ontology_graph.subjects(RDF.type, URIRef("http://www.w3.org/2002/07/owl#Class")):
        ontology_classes.add(str(cls))

    # Check shapes reference valid ontology classes (sh:targetClass)
    for shape in shapes_graph.subjects(RDF.type, SH.NodeShape):
        for target_class in shapes_graph.objects(shape, SH.targetClass):
            if str(target_class).startswith(model_namespace):
                if str(target_class) not in ontology_classes:
                    errors.append(ValidationError(
                        file="shapes",
                        subject=str(shape),
                        rule="ref-integrity-shape-class",
                        message=f"Shape targets class '{target_class}' not defined in ontology",
                    ))

    # Check seed data uses types defined in ontology
    for s, _, o in seed_graph.triples((None, RDF.type, None)):
        if str(o).startswith(model_namespace):
            if str(o) not in ontology_classes:
                errors.append(ValidationError(
                    file="seed",
                    subject=str(s),
                    rule="ref-integrity-seed-type",
                    message=f"Seed data uses type '{o}' not defined in ontology",
                ))

    return errors
```

### Pattern 6: Model Registry in Triplestore

**What:** Track installed models as RDF triples in a dedicated named graph (`urn:sempkm:models`). Each model gets a registry entry with metadata from the manifest.

**When to use:** During install (add entry), remove (delete entry), and list (query entries).

**Example:**
```python
# Source: Architecture decision
# Registry triples pattern:
# GRAPH <urn:sempkm:models> {
#   <urn:sempkm:model:basic-pkm> a sempkm:MentalModel ;
#     sempkm:modelId "basic-pkm" ;
#     sempkm:version "1.0.0" ;
#     dcterms:title "Basic PKM" ;
#     dcterms:description "Personal knowledge management..." ;
#     sempkm:namespace "urn:sempkm:model:basic-pkm:" ;
#     sempkm:installedAt "2026-02-21T..." .
# }

MODELS_GRAPH = "urn:sempkm:models"

async def list_installed_models(client: TriplestoreClient) -> list[dict]:
    """Query the model registry for all installed models."""
    query = f"""
    SELECT ?model ?modelId ?version ?name ?description ?installedAt
    WHERE {{
      GRAPH <{MODELS_GRAPH}> {{
        ?model a <urn:sempkm:MentalModel> ;
               <urn:sempkm:modelId> ?modelId ;
               <urn:sempkm:version> ?version ;
               <http://purl.org/dc/terms/title> ?name .
        OPTIONAL {{ ?model <http://purl.org/dc/terms/description> ?description }}
        OPTIONAL {{ ?model <urn:sempkm:installedAt> ?installedAt }}
      }}
    }}
    ORDER BY ?name
    """
    result = await client.query(query)
    return [
        {
            "modelId": b["modelId"]["value"],
            "version": b["version"]["value"],
            "name": b["name"]["value"],
            "description": b.get("description", {}).get("value", ""),
            "installedAt": b.get("installedAt", {}).get("value", ""),
        }
        for b in result.get("results", {}).get("bindings", [])
    ]
```

### Pattern 7: User Data Check Before Model Removal

**What:** Before removing a model, check if any user data in the current state graph uses types defined by the model. If found, block removal and report which types have data.

**When to use:** During model removal.

**Example:**
```python
# Source: Architecture decision (removing blocked if user data exists)
async def check_user_data_exists(
    client: TriplestoreClient,
    model_namespace: str,
    ontology_graph: Graph,
) -> list[str]:
    """Check if user data exists for any types defined by this model."""
    types_with_data = []

    # Get all classes defined by this model
    for cls in ontology_graph.subjects(RDF.type, URIRef("http://www.w3.org/2002/07/owl#Class")):
        cls_str = str(cls)
        if not cls_str.startswith(model_namespace):
            continue

        # ASK if any instance exists in the current state graph
        ask_query = f"""
        ASK {{
          GRAPH <urn:sempkm:current> {{
            ?s a <{cls_str}> .
          }}
        }}
        """
        result = await client.query(ask_query)
        if result.get("boolean", False):
            types_with_data.append(cls_str)

    return types_with_data
```

### Pattern 8: Shapes Loader Integration with Validation Service

**What:** Replace the `empty_shapes_loader` from Phase 2 with a real shapes loader that aggregates SHACL shapes from all installed models. The loader fetches shapes from model named graphs.

**When to use:** During app startup (wire into ValidationService) and after model install/remove (shapes change).

**Example:**
```python
# Source: Existing ValidationService + Phase 2 research
from rdflib import Graph

async def model_shapes_loader(client: TriplestoreClient) -> Graph:
    """Load all SHACL shapes from installed Mental Models.

    Replaces the empty_shapes_loader from Phase 2.
    Fetches shapes from all model shapes graphs via SPARQL CONSTRUCT.
    """
    # Get all installed model IDs
    models = await list_installed_models(client)
    if not models:
        return Graph()  # No models installed, return empty (same as Phase 2)

    # Build UNION of all model shapes graphs
    from_clauses = "\n".join(
        f"FROM <urn:sempkm:model:{m['modelId']}:shapes>"
        for m in models
    )

    query = f"""
    CONSTRUCT {{ ?s ?p ?o }}
    {from_clauses}
    WHERE {{ ?s ?p ?o }}
    """

    turtle_bytes = await client.construct(query)
    shapes_graph = Graph()
    if turtle_bytes.strip():
        shapes_graph.parse(data=turtle_bytes, format="turtle")

    return shapes_graph
```

### Pattern 9: View Specs as RDF

**What:** View specifications stored as RDF triples in the triplestore, not as JSON config files. Each view has a type, a target class, a SPARQL query (stored as a literal), and renderer configuration.

**When to use:** When defining views in the Basic PKM model and when Phase 5 renderers consume view specs.

**Example:**
```json
{
  "@context": {
    "sempkm": "urn:sempkm:",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#"
  },
  "@graph": [
    {
      "@id": "urn:sempkm:model:basic-pkm:view:projects-table",
      "@type": "sempkm:ViewSpec",
      "rdfs:label": "Projects Table",
      "sempkm:targetClass": { "@id": "urn:sempkm:model:basic-pkm:Project" },
      "sempkm:rendererType": "table",
      "sempkm:sparqlQuery": "SELECT ?s ?title ?status ?start ?end WHERE { ?s a <urn:sempkm:model:basic-pkm:Project> ; <http://purl.org/dc/terms/title> ?title . OPTIONAL { ?s <urn:sempkm:model:basic-pkm:status> ?status } OPTIONAL { ?s <https://schema.org/startDate> ?start } OPTIONAL { ?s <https://schema.org/endDate> ?end } }",
      "sempkm:columns": "title,status,start,end",
      "sempkm:sortDefault": "title"
    }
  ]
}
```

### Pattern 10: Auto-Install on First Startup

**What:** During app startup, check if any models are installed. If none, auto-install the Basic PKM starter model from the bundled directory.

**When to use:** In the app lifespan handler, after TriplestoreClient is ready.

**Example:**
```python
# Source: Architecture decision
from pathlib import Path

STARTER_MODEL_PATH = Path(__file__).parent.parent.parent / "models" / "basic-pkm"

async def ensure_starter_model(model_service: ModelService) -> None:
    """Auto-install Basic PKM if no models are installed."""
    installed = await model_service.list_models()
    if not installed:
        logger.info("No models installed, auto-installing Basic PKM starter model")
        result = await model_service.install(STARTER_MODEL_PATH)
        if result.success:
            logger.info("Basic PKM installed successfully")
        else:
            logger.error("Failed to install Basic PKM: %s", result.errors)
```

### Anti-Patterns to Avoid
- **Loading JSON-LD directly via RDF4J REST API (Graph Store Protocol):** While RDF4J supports PUT with Content-Type: application/ld+json, the existing codebase uses SPARQL for all triplestore operations. Mixing protocols creates inconsistency and harder error handling.
- **Single named graph per model (all artifact types merged):** Loses the ability to selectively query just shapes or just views. Separate graphs per artifact type enable the shapes loader to fetch only shapes without pulling ontology/seed data.
- **Validating seed data against shapes AFTER writing to triplestore:** Validate in-memory first, then write. Writing invalid data and then discovering it fails validation leaves the triplestore in a dirty state.
- **Using ConjunctiveGraph or Dataset for parsing:** The rdflib ConjunctiveGraph has known issues with JSON-LD parsing and is deprecated. Use plain Graph objects and manage named graphs via SPARQL INSERT DATA.
- **Storing SPARQL queries as Python string constants:** View specs with SPARQL queries should be stored in the RDF files (JSON-LD) within the model archive, not hardcoded in Python. The SPARQL query is a literal value on the view spec resource in the graph.
- **Allowing model removal without user data check:** If user data references model types and the model is removed, the data becomes orphaned (no shapes, no labels, no views). Always check first.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| YAML parsing | Custom YAML tokenizer | PyYAML yaml.safe_load() | YAML spec is complex; safe_load prevents code execution attacks |
| Manifest validation | Custom field-by-field validation | Pydantic BaseModel.model_validate() | Declarative, produces detailed error messages, handles nested models, already in project |
| JSON-LD parsing | Custom JSON-LD processor | rdflib Graph.parse(format="json-ld") | JSON-LD 1.1 is a complex spec with context resolution, blank node handling, etc.; rdflib handles it all |
| IRI validation | Regex-based IRI checker | rdflib URIRef + string prefix check | rdflib handles IRI normalization; prefix check is simple string startswith() |
| Seed data validation | Custom type checker | pyshacl.validate() | Already in project; validates seed data against shapes with full SHACL compliance |
| RDF serialization to SPARQL | Custom triple formatter | rdflib Graph.serialize(format="nt") | N-Triples format embeds directly in SPARQL INSERT DATA; handles escaping, datatypes, language tags |

**Key insight:** The model install pipeline looks deceptively simple (load files, write to triplestore) but the validation layer is where complexity lives. IRI namespacing, cross-file reference integrity, and seed-vs-shapes conformance are all constraint-checking problems -- Pydantic handles the manifest, and pyshacl handles the RDF conformance. Don't build custom validators for either.

## Common Pitfalls

### Pitfall 1: JSON-LD Context Resolution Failures
**What goes wrong:** JSON-LD files with external @context URLs (e.g., "https://schema.org/") cause rdflib to attempt HTTP fetches during parsing, which fails in Docker containers without internet access or times out.
**Why it happens:** JSON-LD spec allows remote context documents. rdflib's JSON-LD parser follows the spec and tries to fetch them.
**How to avoid:** All JSON-LD files in model archives MUST use inline @context (local prefix mappings), never remote URLs. Validate this during the manifest/file loading step. The existing `SEMPKM_CONTEXT` in `app/rdf/jsonld.py` already follows this pattern.
**Warning signs:** Model install hangs for 30 seconds then fails with a connection error. Works on developer machine but fails in Docker.

### Pitfall 2: N-Triples Serialization Issues in SPARQL INSERT DATA
**What goes wrong:** rdflib's N-Triples serializer may produce output with blank lines or comments that break SPARQL INSERT DATA syntax.
**Why it happens:** N-Triples format allows blank lines and comments, but SPARQL INSERT DATA blocks don't expect them.
**How to avoid:** Filter out blank lines and comment lines from N-Triples output before embedding in SPARQL. Or serialize triple-by-triple using the existing `_serialize_rdf_term()` from `app/events/store.py`.
**Warning signs:** SPARQL UPDATE fails with parse error on lines containing only whitespace.

### Pitfall 3: Named Graph Cleanup on Failed Install
**What goes wrong:** Model install writes ontology and shapes graphs, then fails during seed data validation. Orphaned partial data remains in the triplestore.
**Why it happens:** Without transactional install, each SPARQL INSERT DATA is committed independently.
**How to avoid:** Use RDF4J transactions (begin_transaction/commit_transaction/rollback_transaction) to wrap the entire install. The existing TriplestoreClient already supports transactions. If any step fails, rollback clears all partial writes.
**Warning signs:** After a failed install, querying the triplestore shows partial model data.

### Pitfall 4: IRI Namespace Validation False Positives on External Vocabulary References
**What goes wrong:** IRI namespace validation rejects shapes that use sh:targetClass, rdf:type, or other standard vocabulary terms because they don't start with the model namespace.
**Why it happens:** The validator checks ALL IRIs, not just model-defined IRIs. Standard vocabulary IRIs (rdf:, rdfs:, sh:, owl:, etc.) are intentionally external.
**How to avoid:** Only validate subject IRIs that define new resources. Skip IRIs from known external vocabularies (W3C namespaces, schema.org, Dublin Core, FOAF, etc.). Predicate and object IRIs referencing external vocabularies are expected.
**Warning signs:** Every model fails validation with hundreds of "IRI does not use model namespace" errors on standard vocabulary terms.

### Pitfall 5: Seed Data Written to Model Graph Instead of Current State
**What goes wrong:** Seed data is written to the model's seed named graph but not materialized into `urn:sempkm:current`, so it's invisible to normal SPARQL queries, forms, and views.
**Why it happens:** Confusion between storing seed data as a model artifact vs. making it available as user-visible data.
**How to avoid:** Seed data must be written to BOTH the model's seed graph (for provenance/cleanup) AND materialized into `urn:sempkm:current` (for visibility). On model removal, delete seed data from both locations. Alternatively, write seed data only to `urn:sempkm:current` via the existing EventStore.commit() to maintain event sourcing consistency, and just keep the seed graph as an archive reference.
**Warning signs:** Fresh install shows no data in the UI despite seed data files being present. SPARQL queries against `urn:sempkm:current` return empty results.

### Pitfall 6: Shapes Loader Returns Stale Cache After Model Install/Remove
**What goes wrong:** After installing or removing a model, the validation service continues using the old shapes graph because the shapes loader was cached or created at startup.
**Why it happens:** The shapes loader callable is created once during app startup. If it caches the shapes graph, it won't reflect new model installs/removes.
**How to avoid:** The shapes loader should always fetch fresh shapes from the triplestore (via SPARQL CONSTRUCT). Alternatively, provide a cache invalidation hook that ModelService calls after install/remove.
**Warning signs:** Validation reports don't reflect newly installed shapes. New model types pass validation even without shapes constraints.

### Pitfall 7: Model Registry Not Checked Before Duplicate Install
**What goes wrong:** Installing the same model twice creates duplicate triples in the registry and potentially duplicate data in named graphs.
**Why it happens:** No idempotency check in the install pipeline.
**How to avoid:** Before install, check if a model with the same modelId is already installed. If so, reject with a clear error message ("Model 'basic-pkm' is already installed. Remove it first to reinstall.").
**Warning signs:** `list_models()` returns duplicate entries. Named graphs have duplicate triples.

## Code Examples

Verified patterns from official sources:

### JSON-LD Parsing with rdflib
```python
# Source: rdflib docs (JSON-LD support built-in since v6.0)
# Verified: rdflib >=7.5.0 in project's pyproject.toml
from rdflib import Graph

g = Graph()
g.parse("models/basic-pkm/ontology/basic-pkm.jsonld", format="json-ld")
print(f"Loaded {len(g)} triples")

# Iterate subjects to check namespacing
for s in set(g.subjects()):
    print(s)
```

### YAML Manifest Parsing with Pydantic
```python
# Source: Pydantic v2 docs + PyYAML docs
# Pattern verified against multiple community examples
import yaml
from pydantic import BaseModel, ValidationError

class ManifestSchema(BaseModel):
    modelId: str
    version: str
    name: str
    # ... other fields

try:
    with open("manifest.yaml") as f:
        raw = yaml.safe_load(f)
    manifest = ManifestSchema.model_validate(raw)
except ValidationError as e:
    # e.errors() returns list of dicts with loc, msg, type
    for error in e.errors():
        print(f"  {error['loc']}: {error['msg']}")
```

### SPARQL CLEAR GRAPH for Model Removal
```python
# Source: W3C SPARQL 1.1 Update specification
# Verified: RDF4J 5.0.1 supports CLEAR GRAPH
async def clear_model_graphs(client: TriplestoreClient, model_id: str) -> None:
    """Remove all data for a model by clearing its named graphs."""
    graphs = ModelGraphs(model_id)
    for graph_iri in graphs.all_graphs:
        await client.update(f"CLEAR SILENT GRAPH <{graph_iri}>")

    # Remove registry entry
    await client.update(f"""
    DELETE WHERE {{
      GRAPH <urn:sempkm:models> {{
        <urn:sempkm:model:{model_id}> ?p ?o .
      }}
    }}
    """)
```

### SPARQL ASK for User Data Check
```python
# Source: W3C SPARQL 1.1 Query Language
# Verified: RDF4J supports ASK queries
async def has_user_data(client: TriplestoreClient, class_iri: str) -> bool:
    """Check if any instances of a class exist in the current state graph."""
    result = await client.query(f"""
    ASK {{
      GRAPH <urn:sempkm:current> {{
        ?s a <{class_iri}> .
      }}
    }}
    """)
    return result.get("boolean", False)
```

### Writing rdflib Graph to Named Graph via SPARQL INSERT DATA
```python
# Source: Existing pattern in app/events/store.py + app/services/validation.py
# Uses the same _serialize_rdf_term pattern already in the codebase
from rdflib import Graph, URIRef, Literal, BNode

async def insert_graph_into_named_graph(
    client: TriplestoreClient,
    graph: Graph,
    named_graph_iri: str,
) -> None:
    """Write an rdflib Graph to a named graph in the triplestore."""
    if len(graph) == 0:
        return

    # Build triple lines using existing serialization pattern
    triple_lines = []
    for s, p, o in graph:
        triple_lines.append(
            f"  {_rdf_term_to_sparql(s)} {_rdf_term_to_sparql(p)} {_rdf_term_to_sparql(o)} ."
        )
    triples_str = "\n".join(triple_lines)

    await client.update(
        f"INSERT DATA {{ GRAPH <{named_graph_iri}> {{\n{triples_str}\n}} }}"
    )
```

### Basic PKM Ontology Structure (JSON-LD)
```json
{
  "@context": {
    "owl": "http://www.w3.org/2002/07/owl#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "schema": "https://schema.org/",
    "dcterms": "http://purl.org/dc/terms/",
    "foaf": "http://xmlns.com/foaf/0.1/",
    "skos": "http://www.w3.org/2004/02/skos/core#",
    "bpkm": "urn:sempkm:model:basic-pkm:"
  },
  "@graph": [
    {
      "@id": "urn:sempkm:model:basic-pkm:ontology",
      "@type": "owl:Ontology",
      "rdfs:label": "Basic PKM Ontology",
      "dcterms:description": "Core types for personal knowledge management"
    },
    {
      "@id": "bpkm:Project",
      "@type": "owl:Class",
      "rdfs:label": "Project",
      "rdfs:comment": "A project or initiative being tracked"
    },
    {
      "@id": "bpkm:Person",
      "@type": "owl:Class",
      "rdfs:label": "Person",
      "rdfs:comment": "A person known to the user"
    },
    {
      "@id": "bpkm:Note",
      "@type": "owl:Class",
      "rdfs:label": "Note",
      "rdfs:comment": "A note, observation, or piece of knowledge"
    },
    {
      "@id": "bpkm:Concept",
      "@type": "owl:Class",
      "rdfs:label": "Concept",
      "rdfs:comment": "An abstract concept, topic, or domain area"
    }
  ]
}
```

### Basic PKM SHACL Shape Structure (JSON-LD)
```json
{
  "@context": {
    "sh": "http://www.w3.org/ns/shacl#",
    "rdfs": "http://www.w3.org/2000/01/rdf-schema#",
    "xsd": "http://www.w3.org/2001/XMLSchema#",
    "dcterms": "http://purl.org/dc/terms/",
    "schema": "https://schema.org/",
    "bpkm": "urn:sempkm:model:basic-pkm:"
  },
  "@graph": [
    {
      "@id": "bpkm:ProjectShape",
      "@type": "sh:NodeShape",
      "sh:targetClass": { "@id": "bpkm:Project" },
      "rdfs:label": "Project Shape",
      "sh:property": [
        {
          "sh:path": { "@id": "dcterms:title" },
          "sh:name": "Title",
          "sh:datatype": { "@id": "xsd:string" },
          "sh:minCount": 1,
          "sh:maxCount": 1,
          "sh:order": 1
        },
        {
          "sh:path": { "@id": "dcterms:description" },
          "sh:name": "Description",
          "sh:datatype": { "@id": "xsd:string" },
          "sh:maxCount": 1,
          "sh:order": 2
        },
        {
          "sh:path": { "@id": "bpkm:status" },
          "sh:name": "Status",
          "sh:datatype": { "@id": "xsd:string" },
          "sh:in": { "@list": ["active", "completed", "on-hold", "cancelled"] },
          "sh:maxCount": 1,
          "sh:order": 3,
          "sh:defaultValue": "active"
        },
        {
          "sh:path": { "@id": "schema:startDate" },
          "sh:name": "Start Date",
          "sh:datatype": { "@id": "xsd:date" },
          "sh:maxCount": 1,
          "sh:order": 4
        }
      ]
    }
  ]
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| rdflib-jsonld plugin (separate) | rdflib >=6.0 built-in JSON-LD | 2021 | No separate plugin needed; JSON-LD parser/serializer included in rdflib |
| ConjunctiveGraph for named graphs | Dataset (or plain Graph + SPARQL) | rdflib 7.x | ConjunctiveGraph is deprecated; use plain Graph + SPARQL INSERT DATA for named graph management |
| Pydantic v1 BaseModel.parse_obj() | Pydantic v2 BaseModel.model_validate() | 2023 | New API; parse_obj deprecated in v2 |
| PyYAML yaml.load() | PyYAML yaml.safe_load() | Long-standing | safe_load prevents arbitrary code execution; always use safe_load |

**Deprecated/outdated:**
- rdflib-jsonld: Deprecated since rdflib 6.0.1. Do not install separately.
- ConjunctiveGraph: Deprecated in rdflib 7.x. Use plain Graph objects for loading and SPARQL for named graph operations.
- Pydantic v1 validators: Use v2 @field_validator with mode="before"/"after".

## Open Questions

1. **Seed data materialization strategy**
   - What we know: Seed data needs to be visible in `urn:sempkm:current` for the UI, views, and SPARQL queries to work. It also needs to be tracked for cleanup on model removal.
   - What's unclear: Should seed data be materialized via EventStore.commit() (maintaining event sourcing consistency) or via direct SPARQL INSERT DATA into `urn:sempkm:current` (simpler but bypasses event log)?
   - Recommendation: Use EventStore.commit() for seed data materialization. This maintains the event sourcing invariant (all data changes flow through events), creates an audit trail for seed data, and enables undo/replay. The seed data archive graph serves as provenance only. The downside is more events in the event log, but these are clearly labeled as "model.install" operations.

2. **Ontology triples in current graph vs model graph only**
   - What we know: Ontology classes and properties need to be queryable for label resolution (rdfs:label on classes), type lookups, and SHACL sh:targetClass resolution.
   - What's unclear: Should ontology triples also be materialized into `urn:sempkm:current`, or should services query model-specific graphs directly?
   - Recommendation: Keep ontology triples only in model named graphs. The label service and SPARQL queries can be extended to include model graphs via FROM clauses. This avoids mixing model infrastructure with user data in the current graph.

3. **View spec vocabulary design**
   - What we know: Views are stored as RDF with a SPARQL query literal, a renderer type, and layout config. Phase 5 will consume them.
   - What's unclear: The exact RDF vocabulary for view specs (what properties does a ViewSpec have? Column configuration? Filter configuration?).
   - Recommendation: Define a minimal vocabulary now (sempkm:ViewSpec, sempkm:targetClass, sempkm:rendererType, sempkm:sparqlQuery) and extend in Phase 5 as renderer requirements become clear. The views JSON-LD file should be authored to be forward-compatible.

4. **Large model install performance**
   - What we know: For the Basic PKM model, we expect a few hundred triples total. This is well within single SPARQL INSERT DATA performance.
   - What's unclear: At what model size does single-request INSERT DATA become problematic? Should we chunk large models?
   - Recommendation: For v1, single INSERT DATA per graph is sufficient. If a model exceeds ~10,000 triples per artifact, consider chunking. Monitor performance during development.

## Sources

### Primary (HIGH confidence)
- [rdflib documentation](https://rdflib.readthedocs.io/) - JSON-LD parser built-in since v6.0, Graph.parse() API, serialization formats (N-Triples)
- [Pydantic v2 documentation](https://docs.pydantic.dev/latest/) - BaseModel.model_validate(), Field validators, error reporting
- [PyYAML documentation](https://pyyaml.org/) - yaml.safe_load() for safe YAML parsing
- [W3C SHACL specification](https://www.w3.org/TR/shacl/) - NodeShape, PropertyShape, sh:property, sh:order, sh:group, sh:name, sh:targetClass
- [SHACL Form Generation (DASH)](https://datashapes.org/forms.html) - sh:order for property ordering, sh:group for grouping, form generation patterns
- [W3C SPARQL 1.1 Update](https://www.w3.org/TR/sparql11-update/) - INSERT DATA, CLEAR GRAPH, DELETE WHERE syntax
- [RDF4J REST API](https://rdf4j.org/documentation/reference/rest-api/) - Transaction management (begin/commit/rollback), SPARQL update endpoints
- [pyshacl GitHub](https://github.com/RDFLib/pySHACL) - validate() API for seed data validation against shapes
- Existing codebase: `app/events/store.py` (SPARQL INSERT DATA pattern), `app/services/validation.py` (shapes loader interface), `app/services/prefixes.py` (register_model_prefixes), `app/rdf/jsonld.py` (inline JSON-LD context pattern)

### Secondary (MEDIUM confidence)
- [RDF4J SPARQL compliance](https://rdf4j.org/documentation/) - CLEAR GRAPH, ASK query support verified against GraphDB compatibility docs
- [Schema.org vocabulary](https://schema.org/) - Properties for Person (name, email, jobTitle), Project (startDate, endDate), Note (dateCreated)
- [FOAF vocabulary](http://xmlns.com/foaf/0.1/) - foaf:Person, foaf:name, foaf:mbox
- [Dublin Core Terms](http://purl.org/dc/terms/) - dcterms:title, dcterms:description, dcterms:created, dcterms:modified

### Tertiary (LOW confidence)
- View spec vocabulary design: No standard RDF vocabulary for view specifications exists. The sempkm: namespace terms (ViewSpec, rendererType, sparqlQuery) are project-specific. This design should be validated during Phase 5 when renderers are built.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All libraries already in the project except PyYAML (well-established, standard Python YAML parser). No new architectural dependencies.
- Architecture: HIGH - Patterns follow existing codebase conventions (TriplestoreClient SPARQL operations, named graph management, Pydantic models, service layer pattern). Named graph strategy is straightforward extension of existing patterns.
- Validation pipeline: HIGH - IRI namespacing is simple string prefix checking. Reference integrity is graph traversal with rdflib. Manifest validation is Pydantic. Seed data validation reuses pyshacl.
- Basic PKM content: MEDIUM - Property selection for types uses well-known vocabularies (schema.org, FOAF, Dublin Core) but exact property lists are Claude's discretion and should be reviewed during implementation.
- Pitfalls: HIGH - Based on direct code review of existing codebase and known rdflib/JSON-LD behavior patterns.

**Research date:** 2026-02-21
**Valid until:** 2026-03-21 (stable domain; all libraries are mature)
