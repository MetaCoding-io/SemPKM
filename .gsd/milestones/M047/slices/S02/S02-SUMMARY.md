---
id: S02
parent: M047
milestone: M047
provides:
  - ppv:PillarScore OWL class + SHACL shape (score 1-10, links to Pillar + WeeklyReview)
  - ppv:GuidingPrinciples OWL class + SHACL shape (values, purpose, meaning, manifestation, foundationalStatement, guidingWord)
  - 15 enriched review reflection properties across Weekly/Monthly/Quarterly/Yearly review shapes
  - 4 new ViewSpecs (pillarscore-table, action-kanban, project-kanban, action-by-context)
  - PillarScoreDateDenormRule (schema:startDate denormalization for calendar/timeline)
  - 99-test validation suite for all PPV ontology expansion artifacts
requires:
  - slice: S01
    provides: Manifest v2 infrastructure with TBox lifecycle hooks
affects:
  - S03
  - S04
key_files:
  - models/ppv/ontology/ppv.jsonld
  - models/ppv/shapes/ppv.jsonld
  - models/ppv/views/ppv.jsonld
  - models/ppv/rules/ppv.ttl
  - models/ppv/manifest.yaml
  - backend/tests/test_ppv_ontology.py
key_decisions:
  - Reused existing ppv:pillar ObjectProperty (no domain restriction) for PillarScore rather than creating a duplicate property
  - Kanban ViewSpecs omit columns/sortDefault since kanban renderer auto-detects status field via SHACL sh:in
  - PillarScoreDateDenormRule derives schema:startDate from linked WeeklyReview to enable calendar/timeline views for PillarScore
patterns_established:
  - SHACL-AF SPARQLRule for date denormalization: derive a date property from a linked object's date to enable time-based views on types that don't have their own date
  - PropertyGroup extension pattern: add new groups to existing shapes at sh:order values after existing groups, with property sh:order values that don't collide
observability_surfaces:
  - none
drill_down_paths:
  - .gsd/milestones/M047/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M047/slices/S02/tasks/T02-SUMMARY.md
duration: ""
verification_result: passed
completed_at: 2026-04-04T23:45:37.654Z
blocker_discovered: false
---

# S02: PPV Ontology Expansion — PillarScore, GuidingPrinciples & Enriched Reviews

**Expanded PPV ontology with PillarScore and GuidingPrinciples classes, 25 new properties, enriched review fields on all 4 review types, 4 new ViewSpecs, a SHACL-AF denormalization rule, manifest icons, and a 99-test validation suite.**

## What Happened

T01 added two new OWL classes (PillarScore for weekly pillar scoring, GuidingPrinciples for values anchor documents) with 22 new ontology properties across the PPV namespace. PillarScore has score (integer 1-10), wentWell, needsAttention, plus weeklyReview and pillar object links. GuidingPrinciples has values, purpose, meaning, manifestation, foundationalStatement, and guidingWord text fields. Fifteen reflection properties were added across all four review types: WeeklyReview (+3: wins, challenges, supportingPriorities), MonthlyReview (+4: biggestWins, biggestChallenges, focusAreas, habitsToAdjust), QuarterlyReview (+6: accomplishments, disappointments, whatWorked, whatDidntWork, howToImprove, annualVisionNotes), and YearlyReview (+2: intentionWord, yearTheme).

SHACL NodeShapes were created for both new classes with property groups (Basic/Relationships/Metadata for PillarScore; Basic/Statement/Metadata for GuidingPrinciples). The PillarScore shape enforces sh:minInclusive 1 and sh:maxInclusive 10 on the score property. All four existing review shapes were extended with new PropertyGroups (ReflectionGroup) containing the reflection fields at appropriate sh:order values that don't collide with existing properties. Manifest icons added for both types (bar-chart-2 amber for PillarScore, heart-handshake purple for GuidingPrinciples).

T02 added 4 new ViewSpecs (pillarscore-table, action-kanban, project-kanban, action-by-context table) bringing total PPV ViewSpecs to 23. Added the PillarScoreDateDenormRule — a SHACL-AF SPARQLRule that derives schema:startDate on PillarScore from the linked WeeklyReview's startDate, enabling calendar and timeline views for pillar scores. This required adding the schema prefix to both the rules file header and the ppv:PrefixDeclarations block.

A comprehensive test_ppv_ontology.py file with 99 tests across 9 test classes validates all new artifacts: ontology class existence, 25 property existence and typing, SHACL shape targets, score constraints, PropertyGroup existence, ViewSpec metadata, rules file structure, manifest icons, combined graph parsing, and cross-reference integrity between ontology classes, shapes, and ViewSpec targets.

## Verification

All 99 tests pass (cd backend && .venv/bin/python -m pytest tests/test_ppv_ontology.py -v — 99 passed in 0.27s). JSON valid for ontology and shapes files. YAML valid for manifest. rdflib parses ontology (364 triples) with both new classes found. rdflib parses rules as Turtle (63 triples). Cross-reference validation confirms PillarScore and GuidingPrinciples classes in ontology match sh:targetClass in shapes and sempkm:targetClass in ViewSpecs.

## Requirements Advanced

None.

## Requirements Validated

None.

## New Requirements Surfaced

None.

## Requirements Invalidated or Re-scoped

None.

## Deviations

None.

## Known Limitations

None.

## Follow-ups

S03 will consume the new classes, ViewSpecs, and denorm rule to build TBox dashboards and workflows that reference PillarScore and GuidingPrinciples. S04 seed data will need to create PillarScore and GuidingPrinciples instances for realistic dashboard rendering.

## Files Created/Modified

- `models/ppv/ontology/ppv.jsonld` — Added PillarScore + GuidingPrinciples OWL classes, 22 new properties (10 PillarScore/GuidingPrinciples + 15 review reflection - 3 counted in both)
- `models/ppv/shapes/ppv.jsonld` — Added PillarScoreShape + GuidingPrinciplesShape NodeShapes with PropertyGroups, extended 4 review shapes with ReflectionGroups and 15 new property shapes
- `models/ppv/views/ppv.jsonld` — Added 4 new ViewSpecs: pillarscore-table, action-kanban, project-kanban, action-by-context
- `models/ppv/rules/ppv.ttl` — Added schema prefix, PillarScoreDateDenormRule SHACL-AF SPARQLRule
- `models/ppv/manifest.yaml` — Added icon entries for PillarScore (bar-chart-2 amber) and GuidingPrinciples (heart-handshake purple)
- `backend/tests/test_ppv_ontology.py` — New 99-test validation suite across 9 test classes
