# M030: Data Quality Linting & Lint UX

**Vision:** Transform SHACL validation from a structural correctness tool into a practical data hygiene system — fix the broken production pipeline so existing rules fire, add 9 data quality rules that catch real-world problems, and build a lint filter/dismiss system so users control what they see.

## Success Criteria

- Existing M011 SHACL-AF validation rules (overdue tasks, stale contacts, unprocessed notes, etc.) fire in the live Docker stack lint panel — they were silently broken before
- User creates data with known quality issues (comma-in-tags, empty body, titleless objects) and sees appropriate warnings/info in the lint panel
- User can suppress an entire rule type from the lint panel — all results for that rule disappear
- User can dismiss a specific lint result on one object — that result disappears but other results for the same rule remain
- User can save a named lint filter preset, switch away, switch back — preset restores correctly
- User can manage suppressions, dismissals, and presets from a lint settings UI (clear all, remove individual items)

## Key Risks / Unknowns

- **Validation performance with rules enabled** — Adding `advanced=True` and loading rules graphs alongside shapes may increase validation time significantly with ~1000 objects and 20+ rules. Need to measure during S01.
- **Orphan object rule may be too expensive** — `NOT EXISTS` pattern for "no edges" requires scanning the entire graph. May need to be a SavedQuery rather than a validation rule.
- **Cross-model rule placement** — Rules like "titleless objects" and "orphan objects" apply to all models. Attaching them to basic-pkm works because it's always installed, but it's architecturally impure.

## Proof Strategy

- **Validation performance** → retire in S01 by measuring pyshacl execution time with `advanced=True` on real data and verifying acceptable response times (~2-5s)
- **Cross-model rules** → retire in S02 by placing cross-model rules in basic-pkm's rules file with broad target patterns and verifying they fire against objects from other models

## Verification Classes

- Contract verification: Offline pytest tests for each new SHACL rule, unit tests for filter CRUD, Alembic migration tests
- Integration verification: Docker stack proves rules fire in production, lint panel shows results, filters hide results, presets restore
- Operational verification: Validation performance remains acceptable with rules enabled, dismissed results persist across Docker restarts
- UAT / human verification: Final acceptance scenarios (create object → see warning → suppress → dismiss → preset save/restore)

## Milestone Definition of Done

This milestone is complete only when all are true:

- Pipeline fix deployed: `model_shapes_loader()` includes rules graphs and `ValidationService.validate()` passes `advanced=True`
- All 11 existing M011 validation rules fire in the live Docker stack (proven by creating an overdue task and seeing the warning)
- All 9 new data quality rules fire correctly in offline pyshacl tests against test data
- New rules fire in Docker stack after object creation/editing
- Lint filter CRUD works: suppress, dismiss, preset create/apply/delete via API
- Lint panel UI shows filter controls and suppression indicators
- Lint settings UI allows managing suppressions, dismissals, and presets
- E2E Playwright tests prove the full acceptance criteria (pipeline fix, new rules, filter system)
- User guide updated with lint filter documentation
- Final integrated acceptance scenarios pass against running Docker stack

## Requirement Coverage

- Covers: LINT-08 (pipeline fix), LINT-09 through LINT-17 (9 data quality rules), LINT-18 (suppress by rule type), LINT-19 (dismiss individual results), LINT-20 (named filter presets)
- Note: LINT-08 through LINT-20 are new requirements registered by this milestone

## Slices

- [x] **S01: Validation Pipeline Fix & Performance Measurement** `risk:high` `depends:[]`
  > After this: User creates a task with a past due date — the overdue-task warning from M011 appears in the lint panel for the first time in production. Performance measured and documented.

- [x] **S02: Data Quality Rules (9 new SHACL-AF rules)** `risk:medium` `depends:[S01]`
  > After this: User creates objects with data quality issues (comma-in-tags, empty body, titleless objects, etc.) and sees appropriate warnings/info in the lint panel. All 9 rules proven by offline pytest tests.

- [x] **S03: Lint Filter System (Suppress, Dismiss, Presets)** `risk:medium` `depends:[S01]`
  > After this: User can suppress rule types, dismiss individual results, save/restore named presets, and manage all filter state from a lint settings UI. Full CRUD with SQLite persistence.

- [ ] **S04: E2E Tests & User Guide** `risk:low` `depends:[S01,S02,S03]`
  > After this: Playwright tests prove the full acceptance criteria end-to-end against Docker stack. User guide chapter documents lint filtering workflow.

## Boundary Map

### S01 → S02

Produces:
- `model_shapes_loader()` returns both shapes AND rules graphs merged into one rdflib Graph
- `ValidationService.validate()` passes `advanced=True` to `pyshacl.validate()`
- Production pipeline proven: SPARQLConstraint rules fire and results appear in lint panel
- Performance measurement baseline documented

Consumes:
- nothing (first slice)

### S01 → S03

Produces:
- Same pipeline fix — lint panel now shows real validation results that need filtering
- `LintService` queries return results with `sh:sourceShape` IRI (the stable identifier used for suppression/dismissal)

Consumes:
- nothing (first slice)

### S02 → S04

Produces:
- 9 new `.ttl` rule files in `models/*/rules/` directories
- Offline pytest tests proving each rule fires correctly
- Rules produce results in Docker stack lint panel

Consumes:
- S01's pipeline fix (rules load and `advanced=True` is passed)

### S03 → S04

Produces:
- `lint_suppressions`, `lint_dismissals`, `lint_presets` SQLite tables (Alembic migration)
- API endpoints for suppress/dismiss/preset CRUD
- `LintService` extended with server-side Python filtering (excludes suppressed/dismissed results)
- Lint panel UI with filter controls, dismiss buttons, preset selector
- Lint settings page for managing suppressions/dismissals/presets

Consumes:
- S01's pipeline fix (lint panel shows real results to filter)
