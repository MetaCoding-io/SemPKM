---
phase: quick-002
plan: 01
subsystem: ontology/research
tags: [gist, ontology, mental-models, research, rdf, owl]
dependency-graph:
  requires: []
  provides: [gist-ontology-research]
  affects: [basic-pkm-model, future-mental-models]
tech-stack:
  added: []
  patterns: [rdfs:subClassOf alignment without owl:imports, gist:KnowledgeConcept for concepts, gist:Task for projects]
key-files:
  created:
    - .planning/quick/2-research-how-the-gist-ontology-can-be-us/gist-ontology-research.md
  modified: []
decisions:
  - "Use rdfs:subClassOf alignment without gist owl:imports -- SHACL-only approach works without OWL inference"
  - "bpkm:Project should align to gist:Task not gist:Project (gist:Project requires sub-tasks per formal OWL definition)"
  - "gist:KnowledgeConcept (new v14) is the best alignment target for bpkm:Concept"
  - "Replace bpkm:tags string property with gist:Tag instances for graph connectivity"
metrics:
  duration: 15min
  completed: 2026-02-24
  tasks: 1
  files: 1
---

# Quick Task 002: gist Ontology Research Summary

## One-liner

gist 14.0.0 (CC BY 4.0) provides ready-made vocabulary for SemPKM Mental Models via rdfs:subClassOf alignment — primarily gist:Task for projects, gist:KnowledgeConcept for concepts, and gist:Person/Organization for agent models.

## What Was Researched

Fetched and analyzed the gist foundational ontology from Semantic Arts GitHub:
- `gistCore.ttl` (develop branch, v14.0.0) — all 96 OWL classes, 60+ properties
- v14.0.0 release notes — major breaking changes and new additions
- README — design philosophy, license, community info
- gist style guide — namespace conventions, OWL best practices
- Current SemPKM Basic PKM ontology (`models/basic-pkm/ontology/basic-pkm.jsonld`) for comparison

## Key Findings

### What gist Is
- Minimalist enterprise upper ontology: 96 classes, ~60 properties, single file (`gistCore.ttl`)
- Version 14.0.0 (Oct 2025), CC BY 4.0 license
- Namespace: `https://w3id.org/semanticarts/ns/ontology/gist/`
- OWL 2 DL; uses complex equivalence axioms requiring reasoner for full inference
- Active community with bi-monthly meetings, bi-annual releases

### Most Relevant Classes for SemPKM
| gist class | SemPKM use case |
|-----------|----------------|
| `gist:Task` | bpkm:Project alignment target |
| `gist:Project` | Task with sub-tasks (stricter than bpkm:Project) |
| `gist:ScheduledTask` | Future task-tracker with due dates |
| `gist:Person`, `gist:Organization` | Contacts Mental Model |
| `gist:KnowledgeConcept` | bpkm:Concept alignment target (new in v14) |
| `gist:Tag` | Replacement for bpkm:tags string property |
| `gist:Text`, `gist:FormattedContent` | bpkm:Note alignment (Markdown content) |
| `gist:Assignment` | Person-to-task temporal assignment |
| `gist:TemporalRelation` | Time-bounded relationships |

### Integration Approach
- **Use alignment without import** (Option C): add `rdfs:subClassOf gist:SomeClass` to Mental Model ontologies without importing gistCore.ttl
- Works with SemPKM's SHACL-only approach — no OWL reasoner required
- RDFS inference in RDF4J handles subclass chain queries
- Defer gist as system-level shared ontology until SemPKM has a shared vocabulary layer feature

### License: Compatible
CC BY 4.0 requires attribution and forbids defining terms in the `gist:` namespace. Both constraints are easy to satisfy. Mental Models mint their own IRIs and point to gist via subclass annotations.

## Proposed gist-based Mental Models
1. **project-tracker** — `gist:Task` + `gist:Project` + `gist:ScheduledTask` + `gist:Assignment` for full task/project tracking
2. **contacts** — `gist:Person` + `gist:Organization` + `gist:TemporalRelation` for rich contact/relationship tracking
3. **knowledge-base** — `gist:KnowledgeConcept` + `gist:FormattedContent` + `gist:ControlledVocabulary` for structured knowledge management

## Immediate Action Items Identified

1. Add `rdfs:subClassOf gist:Task` to `bpkm:Project` in basic-pkm ontology (documentation-level, no functional change)
2. Add `rdfs:subClassOf gist:KnowledgeConcept` to `bpkm:Concept`
3. Plan migration of `bpkm:tags` from `xsd:string` to `gist:Tag` instances
4. Create "Project Tracker" Mental Model design using gist:Task vocabulary

## Deviations from Plan

None — plan executed exactly as written. All 6 required sections present in research document. Actual gist IRI references throughout (193 gist: occurrences).

## Self-Check: PASSED

- [x] `.planning/quick/2-research-how-the-gist-ontology-can-be-us/gist-ontology-research.md` exists (689 lines)
- [x] Document contains actual gist IRI references (193 occurrences of `gist:`)
- [x] All 6 sections present: What is gist, Core Concepts, Alignment, Potential Models, Integration, Recommendations
- [x] Recommendations are concrete and actionable with yes/no/maybe table
- [x] Task commit af5d5ef verified in git log
