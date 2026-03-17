---
id: S02
parent: M011
milestone: M011
provides:
  - Complete CRM model archive (6 files) with Contact, Company, Interaction, Deal types
  - SHACL-AF inference rule deriving crm:lastContactedDate from linked Interaction dates
  - SHACL-AF validation warnings for stale contacts (zero interactions) and overdue follow-ups
  - 10 ViewSpecs (table/card/graph per type + CRM network graph) and 4 SavedQueries
  - Seed data with 12 realistic CRM objects and both-side inverseOf pre-populated
requires:
  - slice: none
    provides: independent (no inter-model dependencies per D151)
affects:
  - S05
key_files:
  - models/crm/manifest.yaml
  - models/crm/ontology/crm.jsonld
  - models/crm/shapes/crm.jsonld
  - models/crm/views/crm.jsonld
  - models/crm/rules/crm.ttl
  - models/crm/seed/crm.jsonld
key_decisions:
  - "D157: CRM stale-contact SHACL rule uses NOT EXISTS instead of 90-day duration arithmetic (rdflib limitation K001)"
patterns_established:
  - CRM namespace convention urn:sempkm:model:crm: for all subject IRIs
  - bpkm prefix in ontology @context for cross-model tag reuse (crm:Contact can use bpkm:tags)
  - SHACL-AF PrefixDeclarations pattern for CRM model (crm:PrefixDeclarations with crm and xsd prefixes)
  - Shapes use "sempkm":"urn:sempkm:" while views use "sempkm":"urn:sempkm:vocab:" (critical namespace split)
  - Seed data uses typed dates {"@value":"...", "@type":"xsd:date"} and typed decimals for dealValue
observability_surfaces:
  - "parse_manifest(Path('models/crm')) — validates manifest via Pydantic, raises ValueError on failure"
  - "validate_archive() — returns ValidationResult with .is_valid, .errors[], .warnings[]"
  - "pyshacl.validate(advanced=True) — conforms=False with 2 Warning violations (stale contact, overdue follow-up)"
  - "Inference check: query (None, CRM.lastContactedDate, None) after inplace=True — returns 3 triples"
drill_down_paths:
  - .gsd/milestones/M011/slices/S02/tasks/T01-SUMMARY.md
  - .gsd/milestones/M011/slices/S02/tasks/T02-SUMMARY.md
  - .gsd/milestones/M011/slices/S02/tasks/T03-SUMMARY.md
duration: 80m
verification_result: passed
completed_at: 2026-03-17
---

# S02: Personal CRM Model

**Complete CRM model archive with 4 types (Contact, Company, Interaction, Deal), SHACL-AF inference and validation rules, 10 ViewSpecs, 4 SavedQueries, and 12 seed objects — all passing offline validation with 2 Warning-level violations firing correctly.**

## What Happened

Built a 6-file `.sempkm-model` archive under `models/crm/` delivering a Personal CRM experience:

**T01 — Manifest and ontology (15m):** Created `manifest.yaml` with modelId `crm`, namespace `urn:sempkm:model:crm:`, 4 Lucide icon entries (user/building-2/message-circle/handshake) each with tree/tab/graph contexts, and `entailment_defaults` enabling owl_inverseOf and shacl_rules. Created ontology with 4 OWL classes aligned to gist hierarchy (Contact→gist:Person, Company→gist:Organization, Interaction→gist:Event, Deal→gist:Agreement), 20 datatype properties, 9 object properties including 4 bidirectional `owl:inverseOf` pairs (worksAt↔hasEmployee, withContact↔hasInteraction, dealContact↔hasContactDeal, dealCompany↔hasCompanyDeal), and `crm:knows` as `owl:SymmetricProperty`. 170 triples, all namespace-compliant.

**T02 — Shapes and views (20m):** Created SHACL shapes with 4 NodeShapes, 17 PropertyGroups for logical field grouping, 6 `sh:in` enums (relationship type, company size, interaction type, deal stage, currency, plus the general-purpose list patterns), and `sempkm:editHelpText` on shapes. Created views with 10 ViewSpecs (Contact table/card/graph, Company table/graph, Interaction table/graph, Deal table/card, CRM Network graph) and 4 SavedQueries (Stale Contacts, Upcoming Follow-ups, Open Deals, Network Map). 405 shape triples + 81 view triples.

**T03 — Rules, seed data, and validation (25m):** Created SHACL-AF rules in Turtle with 3 separate NodeShapes per D153: (1) LastContactedDeriveRule — SPARQLRule CONSTRUCTs `crm:lastContactedDate` from MAX interaction date, (2) StaleContactValidationShape — SPARQLConstraint Warning for contacts with zero interactions (NOT EXISTS fallback per K001/D157), (3) FollowUpOverdueValidationShape — SPARQLConstraint Warning for overdue follow-ups using the proven `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` pattern. Created seed data with 12 objects: 3 companies (Acme Corp, Bright Ideas Studio, DataFlow Inc), 4 contacts (Sarah Park, James Liu, Priya Sharma, Marcus Cole), 3 interactions, 2 deals ($150k and $25k). Both sides of inverseOf pre-populated per D154. Trigger data: Marcus Cole has zero interactions (stale contact), James meeting has overdue followUpDate (overdue follow-up).

## Verification

All 5 slice verification steps pass:

1. **Individual file parse:** ontology (170), shapes (405), views (81), seed (141), rules (31) triples — all parse cleanly ✅
2. **Full pipeline validation:** `parse_manifest()` + `load_archive()` + `validate_archive()` → `is_valid=True`, 0 errors ✅
3. **SHACL-AF validation:** `conforms=False` with 2 Warning-level violations:
   - StaleContactValidationShape: `seed-contact-marcus` — "Contact has had no interactions recorded"
   - FollowUpOverdueValidationShape: `seed-interaction-meeting-james` — "Follow-up is overdue and not marked done" ✅
4. **Diagnostic error reporting:** `parse_manifest(Path('/tmp/nonexistent-model'))` raises `ValueError` with structured message ✅
5. **Triple count diagnostics:** Rules 31 (≥20), Seed 141 (≥60) ✅

**Bonus — inference verification:** `lastContactedDate` materialized for 3 contacts (Sarah→2026-03-10, James→2026-03-15, Priya→2025-11-01) from 0 pre-existing triples ✅

## Requirements Advanced

- MODEL-02 — CRM model archive complete with all 4 types, SHACL forms, ViewSpecs, validation warnings, and seed data. Passes offline validation. Awaits S05 for Docker integration testing.

## Requirements Validated

- None yet — MODEL-02 requires Docker install + form rendering + view rendering proof (S05)

## New Requirements Surfaced

- None

## Requirements Invalidated or Re-scoped

- None

## Deviations

- **Stale-contact rule simplified (D157):** Plan specified 90-day duration arithmetic. rdflib doesn't support `xsd:dayTimeDuration` subtraction (K001). Rule uses `NOT EXISTS` to catch zero-interaction contacts. The SavedQuery "Stale Contacts" handles the time-windowed check.
- **Stale-contact triggers Marcus (not Priya):** Plan expected Priya (old interactions) to trigger. With simplified rule, Marcus (zero interactions) triggers instead. Both demonstrate the warning mechanism correctly.
- **4 inverseOf pairs instead of 3:** Plan listed 3 but detailed property descriptions included 4. All 4 implemented.

## Known Limitations

- **90-day stale contact detection** requires date arithmetic not supported by rdflib's SPARQL engine. The SHACL rule catches zero-interaction contacts; the SavedQuery provides date-based filtering at runtime.
- **No Docker integration testing** — model verified offline only. S05 will prove install + form rendering + view rendering + inference + validation in live Docker environment.

## Follow-ups

- S05: Docker install and form rendering verification for all CRM types
- S05: E2E Playwright tests for CRM object creation and view rendering
- S05: User guide Chapter 31 documenting CRM model usage

## Files Created/Modified

- `models/crm/manifest.yaml` — Model identity, 4 icon entries, entailment_defaults
- `models/crm/ontology/crm.jsonld` — 4 OWL classes, 29 properties, 4 inverseOf pairs, 1 SymmetricProperty (170 triples)
- `models/crm/shapes/crm.jsonld` — 4 NodeShapes, 17 PropertyGroups, 6 enums, helptext (405 triples)
- `models/crm/views/crm.jsonld` — 10 ViewSpecs + 4 SavedQueries (81 triples)
- `models/crm/rules/crm.ttl` — 1 inference rule + 2 validation rules (31 triples)
- `models/crm/seed/crm.jsonld` — 12 seed objects with trigger data (141 triples)

## Forward Intelligence

### What the next slice should know
- The CRM model follows the same structural template as basic-pkm v2. S03 (Zettelkasten+) and S04 (Research Workflow) can use the same 6-file structure and verification pattern.
- The `sempkm` namespace split (shapes=`urn:sempkm:`, views=`urn:sempkm:vocab:`) is critical — mixing them causes runtime failures. This was proven in S01 and S02.
- Seed data must include both sides of inverseOf pairs per D154 — inference produces 0 new triples for seed data because both sides are already there. Inference is proven by testing with one-sided data.

### What's fragile
- **Date comparison in SHACL-AF rules** — the `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` pattern works but rdflib's date handling is limited. Any rule requiring duration arithmetic (P90D, P7D) must use NOT EXISTS or SavedQuery fallback per K001.
- **Seed data followUpDate** — set to 2026-03-16 which is "yesterday" as of verification. If verification runs far in the future, the overdue follow-up warning still fires (any past date works). But if seed data gets dates changed to future dates, the warning won't fire.

### Authoritative diagnostics
- `pyshacl.validate(data, shacl_graph=shapes+rules, ont_graph=ontology, advanced=True)` — returns the full validation report text with focus node, severity, source shape, and message for each violation. This is the single source of truth for whether rules fire correctly.
- `validate_archive()` return value — `.is_valid`, `.errors[]`, `.warnings[]` is the canonical pass/fail surface for the full pipeline.

### What assumptions changed
- **90-day duration arithmetic** was assumed possible in SHACL-AF SPARQL. It is not in rdflib. This was already discovered in S01 planning and recorded as K001, but S02 confirmed the fallback pattern (NOT EXISTS + SavedQuery) works well for CRM.
- **StaleContact trigger object** — assumed Priya (old interactions) would trigger. Marcus (zero interactions) triggers instead with the simplified rule. The model is still correct; just a different trigger scenario.
