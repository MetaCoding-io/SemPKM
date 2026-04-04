---
estimated_steps: 52
estimated_files: 3
skills_used: []
---

# T01: Add PillarScore + GuidingPrinciples to ontology/shapes and extend review shapes with reflection fields

Add two new OWL classes (PillarScore, GuidingPrinciples) with all their properties to the PPV ontology, create their SHACL NodeShapes with property groups, extend all four review shapes (Weekly, Monthly, Quarterly, Yearly) with new reflection properties, and add manifest icon entries.

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

## Inputs

- ``models/ppv/ontology/ppv.jsonld` — existing PPV ontology (406 lines) with 11 classes and ~30 properties`
- ``models/ppv/shapes/ppv.jsonld` — existing PPV shapes (1059 lines) with 11 NodeShapes`
- ``models/ppv/manifest.yaml` — existing manifest (163 lines) with 10 icon entries`

## Expected Output

- ``models/ppv/ontology/ppv.jsonld` — expanded with 2 new classes (PillarScore, GuidingPrinciples), ~20 new properties`
- ``models/ppv/shapes/ppv.jsonld` — expanded with 2 new NodeShapes, 6 new PropertyGroups, ~30 new sh:property entries across 6 shapes`
- ``models/ppv/manifest.yaml` — expanded with 2 new icon entries (PillarScore, GuidingPrinciples)`

## Verification

python3 -c "import json; [json.load(open(f)) for f in ['models/ppv/ontology/ppv.jsonld','models/ppv/shapes/ppv.jsonld']]; print('JSON valid')" && python3 -c "import yaml; yaml.safe_load(open('models/ppv/manifest.yaml')); print('YAML valid')" && python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/ppv/ontology/ppv.jsonld', format='json-ld'); assert (None, None, None) in g; classes=[str(s) for s,_,_ in g.triples((None, None, None)) if 'PillarScore' in str(s) or 'GuidingPrinciples' in str(s)]; assert len(classes) > 0, 'New classes not found'; print(f'Ontology OK: {len(g)} triples, new classes found')"
