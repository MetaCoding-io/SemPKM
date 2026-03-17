# S03: Zettelkasten+ Model — Research

**Date:** 2026-03-17
**Status:** Complete

## Summary

S03 is a **light research** slice — it follows the exact same 6-file model archive pattern proven by S01 (basic-pkm v2) and S02 (Personal CRM). The deliverable is a `models/zettelkasten/` directory with `manifest.yaml`, `ontology/zettelkasten.jsonld`, `shapes/zettelkasten.jsonld`, `views/zettelkasten.jsonld`, `rules/zettelkasten.ttl`, and `seed/zettelkasten.jsonld`. No platform code changes.

The design doc (§3, lines 487–685) specifies 5 types (FleetingNote, Source, LiteratureNote, PermanentNote, StructureNote), ~25 properties, 4 argumentation link types (supports/contradicts/followsFrom/relatedTo), 3 bidirectional owl:inverseOf pairs for the provenance chain, 3 validation rules, 5 ViewSpecs, and 4 SavedQueries. Estimated size: ~1800 lines across 6 files (comparable to CRM's 1225).

The one technical nuance is the "unprocessed fleeting note older than 7 days" validation rule — this requires date arithmetic that rdflib doesn't support (K001). Following the pattern established in D157 (CRM stale-contact), the SHACL-AF rule should use `NOT EXISTS { ?s zk:processedInto ?x }` (simple "unprocessed" check) and the SavedQuery "Unprocessed Fleeting Notes" handles the date-based filtering. The same `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` pattern works for date comparison in the SavedQuery.

## Recommendation

**Approach:** Build the 6 files sequentially following the CRM model as the structural template. The CRM archive (1225 lines, 4 types) is the closest reference — same namespace convention, same shapes/views/rules patterns, same verification pipeline.

**Build order:**
1. Manifest + ontology — establish namespace `urn:sempkm:model:zk:`, 5 OWL classes with gist alignment, all properties, owl:inverseOf declarations
2. Shapes + views — PropertyGroups per type, SHACL constraints, editHelpText; ViewSpecs (table/card/graph) and SavedQueries
3. Rules + seed data + offline validation — 3 SHACL-AF rules on separate NodeShapes, seed data with provenance chain scenario, both-side inverseOf pre-populated, run full validation pipeline

## Implementation Landscape

### Key Files

**Reference models (follow these patterns exactly):**
- `models/crm/manifest.yaml` — Latest manifest with icons (tree/tab/graph contexts), entailment_defaults
- `models/crm/ontology/crm.jsonld` — OWL classes + properties with gist alignment, owl:inverseOf pairs
- `models/crm/shapes/crm.jsonld` — SHACL shapes with PropertyGroups, `sh:in`, `sempkm:editHelpText`; namespace `"sempkm": "urn:sempkm:"`
- `models/crm/views/crm.jsonld` — ViewSpecs + SavedQueries; namespace `"sempkm": "urn:sempkm:vocab:"`
- `models/crm/rules/crm.ttl` — SHACL-AF inference + validation on separate NodeShapes (D153)
- `models/crm/seed/crm.jsonld` — Seed objects with both-side inverseOf, typed dates, trigger data

**Platform code (no changes, read-only reference):**
- `backend/app/models/manifest.py` — `parse_manifest()` Pydantic validation
- `backend/app/models/loader.py` — `load_archive()`, `load_rdf_file()`
- `backend/app/models/validator.py` — `validate_archive()`, `ALLOWED_EXTERNAL_NAMESPACES`

**Files to create (6 new files):**
- `models/zettelkasten/manifest.yaml`
- `models/zettelkasten/ontology/zettelkasten.jsonld`
- `models/zettelkasten/shapes/zettelkasten.jsonld`
- `models/zettelkasten/views/zettelkasten.jsonld`
- `models/zettelkasten/rules/zettelkasten.ttl`
- `models/zettelkasten/seed/zettelkasten.jsonld`

### Type & Property Inventory

**Namespace:** `urn:sempkm:model:zk:` (prefix `zk:`)

**5 Types with gist alignment:**
| Type | gist Parent | Notes |
|------|------------|-------|
| `zk:FleetingNote` | `gist:FormattedContent` | Raw captures, inbox items |
| `zk:Source` | `gist:Content` | Books, articles, papers consumed |
| `zk:LiteratureNote` | `gist:FormattedContent` | Summaries of others' ideas from a Source |
| `zk:PermanentNote` | `gist:FormattedContent` | Atomic ideas in user's own words |
| `zk:StructureNote` | `gist:FormattedContent` | Curated outlines organizing PermanentNotes |

**owl:inverseOf pairs (3):**
| Forward | Inverse | Between |
|---------|---------|---------|
| `zk:derivedFrom` | `zk:hasLiteratureNote` | LiteratureNote → Source / Source → LiteratureNote |
| `zk:developedInto` | `zk:developedFrom` | LiteratureNote → PermanentNote / PermanentNote → LiteratureNote |
| `zk:includes` | `zk:includedInStructure` | StructureNote → PermanentNote / PermanentNote → StructureNote |

**Argumentation links (directional, no inverses):**
- `zk:supports` (PermanentNote → PermanentNote)
- `zk:contradicts` (PermanentNote → PermanentNote)
- `zk:followsFrom` (PermanentNote → PermanentNote)
- `zk:relatedTo` (PermanentNote → PermanentNote)

**Other object properties:**
- `zk:processedInto` (FleetingNote → LiteratureNote or PermanentNote) — no inverse, one-directional
- `zk:relatedStructure` (StructureNote → StructureNote) — symmetric property

**Datatype properties by type:**
- FleetingNote: dcterms:title, zk:body, zk:capturedFrom, bpkm:tags
- Source: dcterms:title, dcterms:creator, zk:sourceType (sh:in 8 values), schema:datePublished, schema:url, zk:notes, zk:rating (xsd:integer 1-5), bpkm:tags
- LiteratureNote: dcterms:title, zk:body, zk:originalQuote, zk:pageReference, bpkm:tags
- PermanentNote: dcterms:title, zk:body, zk:sequenceId, bpkm:tags
- StructureNote: dcterms:title, zk:body, zk:purpose (sh:in 5 values), bpkm:tags

### SHACL-AF Rules (3 rules on 3 separate NodeShapes per D153)

**Rule 1 — UnprocessedFleetingValidation (Warning):**
- `sh:targetClass zk:FleetingNote`, `sh:severity sh:Warning`
- SPARQLConstraint: `NOT EXISTS { $this zk:processedInto ?x }`
- Message: "This fleeting note hasn't been processed. Develop it into a literature or permanent note, or delete it."
- Note: No 7-day check in SHACL rule (K001 — rdflib can't do date arithmetic). SavedQuery handles the age filter.

**Rule 2 — OrphanPermanentNoteValidation (Warning):**
- `sh:targetClass zk:PermanentNote`, `sh:severity sh:Warning`
- SPARQLConstraint: `NOT EXISTS { $this zk:supports|zk:contradicts|zk:followsFrom|zk:includedInStructure ?x }`
- Message: "This permanent note is isolated. Connect it to other ideas or include it in a structure note."
- Implementation note: Use separate FILTER NOT EXISTS for each predicate (rdflib SPARQL property paths in NOT EXISTS can be unpredictable — use explicit UNION or separate checks).

**Rule 3 — UnsourcedPermanentNoteValidation (Info):**
- `sh:targetClass zk:PermanentNote`, `sh:severity sh:Info`
- SPARQLConstraint: `NOT EXISTS { $this zk:developedFrom ?x }`
- Message: "This idea has no literature source. Consider linking it to supporting evidence."
- Note: Design says `sh:Info` severity, not Warning — less urgent than the others.

**No inference rules needed** — all relationships are user-created, not derived. The owl:inverseOf entailment handles inverse property materialization automatically.

### ViewSpecs (5 views + 4 saved queries from design doc)

**Views:**
1. `zk:view-fleeting-table` — FleetingNote inbox table (title, created, processedInto status)
2. `zk:view-source-table` — Source library table (title, creator, sourceType, datePublished)
3. `zk:view-litnote-card` — LiteratureNote cards grouped by source (title, body excerpt, source)
4. `zk:view-zettelkasten-graph` — PermanentNote graph with supports/contradicts/followsFrom edges (CONSTRUCT)
5. `zk:view-structure-table` — StructureNote list (title, purpose, included note count)

**SavedQueries:**
1. "Unprocessed Fleeting Notes" — FleetingNotes older than 3 days with no processedInto. Uses `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` for date comparison of dcterms:created.
2. "Isolated Permanent Notes" — PermanentNotes with no argumentation links
3. "Contradiction Map" — PermanentNote pairs connected by `contradicts`
4. "Provenance Chain" — CONSTRUCT showing Source → LiteratureNote → PermanentNote chain

### Seed Data Scenario

From design doc, ~10 seed objects forming a complete provenance chain:

**Sources (3):** "How to Take Smart Notes" (Ahrens, book, 2017), "The Art of Thinking Clearly" (Dobelli, book, 2013), "Networked Thought" (article, 2024)

**FleetingNotes (2):** One unprocessed (3+ days old, trigger for validation), one recently captured

**LiteratureNotes (3):** Two from Ahrens, one from Dobelli — each `derivedFrom` a Source

**PermanentNotes (3):** "Externalized thinking reduces cognitive load" (supports next), "Structure emerges from connections, not planning" (developed from Ahrens lit note), "Confirmation bias threatens knowledge systems" (contradicts uncritical note-taking, from Dobelli)

**StructureNote (1):** "The Case for Structured Note-Taking" (includes all 3 permanent notes, purpose: argument)

**Trigger data for validation:**
- FleetingNote with old `dcterms:created` and no `processedInto` → fires UnprocessedFleetingValidation
- One PermanentNote deliberately left without any argumentation links → fires OrphanPermanentNoteValidation
- One PermanentNote without `developedFrom` → fires UnsourcedPermanentNoteValidation (Info)

**Both sides of inverseOf pre-populated per D154:**
- LiteratureNote.derivedFrom → Source AND Source.hasLiteratureNote → LiteratureNote
- LiteratureNote.developedInto → PermanentNote AND PermanentNote.developedFrom → LiteratureNote
- StructureNote.includes → PermanentNote AND PermanentNote.includedInStructure → StructureNote

### Icons

From design doc, all standard Lucide icons (verified available in Lucide 0.575.0):
| Type | Icon | Color | Rationale |
|------|------|-------|-----------|
| FleetingNote | `zap` | `#f59e0b` (amber) | Ephemeral, attention-grabbing |
| Source | `book-open` | `#6366f1` (indigo) | Reference material |
| LiteratureNote | `quote` | `#8b5cf6` (violet) | Derived from source |
| PermanentNote | `gem` | `#10b981` (emerald) | The valuable output |
| StructureNote | `network` | `#0ea5e9` (sky blue) | Organizational |

### Build Order

1. **Manifest + ontology** — Create manifest.yaml (modelId: zettelkasten, namespace urn:sempkm:model:zk:, 5 icon entries). Create ontology with 5 classes, ~15 datatype properties, ~10 object properties, 3 inverseOf pairs, 1 symmetric property (relatedStructure). This unblocks everything else.

2. **Shapes + views** — Create shapes with PropertyGroups per type (FleetingNote: 2 groups; Source: 3 groups; LiteratureNote: 3 groups; PermanentNote: 3 groups; StructureNote: 3 groups). Create views with 5 ViewSpecs and 4 SavedQueries. Critical: shapes use `"sempkm": "urn:sempkm:"`, views use `"sempkm": "urn:sempkm:vocab:"`.

3. **Rules + seed data + validation** — Create 3 SHACL-AF rules in Turtle. Create seed data with ~12 objects forming the provenance chain. Run `parse_manifest()` + `load_archive()` + `validate_archive()` to confirm zero errors. Run `pyshacl.validate(advanced=True)` to confirm all 3 validation rules fire.

### Verification Approach

**Step 1 — Individual file parse (per file):**
```bash
cd backend && .venv/bin/python3 -c "
from rdflib import Graph
g = Graph().parse('../models/zettelkasten/{file}', format='{format}')
print(f'Triples: {len(g)}')
"
```

**Step 2 — Full pipeline validation:**
```bash
cd backend && .venv/bin/python3 -c "
from pathlib import Path
from app.models.manifest import parse_manifest
from app.models.loader import load_archive
from app.models.validator import validate_archive
m = parse_manifest(Path('../models/zettelkasten'))
a = load_archive(Path('../models/zettelkasten'), m)
r = validate_archive(a)
print(f'Valid: {r.is_valid}, Errors: {len(r.errors)}, Warnings: {len(r.warnings)}')
for e in r.errors: print(f'  E: {e.file}: {e.message}')
"
```

**Step 3 — SHACL-AF validation rules fire:**
```bash
cd backend && .venv/bin/python3 -c "
from rdflib import Graph
import pyshacl
shapes = Graph().parse('../models/zettelkasten/shapes/zettelkasten.jsonld', format='json-ld')
rules = Graph().parse('../models/zettelkasten/rules/zettelkasten.ttl', format='turtle')
seed = Graph().parse('../models/zettelkasten/seed/zettelkasten.jsonld', format='json-ld')
onto = Graph().parse('../models/zettelkasten/ontology/zettelkasten.jsonld', format='json-ld')
shacl = shapes + rules
conforms, _, text = pyshacl.validate(seed, shacl_graph=shacl, ont_graph=onto, advanced=True)
print(text[:2000])
# Expect conforms=False with 3 violations: UnprocessedFleeting (Warning), OrphanPermanentNote (Warning), UnsourcedPermanentNote (Info)
"
```

**Step 4 — Triple count sanity:**
- Ontology: ≥100 triples (5 classes, ~25 properties)
- Shapes: ≥300 triples (5 NodeShapes with PropertyGroups)
- Views: ≥60 triples (5 ViewSpecs + 4 SavedQueries)
- Rules: ≥20 triples (3 NodeShapes)
- Seed: ≥100 triples (~12 objects with relationships)

## Constraints

- **Subject IRIs must use `urn:sempkm:model:zk:` namespace** — validator checks all subjects start with model namespace or allowed external namespaces (w3.org, purl.org/dc, schema.org, xmlns.com/foaf).
- **No remote @context in JSON-LD** — all prefixes inline in each file.
- **Full IRIs in SPARQL query strings** — ViewSpec and SavedQuery SPARQL cannot use prefixed names.
- **Shapes use `"sempkm": "urn:sempkm:"`, views use `"sempkm": "urn:sempkm:vocab:"`** — mixing causes runtime failures (proven in S01/S02 forward intelligence).
- **sh:severity goes on NodeShape, not SPARQLConstraint** (D153).
- **Validation and inference rules on separate NodeShapes** (D153).
- **`sh:in` must use `@list` in JSON-LD** — `{ "@list": ["a", "b"] }` not `["a", "b"]`.
- **Both sides of owl:inverseOf pre-populated in seed data** (D154).
- **Date arithmetic not available in rdflib SPARQL** (K001) — use NOT EXISTS for presence checks, SavedQueries for date-based filtering.

## Common Pitfalls

- **`zk:body` property domain** — Multiple types (FleetingNote, LiteratureNote, PermanentNote, StructureNote) share `zk:body`. Do NOT declare `rdfs:domain` on this property (same broadening pattern as D155 for bpkm:priority and bpkm:body). Let SHACL shapes constrain which types display it.
- **`bpkm:tags` prefix in ontology @context** — Seed data uses `bpkm:tags` for tagging. Include `"bpkm": "urn:sempkm:model:basic-pkm:"` in ontology and seed @context so the property IRI resolves correctly (proven pattern from CRM).
- **OrphanPermanentNote SPARQL** — Testing `NOT EXISTS` with multiple alternative predicates. Don't use property paths (`zk:supports|zk:contradicts`) in NOT EXISTS — rdflib support is inconsistent. Instead use explicit separate NOT EXISTS blocks: `FILTER NOT EXISTS { $this zk:supports ?x } FILTER NOT EXISTS { $this zk:contradicts ?x } ...` etc.
- **Seed data trigger objects** — Need at least one FleetingNote without `processedInto`, one PermanentNote without argumentation links, and one PermanentNote without `developedFrom` to fire all 3 validation rules.
- **dcterms:created on FleetingNote seed** — For the "unprocessed" SavedQuery to return results, the old fleeting note needs `dcterms:created` set to a date at least 3 days in the past. Use a fixed past date (e.g., `2026-03-12T09:00:00Z`) not a relative date.

## Sources

- Design doc: `.gsd/design/MENTAL-MODELS-EXPANSION-DESIGN.md` §3 (lines 487–685) — complete type definitions, property tables, views, rules, seed data, icons
- CRM model (S02): `models/crm/` (worktree) — structural template, 1225 lines across 6 files
- basic-pkm model (S01): `models/basic-pkm/` — date comparison pattern, upgrade pattern reference
- K001 (KNOWLEDGE.md): rdflib SPARQL engine does not support xsd:dayTimeDuration subtraction
- D153 (DECISIONS.md): Validation rules on separate NodeShapes with sh:severity on NodeShape
- D154 (DECISIONS.md): Seed data pre-populates both sides of owl:inverseOf pairs
- D157 (DECISIONS.md): NOT EXISTS pattern for SHACL rules when date arithmetic needed
