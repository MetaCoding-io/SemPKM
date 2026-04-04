# S02 Research: PPV Ontology Expansion — PillarScore, GuidingPrinciples & Enriched Reviews

## Summary

This is straightforward ontology/shapes/views/rules extension work following well-established patterns in the existing PPV model files. No new technology, no architectural decisions, no library lookups needed. All four files (ontology, shapes, views, rules) use the same JSON-LD / Turtle patterns already in place — this is additive work on known structures.

## Recommendation

Divide into two tasks: (1) ontology + shapes (core schema), (2) views + rules (operational). The ontology and shapes are tightly coupled (validator enforces cross-references), while views and rules are independently testable.

## Implementation Landscape

### Files to Modify

| File | What Changes | Lines (current) |
|------|-------------|-----------------|
| `models/ppv/ontology/ppv.jsonld` | Add 2 new classes (PillarScore, GuidingPrinciples), ~20 new properties | 406 |
| `models/ppv/shapes/ppv.jsonld` | Add 2 new NodeShapes + property groups, extend 4 review shapes with new properties | 1059 |
| `models/ppv/views/ppv.jsonld` | Add 4 new ViewSpecs (pillar-score table, action kanban, project kanban, action-by-context table) | 207 |
| `models/ppv/rules/ppv.ttl` | Add 1 SHACL-AF SPARQL rule (PillarScore denorm: copy weeklyReview date to PillarScore) | 137 |
| `models/ppv/manifest.yaml` | Add 2 new icon entries (PillarScore, GuidingPrinciples) | 163 |
| `models/ppv/seed/ppv.jsonld` | No change in S02 (seed data expansion is S04 scope) |  |

### New Ontology Classes

#### PillarScore
The core mechanic of Bradley's weekly review — score each pillar 1-10 with reflection.

Properties to add to ontology `@graph`:
- `ppv:PillarScore` — owl:Class, label "Pillar Score", comment about weekly scoring mechanic
- `ppv:weeklyReview` — owl:ObjectProperty, domain PillarScore, range WeeklyReview (required link)
- `ppv:score` — owl:DatatypeProperty, domain PillarScore, range xsd:integer (1-10)
- `ppv:wentWell` — owl:DatatypeProperty, domain PillarScore, range xsd:string
- `ppv:needsAttention` — owl:DatatypeProperty, domain PillarScore, range xsd:string

Note: `ppv:pillar` already exists as a generic ObjectProperty — PillarScore can reuse it (no domain restriction on the existing property, only range is ppv:Pillar).

#### GuidingPrinciples
Bradley's values anchor — singleton document transcluded into reviews.

Properties to add:
- `ppv:GuidingPrinciples` — owl:Class, label "Guiding Principles"
- `ppv:values` — owl:DatatypeProperty, domain GuidingPrinciples, range xsd:string
- `ppv:purpose` — owl:DatatypeProperty, domain GuidingPrinciples, range xsd:string
- `ppv:meaning` — owl:DatatypeProperty, domain GuidingPrinciples, range xsd:string
- `ppv:manifestation` — owl:DatatypeProperty, domain GuidingPrinciples, range xsd:string
- `ppv:foundationalStatement` — owl:DatatypeProperty, domain GuidingPrinciples, range xsd:string
- `ppv:guidingWord` — owl:DatatypeProperty, domain GuidingPrinciples, range xsd:string

### Enriched Review Properties

New owl:DatatypeProperty entries for each review type. All are xsd:string, optional (no minCount), maxCount 1.

**WeeklyReview (3 new):** ppv:wins, ppv:challenges, ppv:supportingPriorities
**MonthlyReview (4 new):** ppv:biggestWins, ppv:biggestChallenges, ppv:focusAreas, ppv:habitsToAdjust
**QuarterlyReview (6 new):** ppv:accomplishments, ppv:disappointments, ppv:whatWorked, ppv:whatDidntWork, ppv:howToImprove, ppv:annualVisionNotes
**YearlyReview (2 new):** ppv:intentionWord, ppv:yearTheme

### New SHACL Shapes

#### PillarScoreShape
Follow the exact pattern of existing shapes — PropertyGroups + NodeShape with sh:property array.

Groups:
- `ppv:PillarScoreBasicGroup` (order 1) — title, score, wentWell, needsAttention
- `ppv:PillarScoreRelationshipsGroup` (order 2) — weeklyReview (required, maxCount 1), pillar (required, maxCount 1)
- `ppv:PillarScoreMetadataGroup` (order 3) — dcterms:created

Key SHACL constraints:
- `ppv:score`: sh:datatype xsd:integer, sh:minInclusive 1, sh:maxInclusive 10, sh:minCount 1, sh:maxCount 1
- `ppv:weeklyReview`: sh:class ppv:WeeklyReview, sh:minCount 1, sh:maxCount 1
- `ppv:pillar`: sh:class ppv:Pillar, sh:minCount 1, sh:maxCount 1

#### GuidingPrinciplesShape
Groups:
- `ppv:GuidingPrinciplesBasicGroup` (order 1) — title, values, purpose, meaning, manifestation
- `ppv:GuidingPrinciplesStatementGroup` (order 2) — foundationalStatement, guidingWord
- `ppv:GuidingPrinciplesMetadataGroup` (order 3) — dcterms:created

All string properties are optional (no minCount) except dcterms:title.

#### Extended Review Shapes
Add new sh:property entries to existing review shapes. Each new property:
- Goes in a new or existing "Reflection" group
- sh:datatype xsd:string, sh:maxCount 1, optional
- Ordered after existing properties (increment sh:order values)

WeeklyReview already has 7 properties (orders 1-7). New properties go in a new "Reflection" group (order between BasicGroup and DatesGroup):
- `ppv:WeeklyReviewReflectionGroup` (sh:order 2, push Dates to 3, Relationships to 4, Metadata to 5)

Actually, existing WeeklyReview groups are: Basic (1), Period (2), Relationships (3), Metadata (4). Add a new "Reflection" group with sh:order between existing ones. The cleanest approach: insert `ppv:WeeklyReviewReflectionGroup` at sh:order 2 and renumber Period→3, Relationships→4, Metadata→5. Or: add Reflection at order 5 (after Metadata order 4) — simpler, no renumbering. **Go with adding at the end** to avoid renumbering existing groups.

MonthlyReview already has a "Reflection" group with gratitude and learnedThisMonth. Add new properties (biggestWins, biggestChallenges, focusAreas, habitsToAdjust) to the same group.

QuarterlyReview has no Reflection group. Add one with all 6 new properties.

YearlyReview has no Reflection group. Add one with intentionWord and yearTheme.

### New ViewSpecs

4 new entries in views/ppv.jsonld following the exact JSON-LD format of existing ViewSpecs.

**1. `ppv:view-pillarscore-table`** — PillarScore table
- target: ppv:PillarScore
- renderer: table
- SPARQL: SELECT ?s ?title ?score ?pillarTitle ?weekTitle ?wentWell ?needsAttention WHERE { ... }
- columns: title,score,pillarTitle,weekTitle,wentWell,needsAttention
- sortDefault: title

**2. `ppv:view-action-kanban`** — ActionItem kanban by status
- target: ppv:ActionItem
- renderer: kanban
- SPARQL: SELECT ?s ?title ?status ?priority ?doDate ?context WHERE { ... }
- Note: kanban renderer auto-detects status field from SHACL sh:in on ppv:status. The ViewSpec just needs rendererType="kanban" and a basic SELECT query.

**3. `ppv:view-project-kanban`** — Project kanban by status
- target: ppv:Project
- renderer: kanban
- SPARQL: SELECT ?s ?title ?status ?priority ?progress WHERE { ... }

**4. `ppv:view-action-by-context`** — ActionItem table filtered by context
- target: ppv:ActionItem
- renderer: table
- SPARQL: SELECT ?s ?title ?status ?priority ?doDate ?context ?energy WHERE { ... } ORDER BY ?context
- columns: title,status,priority,doDate,context,energy
- sortDefault: context

### New SHACL-AF Rule

One new denormalization rule: When a PillarScore is linked to a WeeklyReview, copy the review's `schema:startDate` to the PillarScore as a denormalized `schema:startDate`. This enables time-series queries (pillar score trends) without joining through the weekly review.

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

The `schema` prefix needs to be added to `ppv:PrefixDeclarations`.

### Manifest Icon Entries

Two new icon entries in manifest.yaml:

```yaml
- type: "ppv:PillarScore"
  icon: "bar-chart-2"
  color: "#f59e0b"
  # ... tree/tab/graph sub-entries

- type: "ppv:GuidingPrinciples"
  icon: "heart-handshake"
  color: "#8b5cf6"
  # ... tree/tab/graph sub-entries
```

### Validation Constraints

The model archive validator (`backend/app/models/validator.py`) checks:
1. SHACL shapes target classes defined in ontology — PillarScore and GuidingPrinciples must be in ontology
2. Seed data uses types defined in ontology — no seed changes in S02, but S04 will need these classes
3. ViewSpecs reference classes defined in ontology — new ViewSpecs must reference ontology-defined classes

All constraints are satisfied if ontology classes are added first (or simultaneously with shapes/views in the same archive).

### Cross-File Reference Map

```
ontology/ppv.jsonld
  ├── ppv:PillarScore (class) ← referenced by shapes, views, rules
  ├── ppv:GuidingPrinciples (class) ← referenced by shapes
  ├── ppv:weeklyReview (property) ← used in shapes, rules
  ├── ppv:score (property) ← used in shapes
  └── ... (15+ new properties)

shapes/ppv.jsonld
  ├── ppv:PillarScoreShape → targets ppv:PillarScore
  ├── ppv:GuidingPrinciplesShape → targets ppv:GuidingPrinciples
  ├── ppv:WeeklyReviewShape → extended with 3 new properties
  ├── ppv:MonthlyReviewShape → extended with 4 new properties
  ├── ppv:QuarterlyReviewShape → extended with 6 new properties
  └── ppv:YearlyReviewShape → extended with 2 new properties

views/ppv.jsonld
  ├── ppv:view-pillarscore-table → targets ppv:PillarScore
  ├── ppv:view-action-kanban → targets ppv:ActionItem (existing)
  ├── ppv:view-project-kanban → targets ppv:Project (existing)
  └── ppv:view-action-by-context → targets ppv:ActionItem (existing)

rules/ppv.ttl
  └── ppv:PillarScoreDateDenormRule → targets ppv:PillarScore
```

### Verification Strategy

1. **JSON-LD validity**: `python3 -c "import json; json.load(open('models/ppv/ontology/ppv.jsonld'))"` for each JSON-LD file
2. **Turtle validity**: `python3 -c "from rdflib import Graph; g=Graph(); g.parse('models/ppv/rules/ppv.ttl', format='turtle')"` for rules
3. **Cross-reference integrity**: Run the model validator: `cd backend && python3 -c "from app.models.validator import validate_archive; from app.models.loader import load_archive; ..."` — or write a focused test
4. **Manifest YAML validity**: `python3 -c "import yaml; yaml.safe_load(open('models/ppv/manifest.yaml'))"`
5. **rdflib parse round-trip**: Load ontology + shapes into a combined graph, verify PillarScore and GuidingPrinciples classes are present, verify SHACL shapes target them
6. **Unit test**: A focused test that loads all PPV model files, verifies new classes/shapes/views/rules parse without error, and checks cross-references

### Task Decomposition Suggestion

**T01: Ontology + Shapes + Manifest Icons** (~45 min)
- Add PillarScore and GuidingPrinciples classes + all new properties to ontology
- Add PillarScoreShape and GuidingPrinciplesShape to shapes
- Extend 4 review shapes with new reflection properties
- Add 2 icon entries to manifest.yaml
- Verify: all JSON-LD files parse, rdflib loads ontology + shapes, new classes present

**T02: Views + Rules + Verification** (~30 min)
- Add 4 new ViewSpecs to views file
- Add PillarScoreDateDenormRule to rules file (+ schema prefix declaration)
- Add a validation rule for PillarScore missing pillar link
- Run full model archive validation
- Unit test covering all new artifacts
