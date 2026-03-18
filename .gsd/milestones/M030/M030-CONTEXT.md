# M030: Data Quality Linting & Lint UX

**Gathered:** 2026-03-17
**Status:** Queued — pending auto-mode execution

## Project Description

Three-part milestone that transforms SHACL validation from a structural correctness tool into a practical data hygiene system: (1) fix the production validation pipeline so existing and new SHACL-AF rules actually fire in the live app, (2) add 9 data quality rules across all 5 Mental Models that catch real-world data problems (comma-in-tags, empty bodies, orphan objects, stale projects, etc.), and (3) build a lint filter/dismiss system with saved presets so users control what they see in the lint panel.

## Why This Milestone

**Existing rules are broken in production.** The 11 SHACL-AF validation rules shipped in M011 (overdue tasks, stale contacts, unprocessed notes, unsupported claims, etc.) only fire in offline pytest tests. The production `ValidationService` loads only shapes graphs (not rules graphs) and doesn't pass `advanced=True` to pyshacl. Every SPARQLConstraint rule is inert in the live app. This must be fixed first — otherwise new rules suffer the same fate.

**Current linting is structural, not useful.** SHACL shapes enforce "does this object have the right field types" — which catches almost nothing in practice because the form generator already constrains input. Users need rules that catch real data problems: tags imported as comma-separated strings instead of individual values, notes with no body content, duplicate reference URLs on concepts, objects with no title that show as raw IRIs, knowledge graph nodes with zero connections.

**The lint panel has no filtering.** When rules produce dozens of results (especially after an Obsidian import of 900+ notes), users can't manage the noise. They need to suppress rule types they don't care about, dismiss individual findings, and save filter presets for different workflows.

## User-Visible Outcome

### When this milestone is complete, the user can:

- See existing M011 validation warnings (overdue tasks, stale contacts, etc.) actually firing in the lint panel — they were silently broken before
- See new data quality warnings: tags containing commas, objects with no title, notes/concepts with no body, duplicate URLs on same-type objects
- See new data quality info items: orphan objects with no connections, stale projects/goals not modified in 30+ days, concepts with no definition, research claims with no rationale, PPV action items not linked to the goal chain
- Suppress any rule type from the lint panel (e.g., hide all "empty body" results)
- Dismiss individual lint results on specific objects (e.g., "this note intentionally has no body")
- Save and switch between named lint filter presets (e.g., "Show only warnings", "Hide imported-data rules", "CRM only")
- Manage suppressed rules and dismissals from a dedicated lint settings UI (clear all, remove individual suppressions)

### Entry point / environment

- Entry point: `http://localhost:3000/workspace` (lint panel in bottom bar, lint dashboard at `/admin/lint`)
- Environment: Docker Compose (api + triplestore + frontend/nginx)
- Live dependencies involved: RDF4J triplestore, SQLite (lint filter/dismiss storage)

## Completion Class

- Contract complete means: `model_shapes_loader` includes rules graphs and passes `advanced=True`, all 9 new rules fire correctly in pyshacl against seed data, lint filter CRUD works, filter presets save and restore
- Integration complete means: rules fire in the live Docker stack after object edits, lint panel shows real results, filters actually hide results, presets restore correctly across sessions
- Operational complete means: validation performance remains acceptable with rules enabled (~2-5s for typical data volumes), dismissed results persist across Docker restarts

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User creates a task with a past due date and "todo" status — overdue warning appears in lint panel (proving pipeline fix works for existing M011 rules)
- User creates a note with a tag value "design, architecture" — comma-in-tags warning appears
- User creates a note with a title but no body — empty body info appears
- User suppresses the "empty body" rule type — all empty body results disappear from lint panel
- User dismisses a specific comma-in-tags warning on one object — that result disappears but other comma-in-tags warnings remain
- User saves a "Warnings Only" preset, switches to "All Results", switches back — preset restores correctly
- User opens lint settings and clears all suppressions — previously hidden results reappear

## Risks and Unknowns

- **Validation performance with rules enabled.** Adding `advanced=True` and loading rules graphs alongside shapes may increase validation time. With ~1000 objects and 20+ rules, pyshacl could take 5-15 seconds. Need to measure and possibly add an async indicator. Mitigation: rules already work in tests in <1s for seed data; real concern is at Ideaverse scale (900 objects).
- **SPARQL date arithmetic in rdflib.** K001 documents that rdflib doesn't support `xsd:dayTimeDuration` subtraction. The "stale project" rule (no modification in 30+ days) needs the same `STRDT(SUBSTR(STR(NOW()),1,10), xsd:date)` workaround used for overdue tasks, or a `NOT EXISTS` fallback. May need `dcterms:modified` comparison which has `xsd:dateTime` not `xsd:date` — need to verify the SPARQL comparison semantics.
- **Orphan object rule performance.** Checking "no incoming or outgoing edges" for every object requires a full graph scan with `NOT EXISTS` patterns. Could be expensive. May need to be a saved query rather than a SHACL rule, or run only on-demand.
- **Lint filter storage model.** Suppressions and dismissals need to persist per-user. SQLite (alongside auth/settings) is the natural choice, but the schema needs to handle both rule-type suppressions and per-object dismissals efficiently.
- **Cross-model comma-in-tags rule.** Tags use `bpkm:tags` (basic-pkm, crm, zettelkasten) and `schema:keywords` (some imports). The rule needs to catch commas in both predicates, which may require a cross-model validation shape or a shared shape in a common graph.

## Existing Codebase / Prior Art

- `backend/app/services/validation.py` — `ValidationService.validate()` calls `pyshacl.validate()` without `advanced=True`, only loads shapes graphs
- `backend/app/services/models.py` — `model_shapes_loader()` constructs FROM clauses for `:shapes` graphs only, not `:rules`
- `backend/app/main.py` — wires `shapes_loader` into `ValidationService`
- `backend/app/validation/queue.py` — `ValidationQueue` coalesces and dispatches validation runs
- `backend/app/validation/report.py` — `ValidationReport.from_pyshacl()` parses results
- `backend/app/templates/browser/lint/` — lint panel templates in workspace
- `backend/app/lint/` — lint dashboard and lint panel routes
- `models/*/rules/*.ttl` — existing inference + validation rules per model (11 SPARQLConstraint validation rules across 4 models, 0 in ppv)
- `backend/tests/test_basic_pkm_v2.py` — reference for how pyshacl tests load `archive.shapes + archive.rules` with `advanced=True`
- `backend/tests/test_cross_model_validation.py` — cross-model pyshacl validation tests
- `backend/app/commands/handlers/object_patch.py` — `split_tag_values()` and `is_tag_property()` for tag handling context

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- New requirements: LINT-08 through LINT-20 covering pipeline fix, 9 data quality rules, and lint filter system

## Scope

### In Scope

**Validation Pipeline Fix:**
- `model_shapes_loader()` (or a new `model_shapes_and_rules_loader()`) loads both `:shapes` AND `:rules` graphs
- `ValidationService.validate()` passes `advanced=True` to `pyshacl.validate()` so SPARQLConstraint rules fire
- Existing 11 M011 validation rules start working in production without modification
- Performance measurement and acceptable threshold documented

**Data Quality Rules (9 new rules across all 5 models):**

1. **Comma-in-tags** (Warning) — Tag value (`bpkm:tags` or `schema:keywords`) contains a comma, suggesting it was imported as a single string instead of being split into individual tags. Applicable to: basic-pkm, crm, zettelkasten (any type with tags).

2. **Empty body** (Info) — Object of a type that typically has content (`bpkm:Note`, `zk:FleetingNote`, `zk:LiteratureNote`, `zk:PermanentNote`, `zk:StructureNote`, `res:Paper`) has no `urn:sempkm:body` value. Gentle nudge, not a hard error.

3. **Duplicate URL on same type** (Info) — Two objects of the same `rdf:type` share the same `schema:url` or `dcterms:source` value. Possible duplicate or needs deduplication. Applicable to: basic-pkm (Person, Concept), zettelkasten (Source), research (Paper).

4. **Titleless objects** (Warning) — Object has no `dcterms:title`, `skos:prefLabel`, `foaf:name`, or `res:title` — will display as a raw IRI in the UI. Applicable to all models.

5. **Orphan objects** (Info) — Object has zero typed edges (incoming or outgoing) to other user objects. Not connected to anything in the knowledge graph. Applicable to all models. May need performance gating.

6. **Stale project/goal** (Info) — Project (`bpkm:Project`, `ppv:Project`) or goal (`ppv:ValueGoal`, `ppv:GoalOutcome`) with active status but `dcterms:modified` more than 30 days old. Applicable to: basic-pkm, ppv.

7. **PPV broken chain** (Warning) — ActionItem or Project not linked up to a GoalOutcome/Pillar. PPV methodology requires the full chain for alignment tracking. Applicable to: ppv only.

8. **Concept with no definition** (Info) — `bpkm:Concept` or SKOS concept has no `skos:definition` value. A concept that isn't defined is hard to use consistently. Applicable to: basic-pkm.

9. **Research claim with no rationale** (Info) — `res:Claim` has no `res:rationale` value. A claim without reasoning for why it's believed. Applicable to: research.

**Lint Filter System:**
- Suppress by rule type (hide all results matching a SHACL source shape IRI)
- Dismiss individual results (specific object × rule combination)
- Named filter presets: save current filter state as a named preset, switch between presets
- Lint settings UI for managing suppressions, dismissals, and presets (view, delete, clear all)
- Storage in SQLite per-user (alongside existing user preferences layer)
- Alembic migration for filter/preset tables
- Lint panel UI updates to show filter controls and suppression indicators

### Out of Scope / Non-Goals

- Auto-fix actions from the lint panel (e.g., "split these tags" button — separate feature)
- Custom user-defined lint rules (write-your-own SPARQL validation — separate feature)
- Severity override per rule (users can hide rules but not change their severity level)
- Lint webhooks or notifications (lint results are on-demand in the panel)
- Performance optimization of validation beyond ensuring acceptable response times

## Technical Constraints

- SHACL validation rules in Turtle format in model `rules/` directories
- pyshacl with `advanced=True` required for SPARQLConstraint execution
- SPARQL date arithmetic limited by rdflib (K001) — use `STRDT(SUBSTR(...)...)` pattern
- Cross-model rules (comma-in-tags, titleless, orphan) need to target types across multiple models — may require a shared validation shapes graph or rules that use broad `sh:targetNode` patterns
- Lint filter storage in SQLite (not RDF) — user preferences, not knowledge graph data
- Frontend: htmx + vanilla JS for filter UI

## Integration Points

- **ValidationService** — pipeline fix (load rules, pass advanced=True)
- **model_shapes_loader** — extended to include rules graphs
- **pyshacl** — validate() with advanced=True, allow_infos=True, allow_warnings=True
- **Lint panel** — UI updates for filter controls, suppression indicators
- **Lint dashboard** — `/admin/lint` updates for filter management
- **SQLite / Alembic** — new tables for suppressions, dismissals, presets
- **SettingsService** — lint presets may integrate with user settings infrastructure
- **Model rules/ directories** — new `.ttl` files for data quality rules per model

## Open Questions

- **Cross-model rule placement.** Rules like "titleless objects" and "orphan objects" apply to all models. Should they live in a `platform/rules/` directory (new concept) or be duplicated per model? A platform rules graph (`urn:sempkm:platform:rules`) loaded alongside model rules would be cleanest.
- **Orphan detection performance.** A NOT EXISTS pattern for "no edges" across the full graph could be expensive. May need to be a SavedQuery (on-demand) rather than a validation rule (runs on every edit). Or batch it on a longer interval.
- **Preset schema.** Should presets store a list of suppressed rule types (additive — start from "show all", suppress some) or a list of enabled rule types (restrictive — start from "show none", enable some)? Additive is simpler and more natural for the "hide the noisy ones" workflow.
