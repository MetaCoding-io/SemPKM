---
id: T01
parent: S03
milestone: M011
provides:
  - Zettelkasten manifest.yaml with 5 icon entries and entailment_defaults
  - Zettelkasten OWL ontology with 5 classes, 25 properties, 3 inverseOf pairs, 4 argumentation links, 1 symmetric property
key_files:
  - models/zettelkasten/manifest.yaml
  - models/zettelkasten/ontology/zettelkasten.jsonld
key_decisions:
  - "namespace uses urn:sempkm:model:zettelkasten: (not urn:sempkm:model:zk:) — ManifestSchema validator enforces namespace == urn:sempkm:model:{modelId}:, so the zk: prefix is a JSON-LD shorthand only"
patterns_established:
  - Same icon definition pattern as CRM (tree/tab/graph contexts with size overrides)
  - Same inverseOf pattern as CRM (declared on both sides of each pair)
  - D155 broadening pattern applied: zk:body has no rdfs:domain (shared across 4 note types)
observability_surfaces:
  - "parse_manifest(Path('../models/zettelkasten')) — ValueError with structured message on failure"
  - "Graph().parse(ontology_path, format='json-ld') — 132 triples; <100 indicates missing definitions"
  - "Subject namespace check — all subjects must start with urn:sempkm:model:zettelkasten:"
duration: 12m
verification_result: passed
completed_at: 2026-03-17
blocker_discovered: false
---

# T01: Author Zettelkasten manifest and ontology

**Created Zettelkasten model manifest (5 icon entries, entailment_defaults) and OWL ontology (5 classes, 25 properties, 3 inverseOf pairs, 4 argumentation links, 1 symmetric property) — 132 triples, all namespace-compliant.**

## What Happened

Created two files for the Zettelkasten model archive:

1. **`models/zettelkasten/manifest.yaml`** — Model identity with `modelId: zettelkasten`, namespace `urn:sempkm:model:zettelkasten:`, 5 icon entries (zap/book-open/quote/gem/network) each with tree/tab/graph contexts, and entailment_defaults matching CRM pattern (owl_inverseOf + shacl_rules enabled).

2. **`models/zettelkasten/ontology/zettelkasten.jsonld`** — Full OWL ontology with inline @context (no remote contexts), containing:
   - 5 OWL classes aligned to gist (FleetingNote→FormattedContent, Source→Content, LiteratureNote/PermanentNote/StructureNote→FormattedContent)
   - 9 datatype properties (body, capturedFrom, sourceType, notes, rating, originalQuote, pageReference, sequenceId, purpose) — `zk:body` intentionally has no `rdfs:domain` per D155
   - 3 inverseOf pairs declared on both sides (derivedFrom↔hasLiteratureNote, developedInto↔developedFrom, includes↔includedInStructure)
   - 4 argumentation link properties (supports, contradicts, followsFrom, relatedTo)
   - 1 one-directional property (processedInto)
   - 1 symmetric property (relatedStructure)
   - `bpkm` prefix included in @context for tag reuse

Key deviation: the plan specified `namespace: "urn:sempkm:model:zk:"` but `ManifestSchema.validate_namespace()` enforces `namespace == urn:sempkm:model:{modelId}:`. With `modelId: zettelkasten`, the namespace must be `urn:sempkm:model:zettelkasten:`. The `zk:` prefix is a JSON-LD shorthand that maps to this full namespace.

## Verification

All task-level verification passed:

- `parse_manifest(Path('../models/zettelkasten'))` → Model: zettelkasten, Types: 5 — all 5 icons have tree/tab/graph contexts ✓
- Ontology parses to 132 triples (≥100 threshold) ✓
- Subject namespace check: all subjects in `urn:sempkm:model:zettelkasten:` namespace ✓
- 5 OWL classes with correct gist alignment ✓
- 3 inverseOf pairs declared on both sides ✓
- 4 argumentation link properties present ✓
- `zk:relatedStructure` is `owl:SymmetricProperty` ✓
- `zk:body` has no `rdfs:domain` ✓
- No remote @context in JSON-LD ✓
- Diagnostic failure path: `parse_manifest(Path('/tmp/nonexistent-model'))` raises `ValueError` with structured message ✓

Slice-level verification (partial — T01 only):
- Step 1 (individual file parse): ontology parses OK, other files not yet created (expected) ✓
- Step 4 (diagnostic): structured error reporting works ✓

## Diagnostics

- **Inspect manifest:** `cd backend && .venv/bin/python3 -c "from pathlib import Path; from app.models.manifest import parse_manifest; m = parse_manifest(Path('../models/zettelkasten')); print(m.modelId, len(m.icons))"`
- **Inspect ontology triples:** `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g = Graph().parse('../models/zettelkasten/ontology/zettelkasten.jsonld', format='json-ld'); print(len(g), 'triples')"`
- **Check namespace compliance:** `cd backend && .venv/bin/python3 -c "from rdflib import Graph; g = Graph().parse('../models/zettelkasten/ontology/zettelkasten.jsonld', format='json-ld'); bad = [str(s) for s in set(g.subjects()) if str(s).startswith('urn:sempkm:') and not str(s).startswith('urn:sempkm:model:zettelkasten:')]; print('CLEAN' if not bad else bad)"`

## Deviations

- **Namespace IRI:** Plan specified `namespace: "urn:sempkm:model:zk:"` and `prefixes: { zk: "urn:sempkm:model:zk:" }`. Changed to `namespace: "urn:sempkm:model:zettelkasten:"` and `prefixes: { zk: "urn:sempkm:model:zettelkasten:" }` because `ManifestSchema.validate_namespace()` enforces `namespace == urn:sempkm:model:{modelId}:`. The `zk:` shorthand prefix in JSON-LD maps to the full `urn:sempkm:model:zettelkasten:` namespace — functionally equivalent.

## Known Issues

None.

## Files Created/Modified

- `models/zettelkasten/manifest.yaml` — Zettelkasten model manifest with 5 icon entries and entailment_defaults
- `models/zettelkasten/ontology/zettelkasten.jsonld` — OWL ontology with 5 classes, 25 properties, 132 triples
- `.gsd/milestones/M011/slices/S03/S03-PLAN.md` — Added diagnostic failure-path check to Observability section (pre-flight fix)
- `.gsd/milestones/M011/slices/S03/tasks/T01-PLAN.md` — Added Observability Impact section (pre-flight fix)
