# S02: PPV Ontology Expansion — PillarScore, GuidingPrinciples & Enriched Reviews

**Goal:** PPV ontology expanded with PillarScore and GuidingPrinciples classes, enriched review reflection fields on all 4 review types, 4 new ViewSpecs, a SHACL-AF denormalization rule, and manifest icon entries — all parseable and cross-reference-valid.
**Demo:** After this: After PPV install, create a PillarScore via SHACL form (linked to a pillar and weekly review, score 1-10). Create a GuidingPrinciples singleton. New enriched review fields (wins, challenges, supportingPriorities) appear on weekly/monthly/quarterly/yearly review forms.

## Tasks
- [x] **T01: Added PillarScore + GuidingPrinciples classes, 22 new ontology properties, 2 SHACL NodeShapes, 15 enriched review reflection fields, and 2 manifest icons to the PPV model** — Add two new OWL classes (PillarScore, GuidingPrinciples) with all their properties to the PPV ontology, create their SHACL NodeShapes with property groups, extend all four review shapes (Weekly, Monthly, Quarterly, Yearly) with new reflection properties, and add manifest icon entries.

## Steps

1. **Ontology — new classes** (`models/ppv/ontology/ppv.jsonld`): Add `ppv:PillarScore` and `ppv:GuidingPrinciples` as `owl:Class` entries in the `@graph` array. PillarScore: label 'Pillar Score', comment about weekly pillar scoring mechanic. GuidingPrinciples: label 'Guiding Principles', comment about values anchor document.

2. **Ontology — PillarScore properties**: Add these `owl:DatatypeProperty` entries: `ppv:score` (domain PillarScore, range xsd:integer), `ppv:wentWell` (domain PillarScore, range xsd:string), `ppv:needsAttention` (domain PillarScore, range xsd:string). Add `ppv:weeklyReview` as `owl:ObjectProperty` (domain PillarScore, range WeeklyReview). Note: `ppv:pillar` already exists with range ppv:Pillar and no domain restriction — PillarScore can reuse it.

3. **Ontology — GuidingPrinciples properties**: Add these `owl:DatatypeProperty` entries, all with domain GuidingPrinciples and range xsd:string: `ppv:values`, `ppv:purpose`, `ppv:meaning`, `ppv:manifestation`, `ppv:foundationalStatement`, `ppv:guidingWord`.

4. **Ontology — enriched review properties**: Add these `owl:DatatypeProperty` entries, all range xsd:string:
   - WeeklyReview domain: `ppv:wins`, `ppv:challenges`, `ppv:supportingPriorities`
   - MonthlyReview domain: `ppv:biggestWins`, `ppv:biggestChallenges`, `ppv:focusAreas`, `ppv:habitsToAdjust`
   - QuarterlyReview domain: `ppv:accomplishments`, `ppv:disappointments`, `ppv:whatWorked`, `ppv:whatDidntWork`, `ppv:howToImprove`, `ppv:annualVisionNotes`
   - YearlyReview domain: `ppv:intentionWord`, `ppv:yearTheme`

5. **Shapes — PillarScoreShape** (`models/ppv/shapes/ppv.jsonld`): Add 3 PropertyGroups (`ppv:PillarScoreBasicGroup` order 1, `ppv:PillarScoreRelationshipsGroup` order 2, `ppv:PillarScoreMetadataGroup` order 3) and a NodeShape targeting ppv:PillarScore. Properties:
   - dcterms:title (string, required, maxCount 1, order 1, BasicGroup)
   - ppv:score (integer, required, maxCount 1, order 2, BasicGroup, sh:minInclusive 1, sh:maxInclusive 10)
   - ppv:wentWell (string, optional, maxCount 1, order 3, BasicGroup)
   - ppv:needsAttention (string, optional, maxCount 1, order 4, BasicGroup)
   - ppv:weeklyReview (class WeeklyReview, required, maxCount 1, order 5, RelationshipsGroup)
   - ppv:pillar (class Pillar, required, maxCount 1, order 6, RelationshipsGroup)
   - dcterms:created (dateTime, optional, maxCount 1, order 7, MetadataGroup)
   Add editHelpText on the NodeShape and key properties.

6. **Shapes — GuidingPrinciplesShape**: Add 3 PropertyGroups (`ppv:GuidingPrinciplesBasicGroup` order 1, `ppv:GuidingPrinciplesStatementGroup` order 2, `ppv:GuidingPrinciplesMetadataGroup` order 3) and a NodeShape targeting ppv:GuidingPrinciples. Properties:
   - dcterms:title (string, required, maxCount 1, order 1, BasicGroup)
   - ppv:values (string, optional, maxCount 1, order 2, BasicGroup)
   - ppv:purpose (string, optional, maxCount 1, order 3, BasicGroup)
   - ppv:meaning (string, optional, maxCount 1, order 4, BasicGroup)
   - ppv:manifestation (string, optional, maxCount 1, order 5, BasicGroup)
   - ppv:foundationalStatement (string, optional, maxCount 1, order 6, StatementGroup)
   - ppv:guidingWord (string, optional, maxCount 1, order 7, StatementGroup)
   - dcterms:created (dateTime, optional, maxCount 1, order 8, MetadataGroup)

7. **Shapes — extend WeeklyReviewShape**: Add a new PropertyGroup `ppv:WeeklyReviewReflectionGroup` (label 'Reflection', sh:order 5 — after current MetadataGroup at order 4). Add 3 sh:property entries to WeeklyReviewShape's sh:property array:
   - ppv:wins (string, optional, maxCount 1, order 8, ReflectionGroup, helpText 'What went well this week?')
   - ppv:challenges (string, optional, maxCount 1, order 9, ReflectionGroup, helpText 'What were the biggest challenges?')
   - ppv:supportingPriorities (string, optional, maxCount 1, order 10, ReflectionGroup, helpText 'Which priorities are you supporting next week?')

8. **Shapes — extend MonthlyReviewShape**: Add 4 new sh:property entries to MonthlyReviewShape's existing sh:property array, using the existing `ppv:MonthlyReviewReflectionGroup`:
   - ppv:biggestWins (string, optional, maxCount 1, order 7, ReflectionGroup)
   - ppv:biggestChallenges (string, optional, maxCount 1, order 8, ReflectionGroup)
   - ppv:focusAreas (string, optional, maxCount 1, order 9, ReflectionGroup)
   - ppv:habitsToAdjust (string, optional, maxCount 1, order 10, ReflectionGroup)
   Note: existing gratitude is order 5 and learnedThisMonth is order 6 in the ReflectionGroup. New properties start at order 7.

9. **Shapes — extend QuarterlyReviewShape**: Add a new PropertyGroup `ppv:QuarterlyReviewReflectionGroup` (label 'Reflection', sh:order 4 — after MetadataGroup at order 3). Add 6 sh:property entries to QuarterlyReviewShape:
   - ppv:accomplishments, ppv:disappointments, ppv:whatWorked, ppv:whatDidntWork, ppv:howToImprove, ppv:annualVisionNotes (all string, optional, maxCount 1, ReflectionGroup, orders 7-12)

10. **Shapes — extend YearlyReviewShape**: Add a new PropertyGroup `ppv:YearlyReviewReflectionGroup` (label 'Reflection', sh:order 4 — after MetadataGroup at order 3). Add 2 sh:property entries to YearlyReviewShape:
    - ppv:intentionWord (string, optional, maxCount 1, order 6, ReflectionGroup)
    - ppv:yearTheme (string, optional, maxCount 1, order 7, ReflectionGroup)

11. **Manifest icons** (`models/ppv/manifest.yaml`): Add 2 new icon entries at the end of the icons list following exact existing pattern (type/icon/color + tree/tab/graph sub-entries):
    - ppv:PillarScore: icon 'bar-chart-2', color '#f59e0b'
    - ppv:GuidingPrinciples: icon 'heart-handshake', color '#8b5cf6'

## Key constraints
- Follow exact JSON-LD patterns in existing ontology/shapes files (indentation, @id/@type format, property ordering)
- All new properties in shapes MUST reference properties defined in the ontology
- The `ppv:pillar` ObjectProperty already exists (no domain restriction, range ppv:Pillar) — reuse it for PillarScore, don't create a duplicate
- sh:order values within a shape must not collide
- Manifest icon entries must use exact YAML structure matching existing entries
  - Estimate: 45m
  - Files: models/ppv/ontology/ppv.jsonld, models/ppv/shapes/ppv.jsonld, models/ppv/manifest.yaml
  - Verify: python3 -c "import json; [json.load(open(f)) for f in ['models/ppv/ontology/ppv.jsonld','models/ppv/shapes/ppv.jsonld']]; print('JSON valid')" && python3 -c "import yaml; yaml.safe_load(open('models/ppv/manifest.yaml')); print('YAML valid')" && python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/ppv/ontology/ppv.jsonld', format='json-ld'); assert (None, None, None) in g; classes=[str(s) for s,_,_ in g.triples((None, None, None)) if 'PillarScore' in str(s) or 'GuidingPrinciples' in str(s)]; assert len(classes) > 0, 'New classes not found'; print(f'Ontology OK: {len(g)} triples, new classes found')"
- [x] **T02: Added 4 new ViewSpecs, PillarScoreDateDenormRule with schema prefix, and 99-test validation suite for all PPV ontology expansion artifacts** — Add 4 new ViewSpecs to the PPV views file, add a PillarScore date denormalization rule to the rules file (with schema prefix), and write a comprehensive unit test that validates all new model artifacts parse correctly and cross-reference each other.

## Steps

1. **ViewSpecs** (`models/ppv/views/ppv.jsonld`): Add 4 new entries to the `@graph` array following the exact JSON-LD format of existing ViewSpecs. Each needs @id, @type sempkm:ViewSpec, rdfs:label, sempkm:targetClass, sempkm:rendererType, sempkm:sparqlQuery, and for tables: sempkm:columns and sempkm:sortDefault.

   **ppv:view-pillarscore-table** — PillarScore table:
   - label: 'Pillar Scores'
   - target: ppv:PillarScore
   - renderer: table
   - SPARQL: `SELECT ?s ?title ?score ?pillarTitle ?weekTitle ?wentWell ?needsAttention WHERE { ?s a <urn:sempkm:model:ppv:PillarScore> ; <http://purl.org/dc/terms/title> ?title . OPTIONAL { ?s <urn:sempkm:model:ppv:score> ?score } . OPTIONAL { ?s <urn:sempkm:model:ppv:pillar> ?p . ?p <http://purl.org/dc/terms/title> ?pillarTitle } . OPTIONAL { ?s <urn:sempkm:model:ppv:weeklyReview> ?wr . ?wr <http://purl.org/dc/terms/title> ?weekTitle } . OPTIONAL { ?s <urn:sempkm:model:ppv:wentWell> ?wentWell } . OPTIONAL { ?s <urn:sempkm:model:ppv:needsAttention> ?needsAttention } } ORDER BY ?pillarTitle`
   - columns: title,score,pillarTitle,weekTitle,wentWell,needsAttention
   - sortDefault: pillarTitle

   **ppv:view-action-kanban** — ActionItem kanban by status:
   - label: 'Action Kanban'
   - target: ppv:ActionItem
   - renderer: kanban
   - SPARQL: `SELECT ?s ?title ?status ?priority ?doDate ?context WHERE { ?s a <urn:sempkm:model:ppv:ActionItem> ; <http://purl.org/dc/terms/title> ?title . OPTIONAL { ?s <urn:sempkm:model:ppv:status> ?status } . OPTIONAL { ?s <urn:sempkm:model:ppv:priority> ?priority } . OPTIONAL { ?s <urn:sempkm:model:ppv:doDate> ?doDate } . OPTIONAL { ?s <urn:sempkm:model:ppv:context> ?context } }`
   Note: kanban renderer auto-detects status field via SHACL sh:in — no columns/sortDefault needed.

   **ppv:view-project-kanban** — Project kanban by status:
   - label: 'Project Kanban'
   - target: ppv:Project
   - renderer: kanban
   - SPARQL: `SELECT ?s ?title ?status ?priority ?progress WHERE { ?s a <urn:sempkm:model:ppv:Project> ; <http://purl.org/dc/terms/title> ?title . OPTIONAL { ?s <urn:sempkm:model:ppv:status> ?status } . OPTIONAL { ?s <urn:sempkm:model:ppv:priority> ?priority } . OPTIONAL { ?s <urn:sempkm:model:ppv:progress> ?progress } }`

   **ppv:view-action-by-context** — ActionItem table by context:
   - label: 'Actions by Context'
   - target: ppv:ActionItem
   - renderer: table
   - SPARQL: `SELECT ?s ?title ?status ?priority ?doDate ?context ?energy WHERE { ?s a <urn:sempkm:model:ppv:ActionItem> ; <http://purl.org/dc/terms/title> ?title . OPTIONAL { ?s <urn:sempkm:model:ppv:status> ?status } . OPTIONAL { ?s <urn:sempkm:model:ppv:priority> ?priority } . OPTIONAL { ?s <urn:sempkm:model:ppv:doDate> ?doDate } . OPTIONAL { ?s <urn:sempkm:model:ppv:context> ?context } . OPTIONAL { ?s <urn:sempkm:model:ppv:energy> ?energy } } ORDER BY ?context`
   - columns: title,status,priority,doDate,context,energy
   - sortDefault: context

2. **Rules** (`models/ppv/rules/ppv.ttl`): Add `schema` prefix declaration at the top: `@prefix schema: <https://schema.org/> .` Add `schema` to `ppv:PrefixDeclarations` (new sh:declare block with prefix 'schema', namespace 'https://schema.org/'). Then add the PillarScoreDateDenormRule:
   ```turtle
   ppv:PillarScoreDateDenormRule
       a sh:NodeShape ;
       sh:targetClass ppv:PillarScore ;
       sh:rule [
           a sh:SPARQLRule ;
           sh:order 2 ;
           rdfs:label "Derive pillar score date from weekly review" ;
           sh:prefixes ppv:PrefixDeclarations ;
           sh:construct """
               CONSTRUCT { $this schema:startDate ?startDate . }
               WHERE {
                   $this ppv:weeklyReview ?wr .
                   ?wr schema:startDate ?startDate .
                   FILTER NOT EXISTS { $this schema:startDate ?existing }
               }
           """ ;
       ] .
   ```

3. **Validation test** (`backend/tests/test_ppv_ontology.py`): Write a comprehensive test file that:
   - Loads ontology JSON-LD and verifies PillarScore and GuidingPrinciples classes exist as owl:Class
   - Verifies all new properties exist (ppv:score, ppv:weeklyReview, ppv:values, ppv:purpose, ppv:meaning, ppv:manifestation, ppv:foundationalStatement, ppv:guidingWord, ppv:wentWell, ppv:needsAttention, ppv:wins, ppv:challenges, ppv:supportingPriorities, ppv:biggestWins, ppv:biggestChallenges, ppv:focusAreas, ppv:habitsToAdjust, ppv:accomplishments, ppv:disappointments, ppv:whatWorked, ppv:whatDidntWork, ppv:howToImprove, ppv:annualVisionNotes, ppv:intentionWord, ppv:yearTheme)
   - Loads shapes JSON-LD and verifies PillarScoreShape and GuidingPrinciplesShape NodeShapes exist with correct sh:targetClass
   - Verifies PillarScoreShape has sh:minInclusive 1 and sh:maxInclusive 10 on the score property
   - Verifies new reflection PropertyGroups exist (WeeklyReviewReflectionGroup, QuarterlyReviewReflectionGroup, YearlyReviewReflectionGroup)
   - Loads views JSON-LD and verifies 4 new ViewSpec IRIs exist
   - Loads rules Turtle and verifies PillarScoreDateDenormRule exists
   - Loads all files into a combined graph to verify parse success
   - Verifies manifest YAML parses and contains new icon entries
   - Uses pytest parametrize for property existence checks

## Key constraints
- ViewSpec SPARQL queries must use full IRI expansion (not prefixed) matching existing ViewSpec patterns
- Rules file prefix declarations must include the schema prefix in ppv:PrefixDeclarations for the SPARQL rule to work
- Test file should use `pathlib.Path(__file__).resolve().parent.parent.parent / 'models' / 'ppv'` to locate model files (standard pattern in existing tests)
  - Estimate: 40m
  - Files: models/ppv/views/ppv.jsonld, models/ppv/rules/ppv.ttl, backend/tests/test_ppv_ontology.py
  - Verify: cd backend && python3 -c "from rdflib import Graph; g=Graph(); g.parse('../models/ppv/rules/ppv.ttl', format='turtle'); print(f'Rules OK: {len(g)} triples')" && .venv/bin/python -m pytest tests/test_ppv_ontology.py -v
