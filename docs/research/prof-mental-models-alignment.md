# Research: PROF 1.0 and Mental Models

**Date:** 2026-09-11
**Status:** Research note (resolves the research questions in [issue #53](https://github.com/MetaCoding-io/SemPKM/issues/53))
**Goal:** Decide whether the W3C Profiles Vocabulary (PROF) 1.0 should describe, replace, or simply sit alongside the SemPKM Mental Model contract.

---

## Table of Contents

1. [Recommendation](#1-recommendation)
2. [What PROF 1.0 Is](#2-what-prof-10-is)
3. [What a Mental Model Is](#3-what-a-mental-model-is)
4. [Mapping Table](#4-mapping-table)
5. [Gaps and Ambiguities](#5-gaps-and-ambiguities)
6. [Inheritance: `prof:isProfileOf` vs. SemPKM Relations](#6-inheritance-profisprofileof-vs-sempkm-relations)
7. [Discovery, Registry, Versioning, Interchange](#7-discovery-registry-versioning-interchange)
8. [Installation and Execution Boundary](#8-installation-and-execution-boundary)
9. [Content Negotiation by Profile](#9-content-negotiation-by-profile)
10. [Maturity and Adoption Risk](#10-maturity-and-adoption-risk)
11. [Options Compared](#11-options-compared)
12. [Follow-up Issues](#12-follow-up-issues)
13. [Worked Example: PPV as a `prof:Profile`](#13-worked-example-ppv-as-a-profprofile)
14. [Sources](#14-sources)

---

## 1. Recommendation

**Partially adopt, as a derived export only. Do not change the Mental Model contract.**

- A Mental Model is **not** a `prof:Profile`. It is an executable package that *contains* one: the ontology + SHACL shapes + validation rules form a data specification that constrains and extends gist, dcterms, schema.org, SKOS and FOAF, which is exactly PROF's definition of a profile. The rest of the bundle (views, dashboards, workflows, seed, icons, settings, entailment defaults) is SemPKM application configuration that PROF has no vocabulary for.
- Roughly half of the manifest and three of the eight artifact kinds map cleanly to PROF. The other half needs SemPKM terms regardless of what PROF does.
- PROF adds nothing to dependency declaration, versioning, compatibility checking, or installation. Those concerns are covered better by DCAT 3 (`dcat:version`, `dcat:Distribution`), Dublin Core (`dcterms:requires`, `dcterms:replaces`) and the existing semver machinery.
- The one real benefit is **self-description for interchange**: a standard way to say "this archive's ontology and shapes are a profile of gist; here is the vocabulary, here are the constraints, here is the token." That is worth a small, isolated addition (generated PROF triples in the `urn:sempkm:models` registry graph plus an RDF endpoint), and nothing more.
- PROF 1.0 reached First Public Working Draft on 2026-08-20. The namespace and term set are unchanged since the 2019 Note, but the working group has open issues on the meaning of its core relation and its role vocabulary. Anything we emit must be regenerable, never hand-authored into `manifest.yaml`.

The recommendation deliberately does **not** treat standards alignment as a benefit in itself. Today no tool outside the five PROF implementations listed in the WG's own report would read what we emit. The value is defensive: a future marketplace, a SHACL-toolchain user pulling just the shapes, or a federation peer gets a standard answer to "what is this thing" at near-zero cost.

---

## 2. What PROF 1.0 Is

**Status.** *The Profiles Vocabulary 1.0*, W3C First Public Working Draft, 20 August 2026, Dataset Exchange Working Group (DXWG). This is the first step of the Recommendation track. It republishes the December 2019 Working Group Note with the same namespace (`http://www.w3.org/ns/dx/prof/`) and the same terms; the vocabulary file carries `owl:versionInfo "1.0"` and a modified date of 2026-06-24. The DXWG's April 2026 charter lists PROF and Content Negotiation by Profile as tentative deliverables "depending on the interest and availability of Working Group participants."

**Model.** Three classes, seven properties, one small role vocabulary.

| Term | Meaning |
|------|---------|
| `prof:Profile` (⊑ `dcterms:Standard`, informatively ⊑ `dcat:Resource`) | "A specification that constrains, extends, combines, or provides guidance or explanation about the usage of other specifications." |
| `prof:ResourceDescriptor` (informatively ⊑ `dcat:Distribution`) | Describes one artifact of a profile: its `dcterms:format`, what it `dcterms:conformsTo` (e.g. SHACL), its role, and its location. |
| `prof:ResourceRole` (⊑ `skos:Concept`) | The purpose an artifact serves. Open-ended; the spec ships a starter set and says communities may extend it. |
| `prof:isProfileOf` (Profile → `dcterms:Standard`) | The base specification(s). Semantics: data conforming to the profile conforms to every base. Backed by the axiom `dcterms:conformsTo ∘ prof:isProfileOf ⊑ dcterms:conformsTo`. |
| `prof:isTransitiveProfileOf` | Convenience closure of `isProfileOf`, to be asserted completely or not at all. |
| `prof:hasResource` / `prof:hasRole` / `prof:hasArtifact` | Profile → descriptor → role, and descriptor → the actual file/IRI. |
| `prof:isInheritedFrom` (descriptor → Profile) | Marks a descriptor as inherited from a base profile so clients need not walk the hierarchy. |
| `prof:hasToken` (Profile → `xsd:token`) | "A simple lexical form of identifier that may be accepted … such as API arguments or in content negotiation." |

**Roles** (`http://www.w3.org/ns/dx/prof/role/`, lowercase local names): `specification`, `guidance`, `vocabulary`, `schema`, `constraints`, `validation`, `mapping`, `example`. The `resource_roles.ttl` in the WG repository also defines `manifest` ("a resource that organizes metadata about the resources associated with a profile"); it is not in the role table of the rendered editors' draft I could reach, so treat it as unconfirmed until the next draft.

**What PROF does not have.** No version property, no dependency relation, no packaging or checksum terms, no notion of installation, no conformance-checking procedure beyond pointing at a validation artifact. It is a description vocabulary layered on Dublin Core and (informatively) DCAT.

---

## 3. What a Mental Model Is

Facts from `backend/app/models/` and the eight bundled models, since the mapping has to be against what the code does rather than what the guide says.

- **Identity.** `modelId` (`^[a-z][a-z0-9-]*$`), semver `version`, `name`, `description`, and a `namespace` forced to `urn:sempkm:model:{modelId}:`. The registry graph `urn:sempkm:models` already records the model as `<urn:sempkm:model:{id}> a sempkm:MentalModel` with `dcterms:title` and `dcterms:description`.
- **Entrypoints** (`ManifestEntrypoints`): `ontology`, `shapes`, `views` (required, JSON-LD with inline `@context` only), `seed` (optional JSON-LD), `rules` (optional Turtle, SHACL-AF), `dashboards` and `workflows` (optional JSON, manifest v2 only).
- **Other manifest content**: `prefixes`, `icons` (per type, per UI context, plus `browserVisible`), `settings`, `entailment_defaults` (which OWL 2 RL and SHACL rule regimes the inference engine runs).
- **Install semantics.** Each RDF artifact lands in its own named graph (`urn:sempkm:model:{id}:{ontology|shapes|views|seed|rules}`). Seed data is *live* data, not documentation; it includes `sempkm:SavedQuery` objects and default instances. Dashboards and workflows are parsed from JSON and stored as SQLite rows, not RDF.
- **Validation at install** (`validator.py`): every subject IRI must live in the model namespace or one of four allowed external namespaces (W3C, Dublin Core, schema.org, FOAF); shapes, views and seed must reference ontology classes.
- **Base ontology.** Every bundled model subclasses gist (`urn:sempkm:ontology:gist`, gist v14) and reuses dcterms, schema.org, SKOS and FOAF properties. Nothing in the manifest declares this; it is discoverable only from the ontology triples.
- **Relations between models.** None. There is no `dependsOn`, `extends`, or `imports` in the manifest; decision D151 says models must work standalone and cross-model edges go through the shared gist hierarchy. The only dependency mechanism in the repo is *apps* depending on models with semver ranges (`AppModelDependency`, decision D139).
- **Marketplace.** `registry.json` entries are `{id, name, version, description, archive_url, sha256}`; update is download-verify-remove-reinstall; there is no migration concept.

Two reference points used below: **business-planning** (v1.0.0, 34 classes, no rules, no dashboards) as the simple case, and **PPV** (v2.0.0, manifest v2, 12 classes, three SHACL-AF inference rules, three SPARQL constraints, five dashboards, five workflows) as the rich case.

---

## 4. Mapping Table

| Mental Model element | PROF / adjacent standard term | Fit | Notes |
|---|---|---|---|
| The model as a whole | `prof:Profile` for the *specification core* only | Partial | The package is a `dcat:Resource` with a `dcat:Distribution` (the `.tar.gz`); the profile is the ontology+shapes+rules subset. Same IRI `urn:sempkm:model:{id}` can carry both types. |
| `modelId` | `prof:hasToken` | Exact | PROF's definition ("API arguments or content negotiation") is literally what `modelId` is used for in URLs and graph names. |
| `version` | `dcat:version` (DCAT 3) or `owl:versionInfo` | Exact, not PROF | PROF has no version term. |
| `name` / `description` | `dcterms:title` / `dcterms:description` | Exact | Already emitted by `register_model()`. |
| `namespace` | none (`vann:preferredNamespaceUri` is the closest) | None | Keep `sempkm:namespace`. |
| `prefixes` | `vann:preferredNamespacePrefix` or `sh:declare` | Weak | Keep `sempkm:` terms; a PROF consumer does not need them. |
| `entrypoints.ontology` | `prof:ResourceDescriptor` with `role:vocabulary` (and `role:schema`), `dcterms:conformsTo <OWL 2>`, `dcterms:format application/ld+json` | Good | |
| `entrypoints.shapes` | descriptor with `role:schema` **and** `role:validation` (multiple roles allowed), `dcterms:conformsTo <SHACL>` | Good, ambiguous | Shapes drive form generation (schema role) and lint (validation role). Which of `schema`/`constraints`/`validation` is "right" is open in DXWG issue #85. |
| `entrypoints.rules` (SPARQL constraints part) | `role:validation` | Good | |
| `entrypoints.rules` (SHACL-AF inference part) | none | None | Deriving triples is an entailment regime, not a constraint. Needs a SemPKM role, e.g. `urn:sempkm:role:inference`. |
| `entrypoints.views` | none | None | Presentation config conforming to the SemPKM `ViewSpec` vocabulary (`urn:sempkm:vocab:`). Needs `urn:sempkm:role:presentation`. |
| `entrypoints.seed` | `role:example` | Misleading | PROF: "sample instance data conforming to the profile" (illustrative). SemPKM: installed live data including saved queries. Use a sub-role `urn:sempkm:role:seed skos:broader role:example`, or omit. |
| `entrypoints.dashboards` / `workflows` | none | None | JSON, not RDF, stored in SQLite. `urn:sempkm:role:presentation`. |
| `manifest.yaml` itself | `role:manifest` (if confirmed) | Good if it survives | Otherwise `role:specification` is wrong (that role is human-readable). |
| `icons`, `browserVisible` | none | None | UI hints; stay in the manifest. |
| `settings` | none | None | App configuration. |
| `entailment_defaults` | none | None | Execution semantics; see §8. |
| Human documentation (guide ch. 39 catalog entries) | `role:guidance` / `role:specification` | Good, currently absent | Bundles ship no README. PROF would nudge toward one; independent of PROF that is a reasonable gap to close. |
| Migrations | `role:mapping` ("conversions between two specifications") | Plausible, hypothetical | SemPKM has no migrations. If v1→v2 SPARQL UPDATE scripts ever exist, this is their role. |
| gist and reused vocabularies | `prof:isProfileOf <gist>`; `dcterms:references` for dcterms/schema.org/SKOS/FOAF | Good | See §6 for why reuse is not profiling. |
| `registry.json` entry | `dcat:Catalog` → `dcat:Resource` + `dcat:Distribution` (`dcat:downloadURL`, `spdx:checksum`, `dcat:mediaType`) | Exact, not PROF | The PROF part is only `hasToken` and the descriptors. |
| `sempkm:installedAt` | `dcterms:issued` or keep | Keep | Instance-local state, not part of the description. |
| App → model dependency (`>=1.0.0`) | none in PROF; `dcterms:requires` loses the range | None | Keep the semver specifier. |

Score: 9 of 22 rows are good or exact fits, 4 are partial or misleading, 9 have no PROF equivalent at all. Every "exact" row for identity and versioning comes from Dublin Core or DCAT, not from PROF itself.

---

## 5. Gaps and Ambiguities

**Semantic mismatches**

1. **Seed ≠ example.** `role:example` describes illustrative data. SemPKM installs seed into the live graph, and PPV's seed includes `SavedQuery` objects that are configuration. Emitting `role:example` for seed would tell a consumer it is safe to ignore, which is wrong for SemPKM.
2. **Shapes serve two roles.** Same file drives form rendering (a schema use) and lint (a validation use). PROF permits multiple roles, but the WG itself cannot yet say how `schema`, `constraints` and `validation` differ (issue #85). Our choice cannot be "wrong" today, and it cannot be stable either.
3. **Inference rules have no role.** SHACL-AF `sh:SPARQLRule` derivations are the single most SemPKM-specific artifact and PROF cannot name them. This is the clearest case for a SemPKM role extension.
4. **`hasArtifact` target.** PROF declares it an object property (an IRI), yet usage includes literal URLs and the WG has an open issue on it (#63). For installed models the natural target is the named graph IRI `urn:sempkm:model:{id}:shapes`, which is not "a downloadable file". If we emit it, the IRI must also be dereferenceable (§12, follow-up 2), or a consumer gets a dangling pointer.
5. **`ResourceDescriptor` cardinality.** The vocabulary file appears to require exactly one role and one artifact per descriptor while the prose allows several roles. Emit one descriptor per (artifact, role) pair to be safe.

**Things PROF cannot express at all**

- Presentation: views, dashboards, workflows, icons, `browserVisible`.
- Execution: `entailment_defaults`, install order, target named graphs, refresh semantics.
- Packaging: archive URL, checksum, semver ranges (DCAT/SPDX/packaging cover these).
- Relations other than "is a profile of": dependency, replacement, version lineage (Dublin Core covers these).

**Terminology drift risk in PROF itself**

- The rename of `ResourceDescriptor` has been an open issue since 2018 (#6, currently labeled "due for closing").
- "Differentiate `partOf`, `profileOf`, `extends`" (#81) is open and unassigned. It is the exact question §6 answers for SemPKM, and the WG has not answered it for itself.
- `hasArtifact` guidance (#63), definitions (#83), "data specification" definition (#80), and ADMS alignment (#79) are all open.

---

## 6. Inheritance: `prof:isProfileOf` vs. SemPKM Relations

SemPKM has three candidate relations that people might be tempted to write as `prof:isProfileOf`. Only one is.

| Relation | Example | Correct term | Why |
|---|---|---|---|
| Constrains/extends a base specification | basic-pkm and gist | `prof:isProfileOf <gist>` | Data valid under basic-pkm's shapes is gist-conformant; the ontology subclasses gist classes and adds SHACL constraints. This is PROF's definition. |
| Reuses terms from a vocabulary | basic-pkm uses `dcterms:title`, `schema:startDate` | `dcterms:references` (or nothing) | Using a term does not constrain the source specification. Asserting `isProfileOf <dcterms>` would claim every basic-pkm object "conforms to Dublin Core," which is vacuous. |
| Needs another model installed | (none today; apps → models via semver) | `dcterms:requires` plus the semver specifier in SemPKM terms | Dependency is about installation, not conformance. |
| Newer version of the same model | basic-pkm 2.2.0 replaces 2.1.0 | `dcterms:replaces` / `dcat:previousVersion` | Not profiling. |
| A future "extension model" that adds constraints on another model's types | hypothetical `basic-pkm-agile` tightening `bpkm:Task` | `prof:isProfileOf <basic-pkm>` **and** `dcterms:requires` | The only case where both apply, because the extension both depends on and narrows the base. |

Two cautions. First, the `conformsTo ∘ isProfileOf` chain axiom is OWL 2 RL-expressible, so if the PROF ontology were ever loaded into the inference engine and objects carried `dcterms:conformsTo <model>`, gist conformance would be inferred for every object. Harmless, but pointless triples; do not load PROF into `urn:sempkm:inferred`. Second, `prof:isInheritedFrom` only pays off once there is a profile hierarchy. With every model a direct profile of gist and no model-to-model extension, it has nothing to describe.

**Answer to research question 5:** yes, `prof:isProfileOf` can represent the gist relationship without overstating anything. It cannot represent dependency, and SemPKM should not repurpose it to.

---

## 7. Discovery, Registry, Versioning, Interchange

| Concern | Does PROF help? | What actually helps |
|---|---|---|
| Discovering what artifacts a model has before download | Marginally: descriptors with roles and formats | Same info in a `files` array in `registry.json` would serve every real client today |
| Registry / catalog metadata | No (PROF defers to DCAT) | `dcat:Catalog` + `dcat:Distribution` with `spdx:checksum`; `registry.json` could become JSON-LD with a context, keeping current clients working |
| Dependency declaration | No | Existing semver `SpecifierSet` machinery; `dcterms:requires` if an RDF view is wanted |
| Versioning | No | `dcat:version`, `dcat:previousVersion`, `dcterms:replaces` |
| Compatibility checks | No; PROF has no checking procedure | SHACL validation, which SemPKM already runs at install and continuously |
| Model interchange outside SemPKM | **Yes, modestly** | A PROF description lets a SHACL toolchain user identify the shapes as constraints on gist without reading `manifest.yaml`; this is the one place PROF is the right vocabulary |
| Discovery for federation peers | Marginally | `.well-known/sempkm` could list installed profiles (IRIs + tokens); peers already exchange RDF Patch per graph |

Nothing here justifies a milestone. The interchange row justifies an endpoint.

---

## 8. Installation and Execution Boundary

Whatever PROF describes, the following stay in `manifest.yaml` and code, because they are behavior rather than description:

- Entrypoint file paths and the `{modelId}` placeholder resolution.
- Named-graph targets and the install / uninstall / refresh-artifacts transactions.
- `entailment_defaults` and per-model entailment overrides (`/admin/models/{id}/entailment`).
- Seed data as live state; dashboards and workflows as SQLite rows.
- Icons, `browserVisible`, settings, prefix registration.
- Namespace enforcement and cross-file reference validation.
- Marketplace download, checksum, and update ordering.

Direction of derivation must be one-way: **manifest → PROF**, generated at install (and refresh) time, never authored by hand and never read back to drive behavior. That keeps PROF churn (§10) out of the install path.

---

## 9. Content Negotiation by Profile

*Content Negotiation by Profile* was republished as a Working Draft on 2026-07-03. It defines two functions (list profiles; get a resource by profile) and three realizations: HTTP headers (`Accept-Profile`, `Content-Profile`, `Link rel="profile"`, `Link` alternates), fixed query-string arguments (`_profile=`, `_mediatype=`, `_profile=alt`), and server-named query-string keys. Tokens map to profile IRIs via `prof:hasToken`, and the IETF header draft it depends on is still early.

Where it could apply in SemPKM:

- **Object representations.** Object IRIs are not dereferenceable as RDF today; only the WebID profile does Accept-based negotiation. If an `/objects/{iri}` RDF endpoint is ever added, `?_profile=basic-pkm` (token = `modelId`) selecting the projection of an object onto one model's properties is a real use, since one object can carry properties from several models (a Person in both crm and basic-pkm).
- **`Link: rel="profile"`** on RDF responses listing the models whose types the object has. Cheap and harmless once RDF responses exist.
- **Federation.** `Content-Profile` on outgoing patches would tell a peer which model graphs a patch assumes. Peers already know this from the graph IRIs, so it is redundant.
- **`/api/types` and `/api/shapes`.** Already filter by model via IRI convention; a `_profile` parameter would be sugar.

Assessment: nothing to build now. The only design constraint worth adopting is that `modelId` continues to be safe to use as a profile token (it already matches `xsd:token`).

---

## 10. Maturity and Adoption Risk

| Factor | State (2026-09) | Risk to SemPKM |
|---|---|---|
| Standards status | FPWD 2026-08-20; charter makes completion contingent on participant availability | Low if emit-only; a Rec might not arrive in this charter period |
| Namespace stability | Unchanged since 2018 | Low |
| Term stability | Same 3 classes / 7 properties as the 2019 Note | Low for properties; `ResourceDescriptor` rename open since 2018 |
| Role semantics | Open issues on schema/constraints/validation and on `manifest` role presence | Medium: whatever roles we emit for shapes may need regenerating |
| Core relation semantics | "profileOf vs. extends vs. partOf" open (#81) | Medium for anyone reading our `isProfileOf` |
| Implementation evidence | 5 implementations in 3 independent groups; per-element table in the WG report is empty | Low direct risk; signals a small ecosystem, so little interoperability payoff |
| Consumers of a SemPKM PROF export | None known | The benefit is speculative; keep cost proportionate |
| Related work | SHACL 1.2 Profiling (Data Shapes WG) references PROF for describing SHACL profiles | Worth watching: SemPKM is SHACL-centric and that spec may define the descriptor shape we should match |

---

## 11. Options Compared

**Option 1: No adoption.**
Cost 0. Loses nothing users can feel. Leaves "what is a Mental Model, in standard terms" answered only in prose. Perfectly defensible.

**Option 2: Expose PROF metadata alongside the existing manifest** (recommended).
Generate `prof:Profile` and descriptor triples into `urn:sempkm:models` at install/refresh; serve them as Turtle/JSON-LD; leave `manifest.yaml`, the loader, the validator and the marketplace untouched. Roughly 60 lines in `registry.register_model()` plus one router function. Regenerable when PROF changes. Provides the interchange answer from §7 and a standard description for future catalogs.

**Option 3: PROF as a first-class part of the Mental Model contract** (rejected).
Replace or mirror entrypoints with hand-authored descriptors in the manifest. Fails on the facts in §4: half the manifest has no PROF expression, so the manifest would carry two vocabularies for the same thing; the role choice for shapes is unsettled upstream; `hasArtifact` semantics are unsettled; a rename of `ResourceDescriptor` would break every bundled archive. This is the option where "standards alignment" would cost more than it returns.

---

## 12. Follow-up Issues

Only two, both small, both optional, both to be scheduled when the models registry or the marketplace is next touched rather than as their own milestone.

1. **Emit a PROF description for installed models.** In `register_model()` add `a prof:Profile`, `prof:hasToken`, `dcat:version`, `prof:isProfileOf <urn:sempkm:ontology:gist>`, and one `prof:ResourceDescriptor` per (artifact, role) pair using the roles in §13, with SemPKM roles for inference and presentation under `urn:sempkm:role:`. Remove them in `unregister_model()`. Unit tests on the generated triples.
2. **Serve it.** `GET /api/models/{model_id}/profile` returning Turtle or JSON-LD by `Accept`, and make `urn:sempkm:model:{id}:{artifact}` dereferenceable through `GET /api/models/{model_id}/artifacts/{artifact}` so `prof:hasArtifact` targets resolve. Add `profiles` to the `.well-known/sempkm` capabilities list.

Explicitly not proposed: manifest schema changes, a `dependsOn` field justified by PROF (if inter-model dependency is ever wanted it should be justified on its own and use semver ranges like apps do), content negotiation by profile, or loading the PROF ontology into inference.

Independent of PROF, one gap surfaced by the mapping is worth its own issue: bundles carry no human-readable documentation, so the guide's catalog chapter is the only `role:guidance` we have and it lives outside the archive.

---

## 13. Worked Example: PPV as a `prof:Profile`

Generated from `models/ppv/manifest.yaml` (v2.0.0, manifest v2) as follow-up 1 would produce it. Artifact IRIs are the named graphs the loader already uses; dashboards and workflows point at the archive paths because they never become RDF.

```turtle
@prefix prof:    <http://www.w3.org/ns/dx/prof/> .
@prefix role:    <http://www.w3.org/ns/dx/prof/role/> .
@prefix srole:   <urn:sempkm:role:> .
@prefix sempkm:  <urn:sempkm:> .
@prefix dcterms: <http://purl.org/dc/terms/> .
@prefix dcat:    <http://www.w3.org/ns/dcat#> .
@prefix xsd:     <http://www.w3.org/2001/XMLSchema#> .
@prefix skos:    <http://www.w3.org/2004/02/skos/core#> .

<urn:sempkm:model:ppv>
    a sempkm:MentalModel , prof:Profile ;
    dcterms:title "Pillars, Pipelines & Vaults" ;
    dcterms:description "August Bradley's PPV productivity system with five-level goal hierarchy ..." ;
    prof:hasToken "ppv"^^xsd:token ;
    dcat:version "2.0.0" ;
    prof:isProfileOf <urn:sempkm:ontology:gist> ;
    dcterms:references <http://purl.org/dc/terms/> , <https://schema.org/> ,
                       <http://www.w3.org/2004/02/skos/core#> ;
    sempkm:namespace "urn:sempkm:model:ppv:" ;
    sempkm:installedAt "2026-09-11T10:00:00Z"^^xsd:dateTime ;
    prof:hasResource
        <urn:sempkm:model:ppv:ontology#vocabulary> ,
        <urn:sempkm:model:ppv:shapes#schema> ,
        <urn:sempkm:model:ppv:shapes#validation> ,
        <urn:sempkm:model:ppv:rules#validation> ,
        <urn:sempkm:model:ppv:rules#inference> ,
        <urn:sempkm:model:ppv:views#presentation> ,
        <urn:sempkm:model:ppv:seed#seed> ,
        <urn:sempkm:model:ppv:dashboards#presentation> ,
        <urn:sempkm:model:ppv:workflows#presentation> .

# Ontology: 12 OWL classes subclassing gist:Task and others.
<urn:sempkm:model:ppv:ontology#vocabulary> a prof:ResourceDescriptor ;
    prof:hasRole role:vocabulary ;
    dcterms:format "application/ld+json" ;
    dcterms:conformsTo <http://www.w3.org/TR/owl2-overview/> ;
    prof:hasArtifact <urn:sempkm:model:ppv:ontology> .

# Shapes: one descriptor per role, because the file drives both forms and lint.
<urn:sempkm:model:ppv:shapes#schema> a prof:ResourceDescriptor ;
    prof:hasRole role:schema ;
    dcterms:format "application/ld+json" ;
    dcterms:conformsTo <http://www.w3.org/TR/shacl/> ;
    prof:hasArtifact <urn:sempkm:model:ppv:shapes> .
<urn:sempkm:model:ppv:shapes#validation> a prof:ResourceDescriptor ;
    prof:hasRole role:validation ;
    dcterms:format "application/ld+json" ;
    dcterms:conformsTo <http://www.w3.org/TR/shacl/> ;
    prof:hasArtifact <urn:sempkm:model:ppv:shapes> .

# Rules: three sh:SPARQLConstraint shapes (validation) and three sh:SPARQLRule
# derivations (no PROF role; SemPKM extension role).
<urn:sempkm:model:ppv:rules#validation> a prof:ResourceDescriptor ;
    prof:hasRole role:validation ;
    dcterms:format "text/turtle" ;
    dcterms:conformsTo <http://www.w3.org/TR/shacl/> ;
    prof:hasArtifact <urn:sempkm:model:ppv:rules> .
<urn:sempkm:model:ppv:rules#inference> a prof:ResourceDescriptor ;
    prof:hasRole srole:inference ;
    dcterms:format "text/turtle" ;
    dcterms:conformsTo <https://www.w3.org/TR/shacl-af/> ;
    prof:hasArtifact <urn:sempkm:model:ppv:rules> .

# Views, dashboards, workflows: presentation, not specification.
<urn:sempkm:model:ppv:views#presentation> a prof:ResourceDescriptor ;
    prof:hasRole srole:presentation ;
    dcterms:format "application/ld+json" ;
    dcterms:conformsTo <urn:sempkm:vocab:ViewSpec> ;
    prof:hasArtifact <urn:sempkm:model:ppv:views> .
<urn:sempkm:model:ppv:dashboards#presentation> a prof:ResourceDescriptor ;
    prof:hasRole srole:presentation ;
    dcterms:format "application/json" ;
    prof:hasArtifact <urn:sempkm:model:ppv:archive/dashboards/ppv.json> .
<urn:sempkm:model:ppv:workflows#presentation> a prof:ResourceDescriptor ;
    prof:hasRole srole:presentation ;
    dcterms:format "application/json" ;
    prof:hasArtifact <urn:sempkm:model:ppv:archive/workflows/ppv.json> .

# Seed: 35 live instances. Sub-role of role:example so PROF-only readers still
# classify it, while the narrower term records that it is installed data.
<urn:sempkm:model:ppv:seed#seed> a prof:ResourceDescriptor ;
    prof:hasRole srole:seed ;
    dcterms:format "application/ld+json" ;
    prof:hasArtifact <urn:sempkm:model:ppv:seed> .

# SemPKM role extensions (prof:ResourceRole is a skos:Concept subclass and is
# explicitly open for extension).
srole:inference a prof:ResourceRole ;
    skos:prefLabel "Inference rules" ;
    skos:definition "SHACL-AF rules that derive triples when the profile's data is loaded." .
srole:presentation a prof:ResourceRole ;
    skos:prefLabel "Presentation" ;
    skos:definition "View, dashboard, or workflow definitions that render the profile's data in SemPKM." .
srole:seed a prof:ResourceRole ;
    skos:broader role:example ;
    skos:prefLabel "Seed data" ;
    skos:definition "Instance data installed into the live graph when the profile is installed." .
```

For the simple case, **business-planning** (v1.0.0) produces the same structure with five descriptors (`ontology#vocabulary`, `shapes#schema`, `shapes#validation`, `views#presentation`, `seed#seed`) and no rules, dashboards or workflows. Nothing in the manifest beyond the identity fields and the entrypoints contributes; `icons` (34 entries) and the absence of `entailment_defaults` are invisible to PROF, which is the point of §8.

---

## 14. Sources

Reached during this research (the W3C site itself was not reachable from the research environment, so spec text was taken from the working group's GitHub mirror and its FPWD snapshot):

- W3C news, [First Public Working Draft: The Profiles Vocabulary](https://www.w3.org/news/2026/first-public-working-draft-the-profiles-vocabulary/) (2026-08-20); specification at [w3.org/TR/dx-prof-1.0](https://www.w3.org/TR/dx-prof-1.0/)
- [w3c/dx-prof](https://github.com/w3c/dx-prof) repository: `prof/index.html` (editors' draft), `prof/rdf/prof.ttl` (`owl:versionInfo "1.0"`, modified 2026-06-24), `prof/roles/resource_roles.ttl`, `publication-snapshots/2026/FPWD/Overview.html`, `prof-impl-rpt/index.html`
- Open DXWG issues consulted: [#6](https://github.com/w3c/dx-prof/issues/6) (rename ResourceDescriptor), [#63](https://github.com/w3c/dx-prof/issues/63) (`hasArtifact` guidance), [#81](https://github.com/w3c/dx-prof/issues/81) (profileOf vs. extends vs. partOf), [#85](https://github.com/w3c/dx-prof/issues/85) (schema vs. validation vs. constraints)
- [Content Negotiation by Profile](https://www.w3.org/TR/dx-prof-conneg/), Working Draft 2026-07-03, via [w3c/dx-connegp](https://github.com/w3c/dx-connegp)
- [Dataset Exchange Working Group Charter, April 2026](https://www.w3.org/2026/04/dx-wg-charter.html)
- [SHACL 1.2 Profiling](https://www.w3.org/TR/shacl12-profiling/) (referenced, not read; blocked)
- SemPKM: `backend/app/models/{manifest,loader,validator,registry,tbox_loader}.py`, `backend/app/services/marketplace.py`, `backend/app/apps/manifest.py`, `backend/app/api/router.py`, `models/{ppv,business-planning,basic-pkm}/`, `.gsd/DECISIONS.md` (D139, D150, D151)
