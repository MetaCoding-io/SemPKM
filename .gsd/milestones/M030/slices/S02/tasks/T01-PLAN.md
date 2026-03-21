---
estimated_steps: 9
estimated_files: 4
---

# T01: Write 9 SHACL-AF validation rules across 4 model rules files

**Slice:** S02 — Data Quality Rules (9 new SHACL-AF rules)
**Milestone:** M030

## Description

Add 9 new SHACL-AF SPARQLConstraint validation rules to existing Mental Model rules files. Each rule is a separate NodeShape (per D153) with `sh:severity` and `sh:sparql` containing a `sh:SPARQLConstraint`. The rules follow the identical pattern proven by the 11 existing rules across 4 models.

Cross-model rules (comma-in-tags, titleless objects, orphan objects, empty body for Note/Concept, concept with no definition, duplicate URL) go in `basic-pkm/rules/basic-pkm.ttl` per D278. Empty body for zettelkasten note types goes in `zettelkasten/rules/zettelkasten.ttl`. Stale project and broken chain go in `ppv/rules/ppv.ttl`. Claim with no rationale goes in `research/rules/research.ttl`.

## Steps

1. **Update `basic-pkm.ttl` PrefixDeclarations** — Add `sh:declare` entries for `rdf`, `rdfs`, `skos`, `foaf`, and `schema` (http://schema.org/) namespaces. These are needed by the cross-model rules (titleless checks dcterms:title + skos:prefLabel + foaf:name + rdfs:label; duplicate URL uses schema:url; orphan uses rdf:type).

2. **Add comma-in-tags rule to `basic-pkm.ttl`** — New NodeShape `bpkm:CommaInTagsValidationShape` with `sh:targetSubjectsOf bpkm:tags`, `sh:severity sh:Warning`. SPARQL: `SELECT $this ?tagVal WHERE { $this bpkm:tags ?tagVal . FILTER(CONTAINS(STR(?tagVal), ",")) }`. Message: "Tag value contains a comma — split into individual tags."

3. **Add empty body rule for Note/Concept to `basic-pkm.ttl`** — New NodeShape `bpkm:EmptyBodyValidationShape` with `sh:severity sh:Info`. Use `sh:targetClass` cannot target two classes on one shape in standard SHACL — use `sh:targetSubjectsOf rdf:type` with SPARQL filter for the types instead. SPARQL: `SELECT $this WHERE { { $this a bpkm:Note } UNION { $this a bpkm:Concept } FILTER NOT EXISTS { $this <urn:sempkm:vocab:body> ?body } }`. Message: "Object has no body content. Consider adding a description or notes." Use full IRI for body predicate (`<urn:sempkm:vocab:body>`) since sempkm vocab prefix is not in PrefixDeclarations.

4. **Add concept with no definition rule to `basic-pkm.ttl`** — New NodeShape `bpkm:ConceptNoDefinitionValidationShape` with `sh:targetClass bpkm:Concept`, `sh:severity sh:Info`. SPARQL: `SELECT $this WHERE { FILTER NOT EXISTS { $this <http://www.w3.org/2004/02/skos/core#definition> ?def } }`. Message: "Concept has no definition. Consider adding a skos:definition." Use full IRI for skos:definition OR use the prefix added in step 1.

5. **Add titleless objects rule to `basic-pkm.ttl`** — New NodeShape `bpkm:TitlelessObjectValidationShape` with `sh:targetSubjectsOf rdf:type`, `sh:severity sh:Warning`. SPARQL: `SELECT $this WHERE { $this a ?type . FILTER NOT EXISTS { $this dcterms:title ?t1 } FILTER NOT EXISTS { $this rdfs:label ?t2 } FILTER NOT EXISTS { $this skos:prefLabel ?t3 } FILTER NOT EXISTS { $this foaf:name ?t4 } }`. Message: "Object has no title (dcterms:title, rdfs:label, skos:prefLabel, or foaf:name)." Use prefixed names from the updated PrefixDeclarations. **Important:** CRM Contacts use `crm:firstName`/`crm:lastName`, not dcterms:title — they will trigger this rule. CRM Interactions also lack dcterms:title. This is correct behavior — these are cross-model rules. However, to avoid false positives on objects that have model-specific name properties, limit this rule's scope: add `FILTER(STRSTARTS(STR(?type), "urn:sempkm:model:basic-pkm:"))` so it only fires for basic-pkm types. Other models can add their own titleless rules later.

6. **Add orphan objects rule to `basic-pkm.ttl`** — New NodeShape `bpkm:OrphanObjectValidationShape` with `sh:targetSubjectsOf rdf:type`, `sh:severity sh:Info`. SPARQL per D282: check that no edges to/from OTHER typed resources exist. `SELECT $this WHERE { $this a ?type . FILTER NOT EXISTS { $this ?p ?other . ?other a ?anyType . FILTER(?p != rdf:type) } FILTER NOT EXISTS { ?other2 ?p2 $this . ?other2 a ?anyType2 } }`. Message: "Object has no connections to other objects. Consider linking it." **Important:** Scope to basic-pkm types with FILTER on ?type prefix to avoid firing on every typed resource in the graph. Use full IRI: `FILTER(STRSTARTS(STR(?type), "urn:sempkm:model:basic-pkm:"))`.

7. **Add duplicate URL rule to `basic-pkm.ttl`** — New NodeShape `bpkm:DuplicateUrlValidationShape` with `sh:targetSubjectsOf <http://schema.org/url>`, `sh:severity sh:Info`. SPARQL: `SELECT $this ?url WHERE { $this <http://schema.org/url> ?url . $this a ?type . ?other a ?type . ?other <http://schema.org/url> ?url . FILTER(?other != $this) }`. Message: "Another object of the same type shares this URL: {?url}." Use full IRI for schema:url since it may not be in PrefixDeclarations.

8. **Add empty body rule for zk note types to `zettelkasten.ttl`** — New NodeShape `zk:EmptyBodyValidationShape` with `sh:severity sh:Info`. SPARQL: `SELECT $this WHERE { { $this a zk:FleetingNote } UNION { $this a zk:LiteratureNote } UNION { $this a zk:PermanentNote } UNION { $this a zk:StructureNote } FILTER NOT EXISTS { $this <urn:sempkm:vocab:body> ?body } }`. Message: "Note has no body content. Consider adding your thoughts."

9. **Update `ppv.ttl` PrefixDeclarations** — Add `sh:declare` entries for `dcterms` and `xsd` namespaces.

10. **Add stale project rule to `ppv.ttl`** — New NodeShape `ppv:StaleProjectValidationShape` with `sh:targetClass ppv:Project`, `sh:severity sh:Info`. Since PPV seed Projects have NO `dcterms:modified` at all, use the simpler "no modified date" check: `SELECT $this WHERE { FILTER NOT EXISTS { $this dcterms:modified ?mod } }`. Message: "Project has no modification date recorded. Consider reviewing its status." This avoids the date arithmetic limitation (K001).

11. **Add broken chain rules to `ppv.ttl`** — Two NodeShapes:
    - `ppv:ActionItemNoProjectValidationShape` with `sh:targetClass ppv:ActionItem`, `sh:severity sh:Warning`. SPARQL: `SELECT $this WHERE { FILTER NOT EXISTS { $this ppv:project ?proj } }`. Message: "Action item is not linked to any project."
    - `ppv:ProjectNoGoalValidationShape` with `sh:targetClass ppv:Project`, `sh:severity sh:Warning`. SPARQL: `SELECT $this WHERE { FILTER NOT EXISTS { $this ppv:goalOutcome ?go } }`. Message: "Project is not linked to any goal outcome."

12. **Add claim no rationale rule to `research.ttl`** — New NodeShape `res:ClaimNoRationaleValidationShape` with `sh:targetClass res:Claim`, `sh:severity sh:Info`. SPARQL: `SELECT $this WHERE { FILTER NOT EXISTS { $this <urn:sempkm:model:research:rationale> ?rat } }`. Message: "Claim has no rationale. Consider explaining why you believe this." Use full IRI since `res:rationale` may need explicit namespace.

13. **Verify all 4 .ttl files parse cleanly** with rdflib: `python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/<model>/rules/<model>.ttl', format='turtle'); print(f'{model}: {len(g)} triples')"` for each model.

## Must-Haves

- [ ] Each new rule is on its own dedicated NodeShape (D153)
- [ ] Each NodeShape has `sh:severity` (Warning or Info as specified)
- [ ] Each SPARQLConstraint has `sh:message`, `sh:prefixes`, and `sh:select`
- [ ] PrefixDeclarations updated with all prefixes used in SPARQL strings
- [ ] All 4 rules files parse cleanly with rdflib
- [ ] Orphan objects rule scoped to basic-pkm types to avoid performance issues (D282)
- [ ] Body predicate uses full IRI `<urn:sempkm:vocab:body>` (not prefix)
- [ ] Stale project uses "no dcterms:modified" check (avoids K001 date arithmetic limitation)

## Verification

- `python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/rules/basic-pkm.ttl', format='turtle'); print(len(g))"` — parses without error
- `python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/ppv/rules/ppv.ttl', format='turtle'); print(len(g))"` — parses without error
- `python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/zettelkasten/rules/zettelkasten.ttl', format='turtle'); print(len(g))"` — parses without error
- `python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/research/rules/research.ttl', format='turtle'); print(len(g))"` — parses without error
- Count of new NodeShapes: 5 in basic-pkm, 1 in zettelkasten, 3 in ppv, 1 in research = 10 total (stale project + 2 broken chain in ppv = 3)

## Inputs

- `models/basic-pkm/rules/basic-pkm.ttl` — existing file with 2 inference rules + 1 validation rule + PrefixDeclarations
- `models/ppv/rules/ppv.ttl` — existing file with 2 inference rules + PrefixDeclarations (ppv only)
- `models/research/rules/research.ttl` — existing file with 4 validation rules + PrefixDeclarations
- `models/zettelkasten/rules/zettelkasten.ttl` — existing file with 3 validation rules + PrefixDeclarations
- Research doc specifies exact rule patterns, SPARQL queries, severity levels, and target mechanisms
- K001: rdflib doesn't support xsd:dayTimeDuration subtraction — use NOT EXISTS or STRDT+SUBSTR for dates
- D153: Each validation rule on its own NodeShape
- D278: Cross-model rules in basic-pkm
- D282: Orphan rule as SHACL-AF, monitor performance

## Observability Impact

- **Signals changed:** 10 new SHACL NodeShapes (5 basic-pkm, 1 zettelkasten, 3 ppv, 1 research) — each produces sh:Warning or sh:Info violations when data quality issues are detected during pyshacl validation.
- **How to inspect:** Parse each rules file offline with `python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/<model>/rules/<model>.ttl', format='turtle'); print(len(g))"`. At runtime, violations appear in `GET /api/objects/{id}/lint` responses.
- **Failure visibility:** Malformed SPARQL or missing PrefixDeclarations cause pyshacl `ReportableRuntimeError` at validation time — visible as 500 errors in the lint API and in `docker compose logs backend`. Parse failures at model load time are caught and logged by `model_shapes_loader()`.

## Expected Output

- `models/basic-pkm/rules/basic-pkm.ttl` — 5 new validation NodeShapes + expanded PrefixDeclarations
- `models/zettelkasten/rules/zettelkasten.ttl` — 1 new validation NodeShape
- `models/ppv/rules/ppv.ttl` — 3 new validation NodeShapes + expanded PrefixDeclarations
- `models/research/rules/research.ttl` — 1 new validation NodeShape
