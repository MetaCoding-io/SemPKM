---
id: T02
parent: S02
milestone: M011
provides:
  - SHACL shapes for 4 CRM types with PropertyGroups, enums, and helptext
  - 10 ViewSpecs (table/card/graph per type + CRM network graph)
  - 4 SavedQueries (Stale Contacts, Upcoming Follow-ups, Open Deals, Network Map)
key_files:
  - models/crm/shapes/crm.jsonld
  - models/crm/views/crm.jsonld
key_decisions: []
patterns_established:
  - CRM shapes follow bpkm structural template — PropertyGroups with sh:order, sh:in with @list, sempkm:editHelpText on both NodeShape and PropertyShape
  - Views use full IRIs in SPARQL (not prefixed names) to avoid namespace resolution issues at runtime
  - SavedQueries use urn:sempkm:model:crm:query:* IRI pattern matching bpkm convention
observability_surfaces:
  - "Shapes triple count: 405 triples — count <100 signals missing PropertyGroups or properties"
  - "Views triple count: 81 triples — count <30 signals missing ViewSpecs"
  - "sh:targetClass audit: 4 declarations matching ontology OWL classes"
  - "Namespace check: shapes @context.sempkm = urn:sempkm:, views @context.sempkm = urn:sempkm:vocab:"
duration: 20m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Author CRM shapes and views

**Created SHACL shapes (4 NodeShapes, 17 PropertyGroups, 6 sh:in enums) and views (10 ViewSpecs + 4 SavedQueries) for all CRM types.**

## What Happened

Created `models/crm/shapes/crm.jsonld` with 4 NodeShapes following the basic-pkm structural template:
- **ContactShape** — 6 PropertyGroups (Basic Info, Professional, Social, Follow-up, Tags, Notes), 12 properties including worksAt (→Company), knows (→Contact), relationship enum (colleague/client/friend/mentor/vendor/other)
- **CompanyShape** — 4 PropertyGroups (Basic Info, Details, People, Notes), 6 properties including size enum (solo/small/medium/large/enterprise), hasEmployee (→Contact)
- **InteractionShape** — 3 PropertyGroups (Details, People, Follow-up), 6 properties including interactionType enum (meeting/call/email/coffee/conference/other), withContact (→Contact)
- **DealShape** — 3 PropertyGroups (Basic Info, Parties, Notes), 7 properties including dealStage enum (lead/qualified/proposal/negotiation/won/lost), currency enum (USD/EUR/GBP)

Created `models/crm/views/crm.jsonld` with 10 ViewSpecs and 4 SavedQueries:
- ViewSpecs: Contact table/card/graph, Company table/graph, Interaction table/graph, Deal table/card, CRM Network graph
- SavedQueries: Stale Contacts, Upcoming Follow-ups, Open Deals, Network Map

Critical namespace difference preserved: shapes use `"sempkm": "urn:sempkm:"`, views use `"sempkm": "urn:sempkm:vocab:"`.

## Verification

- Shapes parse: 405 triples, 4 `sh:targetClass` declarations confirmed (Contact, Company, Interaction, Deal)
- Views parse: 81 triples, 10 ViewSpec subjects + 4 SavedQuery subjects confirmed
- Cross-check: all 4 `sh:targetClass` values match OWL classes in ontology — all OK
- Namespace: shapes `sempkm` = `urn:sempkm:`, views `sempkm` = `urn:sempkm:vocab:` — verified

Slice-level verification Step 1 (individual file parse): 3 of 5 files pass (ontology + shapes + views). Remaining 2 files (seed, rules) are T03 deliverables.

## Diagnostics

- `Graph().parse('models/crm/shapes/crm.jsonld', format='json-ld')` — 405 triples; count <100 signals missing shapes/PropertyGroups
- `Graph().parse('models/crm/views/crm.jsonld', format='json-ld')` — 81 triples; count <30 signals missing ViewSpecs
- Query `sh:targetClass` triples from shapes graph — must return exactly 4
- JSON load `@context.sempkm` from each file — shapes must be `urn:sempkm:`, views must be `urn:sempkm:vocab:`

## Deviations

- Plan listed `dealStage` values as `lead/qualified/proposal/negotiation/won/lost` — used these exact values (ontology rdfs:comment had slightly different terms like `prospect` and `closed-won`; shapes align with the plan which are cleaner for user-facing enums)
- Plan listed company `size` values as `solo/small/medium/large/enterprise` — used these exact values (ontology rdfs:comment had `startup` instead of `solo`)

## Known Issues

None.

## Files Created/Modified

- `models/crm/shapes/crm.jsonld` — SHACL shapes with 4 NodeShapes, 17 PropertyGroups, 6 enums, helptext
- `models/crm/views/crm.jsonld` — 10 ViewSpecs + 4 SavedQueries for table/card/graph browsing
- `.gsd/milestones/M011/slices/S02/tasks/T02-PLAN.md` — Added Observability Impact section (pre-flight fix)
