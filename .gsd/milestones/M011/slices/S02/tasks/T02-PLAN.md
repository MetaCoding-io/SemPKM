---
estimated_steps: 7
estimated_files: 2
---

# T02: Author CRM shapes and views

**Slice:** S02 — Personal CRM Model
**Milestone:** M011

## Description

Create SHACL shapes (form-driving constraints with PropertyGroups, enums, helptext) and ViewSpecs + SavedQueries (table/card/graph browsing). These are the two largest files in the model archive. Both depend on ontology classes from T01.

Follow `models/basic-pkm/shapes/basic-pkm.jsonld` and `models/basic-pkm/views/basic-pkm.jsonld` as structural templates. **Critical:** shapes use `"sempkm": "urn:sempkm:"` while views use `"sempkm": "urn:sempkm:vocab:"` — different namespaces.

## Steps

1. **Read reference files** for exact structural patterns:
   - `models/basic-pkm/shapes/basic-pkm.jsonld` — @context with `"sempkm": "urn:sempkm:"`, NodeShape structure, PropertyGroup structure, `sh:in` with `@list`, `sempkm:editHelpText` placement on both NodeShape and PropertyShape
   - `models/basic-pkm/views/basic-pkm.jsonld` — @context with `"sempkm": "urn:sempkm:vocab:"`, ViewSpec structure (`sempkm:targetClass`, `sempkm:renderer`, `sempkm:sparqlSelect`, `sempkm:columnOrder`), SavedQuery structure

2. **Create `models/crm/shapes/crm.jsonld`** with:
   - `@context` with `"sempkm": "urn:sempkm:"`, plus `sh`, `rdfs`, `rdf`, `xsd`, `crm`, `bpkm`, `dcterms`, `schema`, `gist`, `skos`
   - **4 NodeShapes** — each with `sh:targetClass`, `sempkm:editHelpText`, PropertyGroups:
   
   **ContactShape** (`crm:ContactShape`, target: `crm:Contact`):
   - PropertyGroup "Basic Info": firstName, lastName, email, phone
   - PropertyGroup "Professional": role, worksAt (object property → crm:Company), relationship (sh:in enum)
   - PropertyGroup "Social": knows (object property → crm:Contact)
   - PropertyGroup "Follow-up": followUpDate (xsd:date), followUpDone (xsd:boolean)
   - PropertyGroup "Tags": bpkm:tags
   - PropertyGroup "Notes": notes (xsd:string, sh:datatype xsd:string)
   
   **CompanyShape** (`crm:CompanyShape`, target: `crm:Company`):
   - PropertyGroup "Basic Info": dcterms:title (company name), industry, website
   - PropertyGroup "Details": size (sh:in enum: solo/small/medium/large/enterprise)
   - PropertyGroup "People": hasEmployee (object property → crm:Contact)
   - PropertyGroup "Notes": notes
   
   **InteractionShape** (`crm:InteractionShape`, target: `crm:Interaction`):
   - PropertyGroup "Details": interactionType (sh:in enum), interactionDate (xsd:date), summary
   - PropertyGroup "People": withContact (object property → crm:Contact)
   - PropertyGroup "Follow-up": followUpDate, followUpDone
   
   **DealShape** (`crm:DealShape`, target: `crm:Deal`):
   - PropertyGroup "Basic Info": dealName, dealStage (sh:in enum: lead/qualified/proposal/negotiation/won/lost), dealValue (xsd:decimal), currency (sh:in enum: USD/EUR/GBP)
   - PropertyGroup "Parties": dealContact (→ crm:Contact), dealCompany (→ crm:Company)
   - PropertyGroup "Notes": notes

   - All `sh:in` use `{"@list": ["value1", "value2", ...]}` format
   - PropertyGroups use `sh:order` for display ordering
   - Each shape has `sempkm:editHelpText` with a brief description

3. **Validate shapes** via rdflib:
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph, URIRef
   g = Graph().parse('../models/crm/shapes/crm.jsonld', format='json-ld')
   SH = 'http://www.w3.org/ns/shacl#'
   targets = list(g.objects(predicate=URIRef(SH + 'targetClass')))
   print(f'Shapes: {len(g)} triples, {len(targets)} targetClass declarations')
   assert len(targets) >= 4, f'Expected 4 targetClass, got {len(targets)}'
   "
   ```

4. **Create `models/crm/views/crm.jsonld`** with:
   - `@context` with `"sempkm": "urn:sempkm:vocab:"` (DIFFERENT from shapes namespace)
   - Plus `crm`, `rdfs`, `rdf`, `xsd`, `dcterms`
   
   **~10 ViewSpecs:**
   - Contact Table View — SELECT with firstName, lastName, email, role, company label
   - Contact Cards View — card renderer with name, email, role
   - Contact Graph View — CONSTRUCT with worksAt, knows edges
   - Company Table View — SELECT with name, industry, size, website
   - Company Graph View — CONSTRUCT with hasEmployee edges
   - Interaction Table View — SELECT with type, date, contact label, summary
   - Interaction Graph View — CONSTRUCT with withContact edges
   - Deal Table View — SELECT with name, stage, value, contact, company
   - Deal Cards View — card renderer grouped by stage (pipeline view)
   - CRM Network Graph — CONSTRUCT across all types showing full relationship structure
   
   All SPARQL queries use full IRIs: `<urn:sempkm:model:crm:Contact>` not `crm:Contact`
   
   **4 SavedQueries:**
   - "Stale Contacts" — contacts with no recent interaction (SELECT)
   - "Upcoming Follow-ups" — followUpDate in future, not done (SELECT)
   - "Open Deals" — dealStage not in (won, lost) (SELECT)
   - "Network Map" — full CRM graph (CONSTRUCT)

5. **Validate views** via rdflib:
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph
   g = Graph().parse('../models/crm/views/crm.jsonld', format='json-ld')
   print(f'Views: {len(g)} triples')
   # Check for ViewSpec and SavedQuery subjects
   subjects = set(str(s) for s in g.subjects())
   vs = [s for s in subjects if 'ViewSpec' in s or 'view' in s.lower()]
   qs = [s for s in subjects if 'query' in s.lower() or 'Query' in s]
   print(f'ViewSpec-related subjects: {len(vs)}')
   print(f'Query-related subjects: {len(qs)}')
   "
   ```

6. **Cross-check shapes reference ontology classes:**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   from rdflib import Graph, URIRef
   ont = Graph().parse('../models/crm/ontology/crm.jsonld', format='json-ld')
   shapes = Graph().parse('../models/crm/shapes/crm.jsonld', format='json-ld')
   SH = 'http://www.w3.org/ns/shacl#'
   targets = set(str(o) for o in shapes.objects(predicate=URIRef(SH + 'targetClass')))
   OWL = 'http://www.w3.org/2002/07/owl#'
   classes = set(str(s) for s in ont.subjects(URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), URIRef(OWL + 'Class')))
   for t in targets:
       status = 'OK' if t in classes else 'MISSING'
       print(f'  {t}: {status}')
   "
   ```

7. **Verify namespace difference between shapes and views:**
   ```bash
   cd /home/james/Code/SemPKM/backend && .venv/bin/python3 -c "
   import json
   with open('../models/crm/shapes/crm.jsonld') as f:
       sc = json.load(f)['@context']
   with open('../models/crm/views/crm.jsonld') as f:
       vc = json.load(f)['@context']
   print(f'Shapes sempkm: {sc.get(\"sempkm\", \"NOT FOUND\")}')
   print(f'Views sempkm:  {vc.get(\"sempkm\", \"NOT FOUND\")}')
   assert sc.get('sempkm') == 'urn:sempkm:', 'Shapes must use urn:sempkm:'
   assert vc.get('sempkm') == 'urn:sempkm:vocab:', 'Views must use urn:sempkm:vocab:'
   print('Namespace difference verified OK')
   "
   ```

## Must-Haves

- [ ] `models/crm/shapes/crm.jsonld` has 4 NodeShapes with `sh:targetClass` for all 4 CRM types
- [ ] PropertyGroups organize fields logically with `sh:order` for display ordering
- [ ] All `sh:in` enums use `{"@list": [...]}` format (not bare arrays)
- [ ] `sempkm:editHelpText` present on NodeShapes
- [ ] Shapes `@context` uses `"sempkm": "urn:sempkm:"`
- [ ] `models/crm/views/crm.jsonld` has ~10 ViewSpecs covering all 4 types
- [ ] 4 SavedQueries defined (Stale Contacts, Upcoming Follow-ups, Open Deals, Network Map)
- [ ] Views `@context` uses `"sempkm": "urn:sempkm:vocab:"` (different from shapes)
- [ ] SPARQL queries in views use full IRIs (not prefixed names)
- [ ] Both files parse cleanly with rdflib

## Verification

- Shapes file: 4 `sh:targetClass` declarations confirmed via rdflib query
- Views file: parses with rdflib, contains ViewSpec and SavedQuery subjects
- Namespace difference between shapes (`urn:sempkm:`) and views (`urn:sempkm:vocab:`) verified
- Shapes targetClass values match ontology OWL classes

## Inputs

- `models/crm/ontology/crm.jsonld` — OWL classes to reference via sh:targetClass (from T01)
- `models/basic-pkm/shapes/basic-pkm.jsonld` — structural template for shapes
- `models/basic-pkm/views/basic-pkm.jsonld` — structural template for views
- S02 Research doc — enum values, PropertyGroup layout, ViewSpec list, SavedQuery specs

## Observability Impact

- **Shapes triple count:** `Graph().parse('models/crm/shapes/crm.jsonld', format='json-ld')` — triple count should be >100; count <50 signals missing PropertyGroups or shapes.
- **Shapes targetClass audit:** Query `sh:targetClass` triples — must return exactly 4 (Contact, Company, Interaction, Deal). Fewer means missing NodeShapes.
- **Views triple count:** `Graph().parse('models/crm/views/crm.jsonld', format='json-ld')` — triple count should be >80; count <30 signals missing ViewSpecs.
- **Namespace compliance:** Shapes file `@context.sempkm` must be `urn:sempkm:` and views file `@context.sempkm` must be `urn:sempkm:vocab:`. Mismatch causes silent form-rendering or view-loading failures at runtime.
- **Cross-file consistency:** All `sh:targetClass` values in shapes must resolve to OWL classes in the ontology. Missing classes cause SHACL validation to silently skip the shape.

## Expected Output

- `models/crm/shapes/crm.jsonld` — SHACL shapes with 4 NodeShapes, PropertyGroups, enums, helptext
- `models/crm/views/crm.jsonld` — ~10 ViewSpecs + 4 SavedQueries for CRM browsing
