---
id: T02
parent: S01
milestone: M011
provides:
  - TaskProjectDenormRule SHACL-AF inference rule deriving taskProject from milestone chain
  - OverdueTaskValidationShape SPARQL validation constraint with sh:Warning severity
  - Extended PrefixDeclarations with xsd: and dcterms: namespaces
key_files:
  - models/basic-pkm/rules/basic-pkm.ttl
key_decisions:
  - Used STRDT(SUBSTR(STR(NOW()),1,10),xsd:date) for date comparison because rdflib does not support xsd:date(NOW()) cast
  - Kept owl:inverseOf inference out of rules file — platform entailment engine handles it (manifest owl_inverseOf:true)
  - Validation shape is a SEPARATE NodeShape from inference shapes per D153; sh:severity on NodeShape not on SPARQLConstraint
patterns_established:
  - SPARQLConstraint date comparison via STRDT+SUBSTR+NOW for rdflib compatibility
  - Validation shapes separated from inference shapes with sh:severity on parent NodeShape
observability_surfaces:
  - "Rules triple count: python -c \"from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/rules/basic-pkm.ttl', format='turtle'); print(len(g))\" → 35"
  - "NodeShape count in rules file: 3 (ProjectRelatedNoteRule, TaskProjectDenormRule, OverdueTaskValidationShape)"
  - "pyshacl warning detection: validate with advanced=True, check results graph for SH.Warning from OverdueTaskValidationShape"
duration: 15m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T02: Add inference and validation rules for Tasks

**Added TaskProjectDenormRule inference and OverdueTaskValidationShape validation constraint to basic-pkm rules, with rdflib-compatible date arithmetic.**

## What Happened

Expanded `models/basic-pkm/rules/basic-pkm.ttl` from 1 NodeShape (ProjectRelatedNoteRule) to 3:

1. **TaskProjectDenormRule** — SHACL-AF SPARQLRule targeting `bpkm:Task`. Derives `bpkm:taskProject` from the task's milestone's project chain (`$this → bpkm:milestone → ?ms → bpkm:milestoneProject → ?project`). Uses `FILTER NOT EXISTS` to avoid overwriting explicit taskProject links.

2. **OverdueTaskValidationShape** — SHACL SPARQLConstraint on a separate NodeShape (per D153). Flags tasks where `dueDate < today` and status is "todo", "in-progress", or "blocked". Uses `sh:severity sh:Warning` on the NodeShape so overdue tasks don't fail conformance.

3. **PrefixDeclarations** — Extended with `xsd:` and `dcterms:` namespace declarations for SPARQL use.

The key risk item was date arithmetic in SPARQL. Testing revealed rdflib does NOT support `xsd:date(NOW())` — it produces empty results. The working approach is `STRDT(SUBSTR(STR(NOW()), 1, 10), xsd:date)` which constructs a proper `xsd:date` literal from the current datetime string. This was verified to work correctly in both standalone SPARQL queries and pyshacl validation.

Confirmed `owl_inverseOf: true` in manifest — no need for inverse inference rules in the rules file.

## Verification

All checks passed:

- **Turtle parse**: 35 triples loaded without error
- **NodeShape count**: 3 (ProjectRelatedNoteRule, TaskProjectDenormRule, OverdueTaskValidationShape)
- **Severity placement**: Exactly 1 `sh:severity` triple, on `OverdueTaskValidationShape` → `sh:Warning`
- **ProjectRelatedNoteRule**: Preserved unchanged
- **pyshacl end-to-end test**: Created 3 test tasks (overdue/done/future), ran `pyshacl.validate(advanced=True)`:
  - `Conforms: True` (warnings don't fail conformance)
  - 1 validation result: `sh:Warning` on `urn:test:task-overdue` from `OverdueTaskValidationShape`
  - Done tasks and future tasks correctly excluded

Slice-level diagnostics (partial — T03/T04 not yet done):
- Ontology: 197 triples, 6 OWL classes ✅
- Rules: 35 triples, 3 NodeShapes ✅
- Full test suite: not yet created (T04)

## Diagnostics

```bash
# Parse rules and count triples
python -c "from rdflib import Graph; g=Graph(); g.parse('models/basic-pkm/rules/basic-pkm.ttl', format='turtle'); print(len(g))"
# → 35

# Count NodeShapes in rules
python -c "from rdflib import Graph, URIRef; g=Graph(); g.parse('models/basic-pkm/rules/basic-pkm.ttl', format='turtle'); print(len(list(g.subjects(URIRef('http://www.w3.org/1999/02/22-rdf-syntax-ns#type'), URIRef('http://www.w3.org/ns/shacl#NodeShape')))))"
# → 3

# Verify severity placement
python -c "from rdflib import Graph, URIRef; g=Graph(); g.parse('models/basic-pkm/rules/basic-pkm.ttl', format='turtle'); sev=list(g.triples((None, URIRef('http://www.w3.org/ns/shacl#severity'), None))); print(len(sev)); assert len(sev)==1"
# → 1
```

## Deviations

- **Date comparison approach**: Plan suggested `xsd:date(NOW())` with fallback to string comparison. Implemented `STRDT(SUBSTR(STR(NOW()), 1, 10), xsd:date)` instead — this produces a proper typed `xsd:date` literal (better than string comparison) while working around rdflib's lack of `xsd:date()` cast support.
- **No owl:inverseOf rules added**: Plan step 4 mentioned confirming the entailment engine handles inverses. Confirmed — `owl_inverseOf: true` is in the manifest, so no inverse rules were needed or added.

## Known Issues

None.

## Files Created/Modified

- `models/basic-pkm/rules/basic-pkm.ttl` — Expanded from 1 to 3 NodeShapes: added TaskProjectDenormRule (inference) and OverdueTaskValidationShape (validation with sh:Warning), extended PrefixDeclarations with xsd: and dcterms:
