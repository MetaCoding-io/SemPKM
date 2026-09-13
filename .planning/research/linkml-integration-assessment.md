# LinkML Integration Assessment

**Date:** 2026-08-20
**Status:** Research / recommendation — no code changes proposed for the current user-testing window

## TL;DR

LinkML fits SemPKM well — but as a **compile-time authoring layer for Mental Model bundles**, not as a runtime component. The recommendation is:

- **Do:** author Mental Model schemas as LinkML YAML and *generate* the existing bundle artifacts (OWL ontology JSON-LD + SHACL shapes JSON-LD) with a small custom generator. The generated files stay committed in `models/*/`, the bundle format stays the installation contract, and the runtime (RDF4J, pyshacl, owlrl, `ShapesService`) is untouched.
- **Don't:** replace SHACL as the runtime schema representation, put LinkML in the request path, or attempt to cover gist, SHACL-AF rules, ViewSpec SPARQL, or runtime user-created classes with it.

This addresses the two real pain points LinkML is built for — keeping four parallel hand-authored artifacts consistent, and the open "Alembic-style migrations for RDF models" idea (`.gsd/QUEUE.md`) — with zero blast radius on the running app. Nothing in the first two phases below changes runtime behavior, so it is safe to pursue during user testing.

## What LinkML is (one paragraph)

[LinkML](https://linkml.io) is a YAML-based schema language with a rich metamodel (classes, slots, enums, types, inheritance, slot groups, inverses, annotations) and a generator toolchain: `gen-owl`, `gen-shacl`, `gen-jsonld-context`, `gen-pydantic`, `gen-doc`, plus `linkml-validate` for validating instance data (JSON/YAML/RDF) against a schema, `schema-automator` for bootstrapping schemas *from* existing OWL, and LinkML-Map for declarative data transformation between schema versions. One YAML source, many derived artifacts.

## Current state (what the assessment found)

SemPKM already has a clean semantics-native architecture. The relevant facts:

1. **Mental Models are a hand-rolled schema compiler input without the compiler.** Each of the 8 bundled models hand-authors four parallel JSON-LD artifacts (ontology, shapes, views, seed) plus `manifest.yaml`, ~10,200 lines of JSON-LD for ontologies + shapes alone. The same class/property information is restated in the ontology (`owl:Class`, `rdfs:domain/range`), the shapes (`sh:targetClass`, `sh:path`, `sh:datatype`/`sh:class`), the views (full IRIs embedded in SPARQL strings), and the seed data. Consistency is enforced only partially, at install time, by `backend/app/models/validator.py`.

2. **The OWL/SHACL profile in actual use is small and closed.** Census across all 8 models: `owl:Class` ×74, `owl:DatatypeProperty` ×200, `owl:ObjectProperty` ×103, `owl:inverseOf` ×44, `rdfs:subClassOf` ×58, `owl:SymmetricProperty` ×2, one `owl:unionOf`; no `owl:Restriction`, no cardinality axioms. SHACL side: the documented SHACL-UI profile (`orig_specs/spec/shacl-ui/shacl-ui-profile.md`) is ~15 SHACL Core terms (`sh:path/name/datatype/class/in/minCount/maxCount/order/group/defaultValue/pattern/nodeKind` + `sh:PropertyGroup`) plus one custom annotation, `sempkm:editHelpText` (×363). Everything in this profile has a direct LinkML counterpart (see mapping table below).

3. **The runtime consumes triples, not files.** Bundles are loaded via rdflib into named graphs (`urn:sempkm:model:{id}:{artifact}`); forms come from `ShapesService` traversing the shapes graph into the `NodeShapeForm`/`PropertyShape`/`PropertyGroup` dataclasses (`app/services/shapes.py`), which are the narrow waist consumed by ~9 modules; validation is async pyshacl; inference is owlrl + SHACL-AF rules. None of this needs to know or care how the JSON-LD files were produced.

4. **There is no schema-evolution story.** `.gsd/QUEUE.md` ("Mental Model Schema Migrations", status: Idea) records the pain verbatim: binary install/uninstall, uninstall blocked once ABox data exists, "adding `sh:description` or `editHelpText` to shapes requires manual SPARQL graph surgery", "model authors have no iteration loop once a model is in use". Only `ModelService.refresh_artifacts()` (safe RBox refresh) has shipped.

5. **LinkML, ShEx, and JSON Schema have never been evaluated.** Zero LinkML mentions anywhere in code, docs, planning, or git history. The design docs (`.gsd/design/MENTAL-MODELS-EXPANSION-DESIGN.md`) already sketch new models as property tables that read almost exactly like LinkML slot definitions.

## Where LinkML fits

### 1. Single-source authoring for Mental Model bundles (the core fit)

One LinkML YAML file per model becomes the source of truth; a `scripts/` compiler generates the bundle artifacts that are *already* the installation contract:

```
models-src/crm/crm.yaml          (LinkML, hand-authored)
        │  gen (custom, built on linkml-runtime SchemaView)
        ▼
models/crm/ontology/crm.jsonld   (generated OWL)
models/crm/shapes/crm.jsonld     (generated SHACL, SemPKM UI profile)
models/crm/manifest.yaml         (partially generated, or kept hand-authored)
```

What this buys:

- **Consistency by construction.** A property is declared once; its `rdfs:domain/range`, its `sh:path/datatype/class`, and its cardinality can no longer drift apart. Today that drift is only partially caught (and see the validator bug in "Side findings").
- **~3–4× less authored text.** A LinkML slot declaration of ~6 lines replaces ~15 lines of ontology JSON-LD + ~10 lines of shapes JSON-LD.
- **CI-checkable models.** `linkml-validate` can validate `seed/*.jsonld` against the schema at build time (today seed data errors only surface as post-install lint results), and a CI job can assert `generated == committed` so the artifacts can never go stale.
- **A dramatically lower authoring bar.** "Write a YAML file with classes and slots" is a much smaller ask for community model authors than "hand-write four mutually-consistent JSON-LD documents" — relevant to the marketplace ambitions.
- **Bootstrapping is cheap.** `schema-automator import-owl` can draft the LinkML YAML for the 8 existing models from their current ontologies; the shapes' UI metadata (order, groups, helptext) gets folded in by a one-off script.

Importantly, the **generated files stay committed in the repo** and mounted/packaged exactly as today. Marketplace archives, the install pipeline, `refresh_artifacts`, and every runtime consumer see no difference. The Docker "no remote `@context`" constraint (`loader.py:_check_no_remote_context`) is satisfied by inlining contexts at generation time.

### 2. The schema-migrations feature (the strategic fit)

This is the biggest long-term payoff. The QUEUE.md wish — "Alembic-style migrations for RDF models" — is very hard to build against free-form RDF graphs (diffing two arbitrary OWL+SHACL graph pairs and classifying the changes is an open-ended problem). Against two versions of a LinkML schema it becomes tractable:

- **Schema diff** between v1.0.0 and v1.1.0 YAML is a structured, classifiable operation: slot added (append-only TBox addition → safe), enum value added (safe), slot renamed / datatype changed / class removed (needs ABox transformation).
- **ABox transformations** can be expressed declaratively with LinkML-Map, or the diff can drive generation of the SPARQL UPDATE against `urn:sempkm:current` that the migration executes.
- The existing `refresh_artifacts()` becomes the executor for the "safe" class of changes; the registry's semver field becomes meaningful.

Without LinkML (or something like it), the migrations feature would end up inventing a schema-description layer anyway, just ad hoc.

### 3. Secondary wins (optional, later)

- **`gen-doc`** → per-model reference pages for `docs/guide/39-mental-model-catalog.md` and the marketplace, generated instead of hand-written.
- **`gen-pydantic`** → typed DTOs for the public `/api/shapes` / `/api/types` surface consumed by the browser extension and mobile app, replacing hand-maintained dicts.
- **`gen-jsonld-context`** → a published context for the SemPKM vocabulary (currently absent).

## Where LinkML does NOT fit — leave these guts alone

| Area | Why LinkML stays out |
|---|---|
| **Runtime validation** (pyshacl queue, lint panel) | SHACL is the right runtime lingua franca; LinkML *generates* SHACL, it doesn't replace it. No change. |
| **RDF4J storage / named graphs / event sourcing** | LinkML is schema tooling, not a store. The triples-in-named-graphs contract is load-bearing for 40+ modules. |
| **`ShapesService` and the form pipeline** | It consumes the shapes *graph*, which keeps existing exactly as-is (now generated). The `NodeShapeForm` narrow waist is untouched. |
| **Runtime user-created classes** (`app/ontology/service.py` CRUD, `urn:sempkm:user-types`) | LinkML is file/compile-time; users minting classes in the UI is a runtime path that writes triples directly. These two worlds already live in separate named graphs — keep it that way. Folding user types into LinkML would mean round-tripping YAML at runtime for no benefit. |
| **gist upper ontology** | Full OWL 2 DL with `owl:equivalentClass`/`owl:intersectionOf` class expressions that LinkML cannot represent (and which the code already flattens via `_extract_implied_subclasses`). gist remains a vendored artifact; LinkML classes simply declare gist superclasses as IRIs. |
| **SHACL-AF rules** (`models/*/rules/*.ttl`) | SPARQL CONSTRUCT rules are outside LinkML's model. Keep hand-authored Turtle; the compiler passes them through. |
| **ViewSpecs** | SPARQL strings + renderer config are not schema. Keep hand-authored — though the compiler *could* template the boring default table/card/graph specs from the class's slots, and `register_generic_views()` already reduces the need for hand-written ones. |

## Construct mapping (SemPKM profile → LinkML)

| SemPKM (OWL + SHACL) | LinkML | Notes |
|---|---|---|
| `owl:Class` + `rdfs:label`/`comment` | `class` + `title`/`description` | direct |
| `rdfs:subClassOf` (incl. gist parents) | `is_a` / `class_uri` + external parent IRI | direct |
| `owl:DatatypeProperty` + `rdfs:domain/range` | slot with scalar `range` | direct |
| `owl:ObjectProperty` + `sh:class` | slot with class `range` | direct |
| `owl:inverseOf` (×44) | slot `inverse` | direct |
| `owl:SymmetricProperty` | slot `symmetric` | direct |
| `sh:minCount`/`sh:maxCount` | `required` / `multivalued` | direct |
| `sh:in` dropdown lists (×65) | `enum` | direct, and enums become reusable |
| `sh:defaultValue` | `ifabsent` | direct |
| `sh:pattern`, min/max bounds | `pattern`, `minimum_value`/`maximum_value` | direct |
| `sh:order` (×706) | slot `rank` | direct |
| `sh:group` / `sh:PropertyGroup` (×167) | `slot_group` | direct concept match; generator emits the `PropertyGroup` nodes |
| `sh:name` display label | slot `title` | direct |
| `sempkm:editHelpText` (×363) | `annotations` | generator maps annotation → triple |
| Manifest icons/colors/settings | `annotations` on classes, or keep in manifest | either works; keeping manifest hand-authored is simplest |
| Reuse of dcterms/foaf/schema/skos | `slot_uri` per slot | direct — LinkML is explicitly built for vocabulary reuse |

**Gap:** stock `gen-shacl` and `gen-owl` will not emit the UI profile (`sh:order`, `sh:group`, `sh:name`, `sh:defaultValue`, `editHelpText`) in SemPKM's exact shape. The right move is a **custom generator** (~300–600 lines on `linkml-runtime` `SchemaView`) that emits precisely the SemPKM SHACL-UI profile and the OWL profile above. Because the measured profile is small and closed, this is a bounded, well-specified piece of work — much cheaper than bending the stock generators.

## Phased adoption (no gut-ripping)

**Phase 0 — spike (no user-visible change, safe during user testing).**
Pick the smallest model (`rss-feeds`: 140-line ontology, 232-line shapes). Hand-write its LinkML YAML, build the generator, and prove semantic equivalence with `rdflib.compare.isomorphic` between generated and current graphs. Exit criterion: generated bundle installs and passes the full e2e suite unchanged.

**Phase 1 — adopt for authoring.**
Bootstrap the other 7 models with `schema-automator` + a shapes-metadata merge script; commit YAML sources alongside generated artifacts; add the CI freshness check; update `docs/guide/19-creating-mental-models.md` with the YAML authoring path (the raw JSON-LD path remains valid — the bundle format is unchanged, so third-party authors are never forced onto LinkML). Still zero runtime change.

**Phase 2 — schema migrations.**
Build the QUEUE.md migrations feature on LinkML schema diffs: classify changes (safe RBox refresh vs. ABox-transforming), generate migration plans, track versions in the model registry. This is the first phase that touches runtime code, and by then the schema source of truth is already structured.

**Phase 3 — opportunistic codegen.**
`gen-doc` for the model catalog, `gen-pydantic` for API DTOs, published JSON-LD context.

## Risks and costs

- **New toolchain dependency** (Python `linkml`, `linkml-runtime`) — build-time only if the generator runs in CI/scripts; it never needs to be in the API container image.
- **Two representations during transition** — mitigated by the CI freshness check; the generated artifact is always what ships.
- **Custom generator maintenance** — bounded by the closed profile; changes to the SHACL-UI profile (rare, spec'd in `orig_specs/spec/shacl-ui/`) imply generator updates.
- **Expressivity ceiling** — if models ever need real OWL restrictions or exotic SHACL, those constructs would be escape-hatched (LinkML supports embedding raw annotations, and `rules/*.ttl` already demonstrates the pattern of hand-authored companion artifacts). Today's census shows nothing in the models needs it.
- **Not worth it if** model authoring stops (all 8 models frozen, no marketplace growth) — the payoff scales with the number and churn of models.

## Side findings (independent of LinkML, worth fixing)

1. **View reference-integrity check never fires.** `app/models/validator.py:20` binds `SEMPKM_TARGET_CLASS = urn:sempkm:targetClass`, but all shipped views files and `app/views/service.py:167` use `urn:sempkm:vocab:targetClass` — so check #4 in `validate_reference_integrity` silently matches nothing.
2. **Write path ignores declared datatypes.** `_to_rdf_value()` in `app/commands/handlers/object_create.py:50-79` guesses `xsd:date`/`xsd:dateTime`/IRI-ness by string sniffing instead of consulting the property's `sh:datatype` — a source of lint noise that shape-driven coercion would eliminate.
3. **`entailment_defaults` is not a declared field** on `ManifestSchema` (`app/models/manifest.py`), so Pydantic silently drops it there while `app/inference/` reads it from raw YAML — worth unifying.
4. **pyshacl runs without `ont_graph`**, so validation sees no OWL axioms (`app/services/validation.py`); intentional or not, it should be a recorded decision.
