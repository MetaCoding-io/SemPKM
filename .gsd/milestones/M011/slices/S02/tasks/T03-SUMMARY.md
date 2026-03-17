---
id: T03
parent: S02
milestone: M011
provides:
  - CRM SHACL-AF rules with 1 inference rule (LastContactedDeriveRule) + 2 validation rules (StaleContactValidation, FollowUpOverdueValidation)
  - CRM seed data with 12 objects (3 companies, 4 contacts, 3 interactions, 2 deals) covering all 4 types
  - Both-side inverseOf population per D154
  - Trigger data for 2 validation warnings (stale contact, overdue follow-up)
key_files:
  - models/crm/rules/crm.ttl
  - models/crm/seed/crm.jsonld
key_decisions:
  - StaleContact rule uses NOT EXISTS (no interactions) instead of 90-day duration arithmetic — rdflib does not support xsd:dayTimeDuration subtraction from xsd:date
  - FollowUpOverdue rule targets crm:Interaction (not crm:Contact) since followUpDate is set on interactions per ontology
patterns_established:
  - SHACL-AF PrefixDeclarations pattern for CRM model (crm:PrefixDeclarations with crm and xsd prefixes declared)
  - Seed data uses typed dates {"@value": "...", "@type": "xsd:date"} and typed decimals for dealValue
observability_surfaces:
  - pyshacl.validate(advanced=True) returns conforms=False with Warning-level violations for stale contact (Marcus Cole, no interactions) and overdue follow-up (meeting with James, followUpDate 2026-03-16)
  - Inference rule materializes crm:lastContactedDate for 3 contacts (Sarah=2026-03-10, James=2026-03-15, Priya=2025-11-01)
  - validate_archive() returns is_valid=True with 0 errors for the complete 6-file archive
duration: 25m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T03: Author CRM rules, seed data, and run full pipeline validation

**Created CRM SHACL-AF rules (3 NodeShapes: 1 inference + 2 validation) and seed data (12 objects across 4 types), all passing full pipeline and pyshacl validation with Warning-level violations firing as expected.**

## What Happened

Created `models/crm/rules/crm.ttl` in Turtle format with 3 separate NodeShapes per D153:
1. **LastContactedDeriveShape** — SPARQLRule targeting Contact, CONSTRUCTs `crm:lastContactedDate` from `MAX(crm:interactionDate)` of linked Interactions. Verified: materializes dates for all 3 contacts with interactions.
2. **StaleContactValidationShape** — SPARQLConstraint with `sh:severity sh:Warning`, fires when a Contact has NO linked Interactions at all (simpler than 90-day arithmetic which rdflib doesn't support). Marcus Cole triggers this.
3. **FollowUpOverdueValidationShape** — SPARQLConstraint with `sh:severity sh:Warning` targeting Interaction, fires when `crm:followUpDate < today` and `crm:followUpDone` is not true. Uses proven `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` pattern. Meeting with James triggers this.

Created `models/crm/seed/crm.jsonld` with 12 objects (141 triples):
- 3 Companies: Acme Corp (large/technology), Bright Ideas Studio (small/design), DataFlow Inc (medium/analytics)
- 4 Contacts: Sarah Park (client, Acme), James Liu (colleague, Acme), Priya Sharma (vendor, Bright Ideas), Marcus Cole (mentor, DataFlow)
- 3 Interactions: Coffee with Sarah (2026-03-10), Meeting with James (2026-03-15, overdue follow-up), Email with Priya (2025-11-01, old)
- 2 Deals: Enterprise Platform License ($150k, proposal), Design System Audit ($25k, lead)

All inverseOf pairs pre-populated both directions per D154. Sarah↔James `knows` relationship is symmetric.

## Verification

All 5 slice verification steps pass:

1. **Individual file parse** — All 5 files parse: ontology (170), shapes (405), views (81), seed (141), rules (31) triples
2. **Full pipeline validation** — `validate_archive()` returns `is_valid=True`, 0 errors, 0 warnings
3. **pyshacl advanced=True** — `conforms=False` with 2 Warning-level violations:
   - StaleContactValidationShape: `seed-contact-marcus` (no interactions)
   - FollowUpOverdueValidationShape: `seed-interaction-meeting-james` (followUpDate 2026-03-16 < today)
4. **Diagnostic error reporting** — `parse_manifest(Path('/tmp/nonexistent-model'))` raises `ValueError: manifest.yaml not found`
5. **Triple count diagnostics** — Rules: 31 (≥20 ✓), Seed: 141 (≥60 ✓)

**Inference verification:** `lastContactedDate` materialized for Sarah (2026-03-10), James (2026-03-15), Priya (2025-11-01) — 3 triples derived from 0 pre-existing.

## Diagnostics

- **Rules parse:** `Graph().parse('models/crm/rules/crm.ttl', format='turtle')` → 31 triples. Parse error = Turtle syntax issue with line number.
- **Seed parse:** `Graph().parse('models/crm/seed/crm.jsonld', format='json-ld')` → 141 triples. Count <80 signals missing objects or broken @context.
- **Validation warnings:** `pyshacl.validate(..., advanced=True)` → text output contains focus node IRI, severity, source shape, and message for each violation.
- **Inference check:** After `inplace=True` validation, query `data.triples((None, CRM.lastContactedDate, None))` → should return 3 triples for contacts with interactions.

## Deviations

- **StaleContact rule simplified:** Plan specified 90-day duration arithmetic (`?today - "P90D"^^xsd:dayTimeDuration`). rdflib's SPARQL engine does not support this. Used plan's fallback option: `NOT EXISTS` catches contacts with zero interactions. The "Stale Contacts" SavedQuery in views covers the date-based check. Comment in rules file documents this.
- **StaleContact triggers on Marcus (not Priya):** Plan expected Priya (old interactions only) to trigger stale-contact. With the simplified rule (no interactions at all), Marcus (zero interactions) triggers instead. Priya has an interaction (old but present). Both are valid demonstrations of the warning mechanism.

## Known Issues

- 90-day stale contact detection requires date arithmetic not supported by rdflib's SPARQL. The SavedQuery "Stale Contacts" provides this at query time; the SHACL rule catches the zero-interaction case only.

## Files Created/Modified

- `models/crm/rules/crm.ttl` — SHACL-AF rules: 1 inference (LastContactedDeriveRule) + 2 validation (StaleContactValidation, FollowUpOverdueValidation), 31 triples
- `models/crm/seed/crm.jsonld` — 12 seed objects (3 companies, 4 contacts, 3 interactions, 2 deals), 141 triples, both-side inverseOf, trigger data for warnings
