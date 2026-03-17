# S04: Research Workflow Model — Research

**Date:** 2026-03-17
**Status:** Complete
**Depth:** Light — straightforward application of patterns proven in S01–S03

## Summary

S04 builds a new `.sempkm-model` archive at `models/research/` with 5 types (Paper, Claim, Evidence, ResearchQuestion, Argument), 6 `owl:inverseOf` pairs, 4 SHACL-AF validation rules, 5 ViewSpecs, 5 SavedQueries, and 13 seed objects. This is structurally identical to S02 (CRM) and S03 (Zettelkasten+) — same 6-file archive format, same namespace conventions, same validation pipeline. The design doc (§4) is comprehensive and specifies every property, enum, rule, view, query, seed object, and icon. No platform code changes needed (D149).

The Research model is the most relationship-dense of the four M011 models: 40 properties across 5 types, 6 inverseOf pairs, and 4 validation rules (vs CRM's 3 rules and Zettelkasten's 3 rules). However, all validation rules use `NOT EXISTS` / `EXISTS` patterns — no date arithmetic is involved, avoiding K001 entirely. The primary risk is the Evidence Map graph view, which requires a CONSTRUCT query joining Claims, Evidence, and Papers — the most complex SPARQL query in any M011 model.

## Recommendation

Build in 3 tasks matching S02/S03 pattern: (1) manifest + ontology, (2) shapes + views, (3) rules + seed + validation. Use the CRM model as the structural template — it's the closest match (4 types with rich relationships). Copy patterns verbatim and adapt for `res:` namespace.

## Implementation Landscape

### Key Files

**Structural templates (read from worktree, copy patterns):**
- `.gsd/worktrees/M011/models/crm/manifest.yaml` — Reference manifest with 4 icon entries, entailment_defaults
- `.gsd/worktrees/M011/models/crm/ontology/crm.jsonld` — OWL classes with gist alignment, inverseOf pairs, datatype + object properties (170 triples)
- `.gsd/worktrees/M011/models/crm/shapes/crm.jsonld` — 4 NodeShapes, PropertyGroups, `sh:in` enums, `sempkm:editHelpText` (405 triples)
- `.gsd/worktrees/M011/models/crm/views/crm.jsonld` — ViewSpecs + SavedQueries with full-IRI SPARQL (81 triples)
- `.gsd/worktrees/M011/models/crm/rules/crm.ttl` — 1 inference + 2 validation SPARQLConstraints on separate NodeShapes (31 triples)
- `.gsd/worktrees/M011/models/crm/seed/crm.jsonld` — 12 seed objects with both sides of inverseOf pre-populated (141 triples)

**Files to create (6 new files under `models/research/`):**
- `models/research/manifest.yaml` — Model identity, 5 icon entries (tree/tab/graph), entailment_defaults
- `models/research/ontology/research.jsonld` — 5 OWL classes, ~40 properties, 6 inverseOf pairs
- `models/research/shapes/research.jsonld` — 5 NodeShapes, ~20 PropertyGroups, 5 enums, editHelpText
- `models/research/views/research.jsonld` — 5 ViewSpecs + 5 SavedQueries
- `models/research/rules/research.ttl` — 4 validation SPARQLConstraints on separate NodeShapes
- `models/research/seed/research.jsonld` — 13 seed objects with trigger data for validation rules

**Validation pipeline (no changes):**
- `backend/app/models/manifest.py` — `parse_manifest()` validates manifest
- `backend/app/models/loader.py` — `load_archive()` parses all 6 files
- `backend/app/models/validator.py` — `validate_archive()` checks IRI namespaces and cross-references

### Key Patterns to Follow

**Namespace:** `urn:sempkm:model:research:` with `res:` as JSON-LD shorthand. All subject IRIs must use the full namespace. SPARQL queries use full IRIs (no prefixed names).

**Namespace split (critical):** Shapes `@context` uses `"sempkm": "urn:sempkm:"` — Views `@context` uses `"sempkm": "urn:sempkm:vocab:"`. Mixing these causes runtime failures.

**gist alignment for all 5 types:**
- `res:Paper` → `rdfs:subClassOf gist:Content`
- `res:Claim` → `rdfs:subClassOf gist:FormattedContent`
- `res:Evidence` → `rdfs:subClassOf gist:FormattedContent`
- `res:ResearchQuestion` → `rdfs:subClassOf gist:Intention` (a research question expresses a research intention; Intention exists in gist 14.0.0)
- `res:Argument` → `rdfs:subClassOf gist:FormattedContent`

**6 owl:inverseOf pairs:**
1. `res:extractedFrom` (Claim→Paper) ↔ `res:hasClaim` (Paper→Claim)
2. `res:supports` (Evidence→Claim) ↔ `res:supportedBy` (Claim→Evidence)
3. `res:refutes` (Evidence→Claim) ↔ `res:refutedBy` (Claim→Evidence)
4. `res:cites` (Paper→Paper) ↔ `res:citedBy` (Paper→Paper)
5. `res:addresses` (Argument→ResearchQuestion) ↔ `res:hasArgument` (ResearchQuestion→Argument)
6. `res:usesClaim` (Argument→Claim) ↔ `res:addressedBy` (Claim→Argument)

**One-directional properties (no inverse):**
- `res:fromPaper` (Evidence→Paper) — one-directional
- `res:corroborates` (Claim→Claim) — one-directional
- `res:contradicts` (Claim→Claim) — one-directional
- `res:dependsOn` (Claim→Claim) — one-directional
- `res:usesEvidence` (Argument→Evidence) — one-directional

**5 sh:in enums:**
- `res:paperType`: journal-article, conference-paper, preprint, book-chapter, thesis, report, other
- `res:confidence`: established, supported, contested, speculative, refuted
- `res:evidenceType`: empirical-data, statistical-finding, case-study, expert-opinion, logical-argument, observation, quote
- `res:status`: open, partially-answered, answered, abandoned
- `res:argumentType`: literature-review, position-paper, analysis, synthesis, rebuttal

**4 SHACL-AF validation rules (all NOT EXISTS / EXISTS — no date arithmetic):**
1. `UnsupportedClaimValidationShape` (Warning, targetClass: Claim) — confidence is "established" or "supported" but `NOT EXISTS { ?e res:supports $this }`. Message: "Claim marked as {confidence} but has no supporting evidence."
2. `ContestedClaimValidationShape` (Info, targetClass: Claim) — `EXISTS { ?e1 res:supports $this }` AND `EXISTS { ?e2 res:refutes $this }`. Message: "This claim has conflicting evidence — review the argument."
3. `OrphanEvidenceValidationShape` (Warning, targetClass: Evidence) — `NOT EXISTS { $this res:supports ?x }` AND `NOT EXISTS { $this res:refutes ?y }`. Message: "This evidence isn't linked to any claim."
4. `UnansweredQuestionValidationShape` (Info, targetClass: ResearchQuestion) — status is "open" AND `NOT EXISTS { ?arg res:addresses $this }`. Message: "This research question has no arguments yet."

**Seed data trigger design (for validation rule verification):**
- Claim "RDF scales better than property graphs" has confidence "speculative" and NO evidence → fires UnsupportedClaimRule (**Wait — speculative is not in "established"/"supported"**. Need a separate trigger: a claim marked "supported" with no evidence, OR change the speculative claim to "supported"). The cleanest trigger: keep the 4th claim as speculative (which won't fire the rule) AND add the 2nd claim "Knowledge graphs reduce information silos" as "supported" — then ensure it has no `res:supports` evidence in seed data. But the design doc says evidence #2 supports it. **Better approach:** don't link any evidence to claim #4 "RDF scales" and set its confidence to "supported" instead of "speculative". Or add a 5th claim trigger object with confidence "established" and no evidence. The design doc's 4th claim is "speculative" — the rule only fires for "established" or "supported". **Decision: change the 4th claim's confidence to "supported" for trigger purposes, or add a dedicated trigger object.** Using a dedicated trigger is cleaner — keeps the seed data realistic while ensuring the rule fires.
- The "contested" claim (#3, PKM failure) has both supporting evidence (#3) and refuting evidence (#4) → fires ContestedClaimDetection ✓
- Need one orphan evidence object (no `supports`/`refutes` link) → add a 5th evidence trigger object
- ResearchQuestion has status "open" → fires UnansweredQuestionRule only if no arguments link to it. But the design doc's argument addresses this question. **Decision:** either (a) create a 2nd research question with no arguments, or (b) don't link the argument to the question in seed data. Option (a) is cleaner — keeps the happy-path data realistic.

**Updated trigger plan:**
- Add 5th claim: some "supported" claim with no evidence linked → fires UnsupportedClaim
- Claim #3 (PKM failure, contested) has both supporting + refuting evidence → fires ContestedClaim
- Add 5th evidence: an orphan evidence not linked to any claim → fires OrphanEvidence
- Add 2nd research question (status "open", no arguments) → fires UnansweredQuestion

**Seed totals:** 3 papers + 5 claims + 5 evidence + 2 research questions + 1 argument = 16 objects

**Icon manifest (from design doc):**
| Type | Icon | Color |
|------|------|-------|
| res:Paper | file-text | #6366f1 (indigo) |
| res:Claim | message-square-quote | #f59e0b (amber) |
| res:Evidence | flask-conical | #10b981 (emerald) |
| res:ResearchQuestion | help-circle | #ef4444 (red) |
| res:Argument | scale | #8b5cf6 (violet) |

Note: `file-text` is already used by basic-pkm Note. This is fine — different models can share Lucide icon names; the color differentiates them.

### Build Order

**Task 1: Manifest + Ontology (~15 min)**
Create `manifest.yaml` (copy CRM structure, adapt for 5 types, 5 icons) and `ontology/research.jsonld` (5 OWL classes, ~40 properties, 6 inverseOf pairs). Verify: `rdflib.Graph().parse()` succeeds with ≥150 triples.

**Task 2: Shapes + Views (~20 min)**
Create `shapes/research.jsonld` (5 NodeShapes, ~20 PropertyGroups, 5 enums, editHelpText) and `views/research.jsonld` (5 ViewSpecs + 5 SavedQueries). Verify: rdflib parse with ≥350 shape triples and ≥80 view triples.

**Task 3: Rules + Seed + Full Validation (~25 min)**
Create `rules/research.ttl` (4 validation SPARQLConstraints on separate NodeShapes per D153) and `seed/research.jsonld` (16 seed objects with trigger data). Run full pipeline: `parse_manifest()` + `load_archive()` + `validate_archive()` → 0 errors. Run pyshacl validation → conforms=False with exactly 4 violations at correct severities (2 Warning + 2 Info).

### Verification Approach

**Per-file parse (T1, T2):**
```bash
cd backend && .venv/bin/python3 -c "
from rdflib import Graph
g = Graph().parse('../models/research/ontology/research.jsonld', format='json-ld')
print(f'Ontology triples: {len(g)}')
"
```

**Full pipeline validation (T3):**
```bash
cd backend && .venv/bin/python3 -c "
from pathlib import Path
from app.models.manifest import parse_manifest
from app.models.loader import load_archive
from app.models.validator import validate_archive
m = parse_manifest(Path('../models/research'))
a = load_archive(Path('../models/research'), m)
r = validate_archive(a)
print(f'Valid: {r.is_valid}, Errors: {len(r.errors)}, Warnings: {len(r.warnings)}')
for e in r.errors: print(f'  E: {e.file}: {e.message}')
"
```

**SHACL-AF validation (T3):**
```bash
cd backend && .venv/bin/python3 -c "
from rdflib import Graph
import pyshacl
data = Graph().parse('../models/research/seed/research.jsonld', format='json-ld')
shapes = Graph().parse('../models/research/shapes/research.jsonld', format='json-ld')
rules = Graph().parse('../models/research/rules/research.ttl', format='turtle')
ontology = Graph().parse('../models/research/ontology/research.jsonld', format='json-ld')
combined_shapes = shapes + rules
conforms, results_graph, text = pyshacl.validate(
    data, shacl_graph=combined_shapes, ont_graph=ontology, advanced=True
)
print(f'Conforms: {conforms}')
print(text[:1000])
"
```

Expected: conforms=False with 4 violations:
1. Warning — UnsupportedClaimValidationShape on the trigger claim
2. Info — ContestedClaimValidationShape on "PKM failure" claim
3. Warning — OrphanEvidenceValidationShape on the orphan evidence
4. Info — UnansweredQuestionValidationShape on the trigger question

**Triple count sanity checks:**
- Ontology ≥ 150 triples (5 classes × ~30 triples each)
- Shapes ≥ 350 triples (5 NodeShapes × ~70 triples each)
- Views ≥ 80 triples (10 ViewSpec/SavedQuery entries)
- Rules ≥ 30 triples (4 validation shapes)
- Seed ≥ 120 triples (16 objects × ~8 triples each)

## Constraints

- **Subject IRIs must use `urn:sempkm:model:research:`** — validator rejects subjects from other namespaces (gist, bpkm, etc.). gist classes appear only as objects in `rdfs:subClassOf`.
- **No remote @context URLs in JSON-LD** — all contexts must be inline. Docker isolation prevents HTTP fetches.
- **Full IRIs in SPARQL queries** — ViewSpec and SavedQuery SPARQL strings must use `<urn:sempkm:model:research:...>` not `res:...`.
- **`sh:in` must use `@list` in JSON-LD** — `"sh:in": { "@list": [...] }` not `"sh:in": [...]`.
- **`sh:severity` on NodeShape, not SPARQLConstraint** — per D153 and pyshacl behavior.
- **Separate NodeShapes for each validation rule** — per D153, do not mix inference and validation on one shape.
- **Seed data both sides of inverseOf pairs** — per D154, pre-populate forward and inverse in seed data.
- **dcterms:created in seed data must match SHACL shape datatype** — per K002. If shapes declare `sh:datatype xsd:date` for a date field, seed must use `xsd:date` not `xsd:dateTime`.

## Common Pitfalls

- **UnsupportedClaimRule must check confidence value** — The rule only fires for "established" or "supported" confidence, not for all claims without evidence. The SPARQL needs `FILTER(?confidence IN ("established", "supported"))` before the `NOT EXISTS` check. Without this filter, every claim without evidence fires the warning — including speculative claims where lack of evidence is expected.
- **ContestedClaimDetection uses EXISTS (not NOT EXISTS)** — This is the inverse pattern from the other rules. It fires when evidence IS present on both sides, not when something is missing. The SPARQL needs `EXISTS { ?e1 res:supports $this }` AND `EXISTS { ?e2 res:refutes $this }`.
- **`res:year` uses `xsd:gYear` not `xsd:string`** — This is a typed year literal. In seed data, use `{"@value": "2001", "@type": "xsd:gYear"}`. The SHACL shape must declare `sh:datatype xsd:gYear`. rdflib handles gYear correctly.
- **`res:doi` uses `xsd:anyURI` not `xsd:string`** — In seed data, use `{"@value": "https://doi.org/...", "@type": "xsd:anyURI"}`.
- **Claim→Claim self-referencing properties** — `res:corroborates`, `res:contradicts`, `res:dependsOn` all have the same domain and range (Claim). In the shapes, these need `"sh:class": {"@id": "res:Claim"}` and `"sh:nodeKind": {"@id": "sh:IRI"}`.

## Sources

- Design doc: `.gsd/design/MENTAL-MODELS-EXPANSION-DESIGN.md` §4 (Research Workflow, lines 692-880)
- S02 Summary: `.gsd/milestones/M011/slices/S02/S02-SUMMARY.md` (CRM model — structural template)
- S03 Summary: `.gsd/milestones/M011/slices/S03/S03-SUMMARY.md` (Zettelkasten model — validation rule patterns)
- K001 lesson: rdflib SPARQL date arithmetic limitation (not applicable to S04 — no date rules needed)
- K002 lesson: seed data `@type` must match SHACL `sh:datatype` (applies to `res:year` xsd:gYear and any date fields)
- D153: Validation rules on separate NodeShapes with sh:severity on parent
- D154: Seed data pre-populates both sides of inverseOf pairs
