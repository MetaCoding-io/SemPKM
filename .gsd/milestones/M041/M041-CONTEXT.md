---
depends_on: []
---

# M041: Code Quality Audit — Backend & Frontend

**Gathered:** 2026-03-23
**Status:** Queued — pending auto-mode execution

## Project Description

A comprehensive code quality audit of the core SemPKM platform — backend Python (60k LOC across 233 modules in 37 packages), frontend JavaScript (19k LOC across 28 files), CSS (20k LOC across 16 files), and Jinja2 templates (165 files). The sole deliverable is a prioritized recommendation report. No code changes are made — the report feeds a subsequent execution milestone.

The audit examines the codebase across multiple quality dimensions: readability and naming, module structure and cohesion, logging consistency, error handling patterns, type safety, SPARQL/SQL construction practices, CSS architecture and variable usage, JavaScript structure and global state, test coverage gaps, code duplication, dead code, and accumulated tech debt. Each recommendation is categorized, severity-rated, estimated for effort, and anchored to specific files and line ranges.

## Why This Milestone

SemPKM has shipped 40 milestones in rapid succession — from v1.0 through M040 in under 30 days. This velocity produced a rich, working product but accumulated quality debt that's visible in the numbers:

- **Backend:** `views/service.py` is 3663 lines with 56 functions. `main.py` is 750 lines with 53 router registrations. `admin/router.py` has 23 `except Exception` blocks. Raw f-string SPARQL construction in 10+ modules.
- **Frontend:** `workspace.js` is 5409 lines in a single IIFE. `workspace.css` is 9203 lines with 201 hardcoded color values alongside 1205 CSS variable references — inconsistent theming.
- **Cross-cutting:** 9 identical `PersonMatcher` copies across apps (not in audit scope, but symptomatic). No linting configuration (no ruff, no eslint). Inconsistent type annotations — some modules have full annotations, others have none.

Without a systematic audit, future milestones build on an increasingly fragile foundation. The audit produces a prioritized map of what to fix, in what order, and at what cost — enabling an informed execution plan.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Read a structured recommendation report covering every quality dimension of the codebase
- See each recommendation categorized by dimension (readability, structure, logging, errors, types, SPARQL, CSS, JS, tests, duplication, dead code, tech debt)
- See severity ratings (critical, high, medium, low) and effort estimates (small/medium/large) for each recommendation
- See specific file paths and line ranges for each finding
- Use the report to scope and prioritize a follow-up execution milestone

### Entry point / environment

- Entry point: `.gsd/milestones/M041/M041-RECOMMENDATIONS.md` — the primary deliverable
- Environment: Development (static analysis of source code, no runtime needed)
- Live dependencies involved: None — pure code review

## Completion Class

- Contract complete means: every quality dimension has been systematically examined with findings documented; the recommendation report exists with categorized, severity-rated, effort-estimated entries anchored to specific files
- Integration complete means: N/A — this is analysis only
- Operational complete means: N/A — this is analysis only

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- The recommendation report covers all stated dimensions (readability, module structure, logging, error handling, type safety, SPARQL/SQL patterns, CSS architecture, JS structure, test gaps, duplication, dead code, tech debt)
- Every recommendation has: category, severity, effort estimate, and specific file/line references
- The report includes a prioritized summary (top 10 highest-impact recommendations across all dimensions)
- Backend and frontend are both covered — not one at the expense of the other

## Risks and Unknowns

- **Audit breadth vs depth** — 60k+ LOC is too large for line-by-line review. The audit uses pattern-based detection (grep/rg/ast-grep) to find categories of issues, then spot-checks representative examples. Risk: missing isolated one-off problems. Mitigation: acceptable — the goal is systematic patterns, not every bug.
- **Subjectivity in severity ratings** — "High" vs "Medium" is a judgment call. Mitigation: anchor severity to concrete impact (will this cause a runtime error? confuse a new contributor? slow down future development?).
- **Scope creep into fixing** — Temptation to fix things during the audit. Mitigation: the milestone explicitly produces ONLY a report. Fixes are a separate milestone.

## Existing Codebase / Prior Art

- `backend/app/views/service.py` — 3663 lines, 56 functions, 2 classes. Largest backend module. Contains view rendering, SPARQL query building, field detection heuristics, and 8+ renderer-specific method families.
- `backend/app/main.py` — 750 lines with 53 router registrations and a complex lifespan function. Configuration, middleware, router wiring, and startup logic all in one file.
- `backend/app/admin/router.py` — 1400 lines with 23 `except Exception` broad catches.
- `frontend/static/js/workspace.js` — 5409 lines in a single IIFE. Tab management, sidebar, command palette, persona system, view loading, app integration, context indicator, and more.
- `frontend/static/css/workspace.css` — 9203 lines with mixed CSS variable usage (1205 var references) and hardcoded colors (201 hex values).
- `backend/app/dependencies.py` — 249 lines of FastAPI dependency functions.
- `.gsd/KNOWLEDGE.md` — Contains known tech debt items (DashboardSpec in SQLite, ephemeral workflow runs, htmx URL hardcoding, etc.) that should be cross-referenced during the audit.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions — it is an append-only register; read it during planning, append to it during execution.

## Relevant Requirements

- No existing requirements directly. This milestone produces the input for a future execution milestone that would create requirements.

## Scope

### In Scope

**Backend Python (60k LOC):**
- Readability: naming conventions, function length, module length, docstring coverage
- Module structure: cohesion, coupling, god-module detection, circular imports
- Logging: consistency (structured vs unstructured), log level appropriateness, missing context in log messages
- Error handling: broad `except Exception` patterns, swallowed exceptions, missing error context, inconsistent error response formats
- Type safety: type annotation coverage, Pydantic model usage, untyped function signatures
- SPARQL construction: f-string injection risk, query builder patterns, duplicated query logic
- Async patterns: sync/async boundary hygiene, blocking calls in async handlers
- FastAPI patterns: dependency injection consistency, router organization, middleware layering

**Frontend JavaScript (19k LOC):**
- Structure: IIFE monoliths vs modules, global state management, event coupling
- Naming: function/variable naming consistency
- Error handling: silent failures, missing error UI feedback
- DOM manipulation: patterns, memory leaks (event listeners, timers)
- htmx integration: pattern consistency, custom event contracts

**CSS (20k LOC):**
- Architecture: variable usage vs hardcoded values, theme consistency
- Specificity: selector complexity, `!important` usage
- Duplication: repeated property blocks, opportunity for shared classes
- Responsiveness: breakpoint consistency, mobile coverage

**Templates (165 Jinja2 files):**
- Logic in templates: complex conditionals, Python expressions in templates
- Partial reuse: duplication across templates, extraction opportunities
- htmx patterns: attribute consistency, trigger patterns

**Cross-cutting:**
- Dead code: unused functions, unreachable branches, commented-out code
- Duplication: copy-pasted blocks across modules, extractable shared utilities
- Tech debt: items from KNOWLEDGE.md and PROJECT.md tech debt sections, undocumented debt
- Test gaps: modules with zero test coverage, critical paths without tests
- Configuration: hardcoded values that should be configurable

### Out of Scope / Non-Goals

- App Platform apps (`apps/` directory) — core platform patterns cascade to apps; fixing core is sufficient
- App SDK (`backend/sdk/`) — small surface, already well-structured
- E2E test code (`e2e/`) — test code quality is secondary to platform code
- Mental Model content (`models/`) — RDF/JSON-LD content, not application code
- Documentation site (`docs/`) — HTML/CSS, not application code
- Implementing any fixes — the report is the only deliverable
- Performance profiling or benchmarking — covered by M029
- Security audit — partially covered by M002, different methodology

## Technical Constraints

- Analysis uses `rg`, `ast-grep`, `fd`, and Python AST parsing — no external linting tools needed (though findings may recommend adding them)
- The audit agent reads code but does not modify any files except the recommendation report
- Pattern detection should be reproducible — include the grep/rg commands used so findings can be re-verified

## Integration Points

- `.gsd/KNOWLEDGE.md` — known tech debt and patterns to cross-reference
- `.gsd/PROJECT.md` — tech debt section lists known issues
- `.gsd/DECISIONS.md` — architectural decisions that constrain what "good" looks like (e.g., htmx-only frontend, SPARQL string construction patterns)
- `CLAUDE.md` — project coding conventions that should be verified against reality

## Open Questions

- **Linting tool recommendations** — Should the report recommend specific tools (ruff, eslint, stylelint) as part of the findings, or keep recommendations tool-agnostic? Current thinking: recommend specific tools where appropriate — it's more actionable.
- **Threshold for "too large"** — What's the line count threshold for flagging a module as too large? Current thinking: >500 lines for Python modules, >1000 lines for JS files, >2000 lines for CSS files. These are signals, not hard rules.
