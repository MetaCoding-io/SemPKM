---
estimated_steps: 20
estimated_files: 1
skills_used: []
---

# T01: Add GuidingPrinciples, PillarScore instances and enriched review fields to PPV seed data

The PPV seed file (ppv.jsonld) currently has 31 instances across 10 types but no GuidingPrinciples, no PillarScore, and no enriched review reflection fields. This task adds realistic seed data for the new S02 types so dashboards render with actual data.

## Steps

1. Read `models/ppv/seed/ppv.jsonld` to understand the existing JSON-LD structure and @context prefixes.
2. Add 1 GuidingPrinciples instance (`ppv:seed-guiding-principles`) with all 7 fields from the SHACL shape: `dcterms:title`, `ppv:values`, `ppv:purpose`, `ppv:meaning`, `ppv:manifestation`, `ppv:foundationalStatement`, `ppv:guidingWord`. All are `xsd:string` type. Use realistic August Bradley-style content.
3. Add 3 PillarScore instances linked to the existing weekly review (`ppv:seed-review-week-mar3`) and the 3 existing pillars (`ppv:seed-pillar-health`, `ppv:seed-pillar-career`, `ppv:seed-pillar-relationships`). Each PillarScore needs: `dcterms:title` (string), `ppv:score` (xsd:integer, 1-10), `ppv:wentWell` (string), `ppv:needsAttention` (string), `ppv:weeklyReview` (→ weekly review IRI), `ppv:pillar` (→ pillar IRI), `dcterms:created` (xsd:dateTime).
4. Add enriched reflection fields to 4 existing review instances:
   - WeeklyReview (`ppv:seed-review-week-mar3`): add `ppv:wins`, `ppv:challenges`, `ppv:supportingPriorities` (all xsd:string)
   - MonthlyReview (`ppv:seed-review-march-2026`): add `ppv:biggestWins`, `ppv:biggestChallenges`, `ppv:focusAreas`, `ppv:habitsToAdjust` (all xsd:string)
   - QuarterlyReview (`ppv:seed-review-q1-2026`): add `ppv:accomplishments`, `ppv:disappointments`, `ppv:whatWorked`, `ppv:whatDidntWork`, `ppv:howToImprove`, `ppv:annualVisionNotes` (all xsd:string)
   - YearlyReview (`ppv:seed-review-yearly-2026`): add `ppv:intentionWord`, `ppv:yearTheme` (all xsd:string)
5. Verify JSON is valid and type counts are correct.

## Must-Haves

- [ ] 1 GuidingPrinciples instance with all 7 text fields populated
- [ ] 3 PillarScore instances with scores 1-10, linked to existing pillars and weekly review
- [ ] All 4 review instances have enriched reflection fields matching their SHACL shapes
- [ ] JSON-LD is valid (parseable by python json module)
- [ ] All IRI references use existing seed IDs (no dangling references)

## Verification

- `python3 -c "import json; data=json.load(open('models/ppv/seed/ppv.jsonld')); types={}; [types.__setitem__(i.get('@type','?'), types.get(i.get('@type','?'),0)+1) for i in data['@graph']]; print(types); assert types.get('ppv:GuidingPrinciples')==1; assert types.get('ppv:PillarScore')==3; print('OK')"` exits 0
- `python3 -c "import json; data=json.load(open('models/ppv/seed/ppv.jsonld')); weekly=[i for i in data['@graph'] if i['@type']=='ppv:WeeklyReview'][0]; assert 'ppv:wins' in weekly; print('Enriched fields OK')"` exits 0

## Inputs

- ``models/ppv/seed/ppv.jsonld` — existing seed data with 31 instances across 10 types`
- ``models/ppv/shapes/ppv.jsonld` — SHACL shapes defining required fields for PillarScore, GuidingPrinciples, and enriched review properties`

## Expected Output

- ``models/ppv/seed/ppv.jsonld` — updated with 1 GuidingPrinciples + 3 PillarScore instances + enriched review fields on all 4 review instances (35 total instances, 12 types)`

## Verification

python3 -c "import json; data=json.load(open('models/ppv/seed/ppv.jsonld')); types={}; [types.__setitem__(i.get('@type','?'), types.get(i.get('@type','?'),0)+1) for i in data['@graph']]; assert types.get('ppv:GuidingPrinciples')==1; assert types.get('ppv:PillarScore')==3; print('Seed data OK')"
