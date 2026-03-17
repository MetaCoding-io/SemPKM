# M011: Mental Models Expansion

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

Expand the Mental Model lineup from 3 user-facing models (basic-pkm, ppv, gist) to 6 by shipping basic-pkm v2 (Task + Milestone + Event types), Personal CRM, Zettelkasten+, and Research Workflow. Each model includes OWL ontology, SHACL shapes with editHelpText, ViewSpecs (table/cards/graph), SHACL-AF rules, seed data, pre-built dashboards, and icon manifest entries. The models are pure `.sempkm-model` archives — no platform code changes required.

## Why This Milestone

SemPKM's conversion story depends on covering enough workflows that new users find an immediate "aha moment." Two user-facing models (basic-pkm, ppv) is thin — users must create their own types before doing anything beyond basic notes and goals. Shipping 4 additional models/upgrades means:

- **basic-pkm v2** — Tasks and calendar events make SemPKM a daily operational hub, not just a note store. Tasks designed as a semantic hub for future provider sync (M016+).
- **Personal CRM** — Notion users' #1 template search. Strongest typed-relationship demo (Contact → Company → Deal pipeline).
- **Zettelkasten+** — Obsidian power users' favorite methodology. Enforced note types with provenance chains from source to permanent ideas.
- **Research Workflow** — Strongest differentiator for academics. Claims-first PKM with evidence tracking and argument construction.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Install basic-pkm v2 and immediately create Tasks with status/priority/due dates, Milestones grouping tasks, and Events with start/end times and attendees
- Install Personal CRM and track Contacts, Companies, Interactions, and Deals with a pre-built pipeline dashboard
- Install Zettelkasten+ and follow the enforced FleetingNote → Source → LiteratureNote → PermanentNote → StructureNote methodology with argumentation links (supports/contradicts/followsFrom)
- Install Research Workflow and manage Papers, Claims with confidence levels, Evidence (supporting/refuting), Research Questions, and Arguments
- See SHACL validation warnings for overdue tasks, stale contacts, unprocessed fleeting notes, unsupported claims
- Browse pre-built dashboards for each model (Task Hub, CRM Overview, Zettelkasten Workbench, Research Command Center)
- Query cross-model relationships (a Research Paper linked to a CRM Contact who is the author)

### Entry point / environment

- Entry point: Admin > Mental Models > Install, then workspace for object creation
- Environment: Docker Compose (api + triplestore + frontend/nginx)
- Live dependencies involved: RDF4J triplestore

## Completion Class

- Contract complete means: all 4 model archives pass manifest validation, install cleanly, generate correct SHACL forms, views render, seed data creates valid objects, SHACL-AF rules fire correctly
- Integration complete means: cross-model relationships work (CRM Contact linked to basic-pkm Project), generic views show objects from new models, dashboards render with real data, inference materializes inverse properties
- Operational complete means: models survive Docker restart, refresh_artifacts works on each model, uninstall is clean

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User installs all 4 models, creates at least one object of each type, and sees correct forms with helptext
- Task with dueDate in the past and status "todo" shows overdue warning in lint panel
- Zettelkasten provenance chain query returns Source → LiteratureNote → PermanentNote path
- Research Workflow "Unsupported Claims" saved query returns claims with no evidence
- CRM dashboard renders with real Contact/Interaction/Deal data
- Cross-model edge (e.g., Research Paper → CRM Contact) creates and displays correctly

## Risks and Unknowns

- **SHACL-AF rule complexity** — Rules like "stale contact (no interaction in 90 days)" require date arithmetic in SPARQL. pyshacl supports SPARQLRule but complex date filters may have performance implications.
- **Model interdependency** — Cross-model edges (CRM Contact → basic-pkm Project) require both models installed. Models must work standalone but link when co-installed.
- **basic-pkm v2 migration** — Upgrading from v1.3 to v2.0 is additive-only (new types, no changes to existing). Deployable via `refresh_artifacts`. But existing seed data won't include the new Task/Milestone/Event seeds.
- **Seed data volume** — 4 models × ~10-20 seed objects each could take noticeable time to install. Batch INSERT DATA should handle it.

## Existing Codebase / Prior Art

- `models/basic-pkm/` — Current v1.3 model (4 types: Project, Person, Note, Concept)
- `models/ppv/` — PPV model (11 types) — reference for complex model structure
- `backend/app/services/models.py` — ModelService.install()/remove()/refresh_artifacts()
- `backend/app/models/manifest.py` — ManifestSchema validation
- `.gsd/design/MENTAL-MODELS-EXPANSION-DESIGN.md` — Full design with all type definitions, shapes, views, rules, seed data, and icon manifests
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` — Task/Event field mapping for future sync apps (validates schema design)
- Research branch `origin/claude/user-conversion-strategy-NGB0C` — Prototype model files (Personal CRM, Zettelkasten+, Research Workflow)

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- New requirements to be created: MODEL-01 (basic-pkm v2 with Task/Milestone/Event), MODEL-02 (Personal CRM), MODEL-03 (Zettelkasten+), MODEL-04 (Research Workflow)

## Scope

### In Scope

- basic-pkm v2.0: Task, Milestone, Event types with full shapes, views, rules, seed data, icons
- Personal CRM: Contact, Company, Interaction, Deal types with pipeline dashboard
- Zettelkasten+: FleetingNote, Source, LiteratureNote, PermanentNote, StructureNote with argumentation links
- Research Workflow: Paper, Claim, Evidence, ResearchQuestion, Argument with evidence map
- SHACL-AF validation rules for each model (overdue tasks, stale contacts, unprocessed notes, unsupported claims)
- Pre-built dashboards for each model
- Saved queries per model
- Gist alignment (rdfs:subClassOf) for all new types
- Icon manifest entries with Lucide icons and colors
- editHelpText on key properties

### Out of Scope / Non-Goals

- Provider sync apps (M016-M024 — separate milestones)
- Browser extension integration (M014-M015)
- Model marketplace infrastructure
- Premium/free model tiering
- Model migration framework (refresh_artifacts is sufficient for additive changes)

## Technical Constraints

- Models are `.sempkm-model` archives: manifest.yaml + ontology/ + shapes/ + views/ + rules/ + seed/ directories
- All ontology in JSON-LD format
- SHACL shapes in JSON-LD with PropertyGroups
- Views as JSON-LD ViewSpec definitions
- Rules in Turtle format (SHACL-AF SPARQLRule/TripleRule)
- Seed data as JSON-LD
- Must pass existing ManifestSchema validation
- Must work with existing form generation, view rendering, and inference pipelines

## Integration Points

- **ManifestSchema** — All models validated at install time
- **ShapesService** — SHACL forms auto-generated from shapes
- **ViewSpecService** — Views registered and rendered
- **InferenceService** — OWL inverseOf and SHACL-AF rules executed
- **ValidationService** — SHACL validation rules fire and show in lint panel
- **IconService** — Lucide icons from manifest
- **DashboardService** — Pre-built dashboards (if model can declare them)
- **Generic Views** — New types appear in Table/Cards/Graph generic views with SHACL-driven columns

## Open Questions

- **Pre-built dashboards in model archives** — DashboardSpec is currently SQLite JSON (D105). Models can't declare dashboards in their archives yet. Options: (a) seed dashboards via a migration script post-install, (b) add dashboard support to model manifest, (c) ship dashboard specs as documentation/templates. Current thinking: defer dashboard bundling, document recommended dashboard configs in model README.
- **Event recurrence** — The RRULE field for calendar events is complex. Should the SHACL form show a human-friendly recurrence picker, or just a text input? Current thinking: text input with editHelpText for v1, better UX later.
