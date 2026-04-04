---
estimated_steps: 63
estimated_files: 3
skills_used: []
---

# T02: Add ViewSpecs, SHACL-AF denorm rule, and write validation test

Add 4 new ViewSpecs to the PPV views file, add a PillarScore date denormalization rule to the rules file (with schema prefix), and write a comprehensive unit test that validates all new model artifacts parse correctly and cross-reference each other.

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

## Inputs

- ``models/ppv/ontology/ppv.jsonld` — expanded ontology from T01 with new classes and properties`
- ``models/ppv/shapes/ppv.jsonld` — expanded shapes from T01 with new NodeShapes and PropertyGroups`
- ``models/ppv/views/ppv.jsonld` — existing views file (207 lines) with 17 ViewSpecs`
- ``models/ppv/rules/ppv.ttl` — existing rules file (137 lines) with 2 denorm rules and 3 validation rules`
- ``models/ppv/manifest.yaml` — expanded manifest from T01 with new icon entries`

## Expected Output

- ``models/ppv/views/ppv.jsonld` — expanded with 4 new ViewSpecs (pillarscore table, action kanban, project kanban, action-by-context table)`
- ``models/ppv/rules/ppv.ttl` — expanded with schema prefix, PillarScoreDateDenormRule, and schema prefix in PrefixDeclarations`
- ``backend/tests/test_ppv_ontology.py` — comprehensive validation test covering all new ontology, shapes, views, rules, and manifest artifacts`

## Verification

cd backend && python3 -c "from rdflib import Graph; g=Graph(); g.parse('../models/ppv/rules/ppv.ttl', format='turtle'); print(f'Rules OK: {len(g)} triples')" && .venv/bin/python -m pytest tests/test_ppv_ontology.py -v
