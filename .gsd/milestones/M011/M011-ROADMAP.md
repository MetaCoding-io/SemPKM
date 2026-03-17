# M011: Mental Models Expansion

**Vision:** Expand the Mental Model lineup from 3 user-facing models to 6+ by shipping basic-pkm v2 (Task + Milestone types), Personal CRM, Zettelkasten+, and Research Workflow — all as pure `.sempkm-model` archives requiring zero platform code changes.

## Success Criteria

- User installs basic-pkm v2 via refresh_artifacts and immediately sees Task and Milestone types in forms, explorer, and views alongside existing Project/Person/Note/Concept types
- User installs Personal CRM from scratch and creates Contact, Company, Interaction, and Deal objects with SHACL-generated forms showing correct property groups, enums, and helptext
- User installs Zettelkasten+ and creates the full provenance chain: FleetingNote → Source → LiteratureNote → PermanentNote → StructureNote with argumentation links (supports/contradicts/followsFrom)
- User installs Research Workflow and creates Paper, Claim, Evidence, ResearchQuestion, and Argument objects with confidence levels and evidence tracking
- SHACL validation fires warnings for: overdue tasks (due date in past + status "todo"), stale contacts (no interaction in 90 days), unprocessed fleeting notes (status "unprocessed" older than 7 days), unsupported claims (no evidence linked)
- Inference materializes inverse properties for all new owl:inverseOf declarations (e.g., Contact.worksAt ↔ Company.hasEmployee)
- All 4 models pass offline validation: `parse_manifest()` + `load_archive()` + `validate_archive()` return zero errors
- Table and Cards ViewSpecs render with seed data for each model; Graph views show relationship structure
- Saved queries per model return expected results (e.g., "Overdue Tasks", "Unprocessed Fleeting Notes", "Unsupported Claims")
- All new types have Lucide icon manifest entries with tree/tab/graph contexts

## Key Risks / Unknowns

- **SPARQL-based validation rules with date arithmetic** — Rules like "overdue task" and "stale contact (no interaction in 90 days)" require `sh:sparql` SPARQLConstraint with `NOW()` and date comparison. pyshacl 0.31.0 supports this with `advanced=True`, but the specific date filter patterns haven't been exercised in this codebase's models yet.
- **basic-pkm v2 refresh_artifacts upgrade path** — Adding types to an existing installed model via `refresh_artifacts` is additive-only. Ontology/shapes/views/rules graphs are replaced but seed graph is untouched. New seed objects won't appear — users must create Task/Milestone objects manually.
- **sh:severity placement on NodeShape vs SPARQLConstraint** — Research confirms severity must be on the parent NodeShape, not the constraint node. Incorrect placement causes pyshacl to report violations at wrong severity.

## Proof Strategy

- **SPARQL date validation** → retire in S01 by proving the overdue-task SPARQLConstraint fires correctly against seed data with past due dates via offline pyshacl validation
- **refresh_artifacts upgrade** → retire in S01 by proving basic-pkm v2 passes offline validation and the upgrade path preserves existing types while adding new ones
- **sh:severity placement** → retire in S01 by confirming validation warnings (not errors) appear in offline pyshacl output for the overdue task rule

## Verification Classes

- Contract verification: offline `parse_manifest()` + `load_archive()` + `validate_archive()` per model; offline pyshacl validate for SHACL-AF rules and SPARQLConstraint warnings; rdflib parse for JSON-LD/Turtle syntax
- Integration verification: Docker-based install/refresh → form rendering → view rendering → inference → validation lint panel (S05)
- Operational verification: models survive Docker restart; refresh_artifacts works for basic-pkm upgrade; uninstall is clean (S05)
- UAT / human verification: create one object of each type and verify form layout, helptext, and view rendering (S05)

## Milestone Definition of Done

This milestone is complete only when all are true:

- All 4 model slices (S01–S04) deliver archives that pass offline validation with zero errors
- All models install cleanly in Docker (basic-pkm via refresh, others via fresh install)
- SHACL forms render correct property groups, field types, enums, and helptext for every new type
- ViewSpecs (table/cards/graph) render with seed data for each model
- SHACL-AF inference materializes inverse properties for all new owl:inverseOf pairs
- SHACL validation warnings fire correctly for overdue tasks, stale contacts, unprocessed notes, unsupported claims
- Saved queries return expected results for each model
- Cross-model verification proves all 4 models coexist without conflicts
- E2E Playwright tests cover install + object creation + form rendering + view rendering per model
- User guide documents each model with type descriptions, relationship diagrams, and usage examples
- Success criteria are re-checked against live Docker behavior, not just offline artifacts

## Requirement Coverage

- Covers: MODEL-01 (basic-pkm v2), MODEL-02 (Personal CRM), MODEL-03 (Zettelkasten+), MODEL-04 (Research Workflow)
- Partially covers: none
- Leaves for later: Dashboard bundling in model archives (DashboardSpec is SQLite JSON per D105 — document recommended configs instead)
- Orphan risks: none

## Slices

- [x] **S01: basic-pkm v2 — Task & Milestone Types** `risk:high` `depends:[]`
  > After this: basic-pkm v2.0 archive with 6 types (Project, Person, Note, Concept + Task, Milestone) passes offline validation. Overdue-task SPARQLConstraint fires warning against seed data. Refresh_artifacts upgrade path proven offline.

- [ ] **S02: Personal CRM Model** `risk:medium` `depends:[]`
  > After this: crm model archive with 4 types (Contact, Company, Interaction, Deal) passes offline validation. Stale-contact SPARQLConstraint fires. Pipeline views defined. Seed data creates a realistic CRM scenario.

- [ ] **S03: Zettelkasten+ Model** `risk:medium` `depends:[]`
  > After this: zettelkasten model archive with 5 types (FleetingNote, Source, LiteratureNote, PermanentNote, StructureNote) passes offline validation. Provenance chain query works. Argumentation links (supports/contradicts/followsFrom) modeled.

- [ ] **S04: Research Workflow Model** `risk:medium` `depends:[]`
  > After this: research model archive with 5 types (Paper, Claim, Evidence, ResearchQuestion, Argument) passes offline validation. Unsupported-claims and contested-claims SPARQLConstraints fire. Evidence map graph view defined.

- [ ] **S05: Cross-Model Verification, E2E Tests & User Guide** `risk:low` `depends:[S01,S02,S03,S04]`
  > After this: All 4 models install in Docker, forms render, views work, inference fires, validation warnings appear. E2E Playwright tests prove the install + create + view cycle. User guide Chapter 31 documents all 4 models.

## Boundary Map

### S01 → S05

Produces:
- `models/basic-pkm/` — Updated v2.0 archive (6 files: manifest.yaml, ontology, shapes, views, rules, seed) with Task and Milestone types added to existing 4-type model
- Proven pattern for SPARQLConstraint with date arithmetic (overdue task rule)

Consumes:
- nothing (first slice, extends existing basic-pkm model)

### S02 → S05

Produces:
- `models/crm/` — New model archive (6 files) with Contact, Company, Interaction, Deal types
- Proven pattern for cross-model edge references via gist hierarchy (crm:Contact → gist:Person)

Consumes:
- nothing (independent of S01)

### S03 → S05

Produces:
- `models/zettelkasten/` — New model archive (6 files) with 5 note types and argumentation links
- Proven pattern for complex provenance chain SPARQL queries

Consumes:
- nothing (independent of S01, S02)

### S04 → S05

Produces:
- `models/research/` — New model archive (6 files) with 5 research types and evidence tracking
- Proven pattern for multi-constraint validation rules (unsupported + contested claims)

Consumes:
- nothing (independent of S01, S02, S03)

### S05 (final integration)

Produces:
- E2E Playwright tests proving Docker install + create + view cycle for all 4 models
- User guide Chapter 31 documenting all 4 models
- Cross-model verification results

Consumes:
- S01: basic-pkm v2.0 archive
- S02: CRM archive
- S03: Zettelkasten+ archive
- S04: Research Workflow archive
