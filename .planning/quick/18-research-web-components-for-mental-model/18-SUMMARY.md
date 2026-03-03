---
phase: quick-18
plan: 01
subsystem: research
tags: [web-components, custom-elements, htmx, mental-models, security, csp, plugin-system]

# Dependency graph
requires:
  - phase: none
    provides: n/a (research task, no code dependencies)
provides:
  - Architecture analysis for model-contributed Web Components
  - Security model with trust levels (core/trusted/untrusted)
  - manifest.yaml extension design for component declarations
  - Phased adoption roadmap (Jinja2 macros -> Web Components -> SDK)
  - 40+ source links for future implementation reference
affects: [mental-model-system, manifest-schema, frontend-architecture, renderer-registry]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Light DOM Custom Elements (no Shadow DOM) for htmx compatibility"
    - "sempkm-{modelId}-{component} tag naming convention"
    - "CSP connect-src 'self' for trusted model JavaScript sandboxing"
    - "Server-side component discovery via template context (not client-side fetch)"

key-files:
  created:
    - ".planning/research/web-components-for-mental-models.md"
  modified: []

key-decisions:
  - "Shadow DOM incompatible with htmx -- light DOM Custom Elements only"
  - "Three-phase adoption: Jinja2 macros (low risk) -> light DOM Web Components (medium) -> full SDK (high)"
  - "Trust model: core (no restrictions), trusted (CSP-restricted JS), untrusted (Jinja2 macros only, no JS)"
  - "Component tag names must use sempkm- prefix for namespace safety"
  - "nginx static path preferred over API endpoint for serving model JS/CSS"

patterns-established:
  - "Research document format: executive summary, current state, analysis, security, design, integration, comparison, roadmap, sources"

requirements-completed: []

# Metrics
duration: 4min
completed: 2026-03-03
---

# Quick Task 18: Web Components for Mental Model System Integration Summary

**Architecture research for model-contributed Web Components: light DOM Custom Elements recommended over Shadow DOM for htmx compatibility, with phased adoption from Jinja2 macros to full component SDK, CSP-based security model, and manifest.yaml extension design**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-03T02:56:24Z
- **Completed:** 2026-03-03T03:00:19Z
- **Tasks:** 2
- **Files created:** 1

## Accomplishments

- Comprehensive 704-line research document covering 6 research areas with 40+ source links
- Identified critical htmx + Shadow DOM incompatibility (htmx does not process hx-* attributes inside Shadow DOM)
- Designed manifest.yaml extension schema for component declarations (modules, styles, renderers, templates)
- Proposed three-tier trust model (core/trusted/untrusted) with CSP-based sandboxing
- Surveyed plugin systems: Home Assistant cards, Grafana panels, Backstage plugins, Obsidian
- Researched RDF + Web Components ecosystem: Solid, LDflex, Comunica, rdflib.js
- Compared 5 alternative approaches with detailed evaluation matrix
- Proposed phased roadmap from Jinja2 macros (immediate) to full SDK (aspirational)

## Task Commits

Tasks 1 and 2 combined into single commit (research notes embedded in document):

1. **Task 1: Deep web research** + **Task 2: Write research document** - `dcdad2c` (docs)

## Files Created

- `.planning/research/web-components-for-mental-models.md` - 704-line research document with architecture analysis, security model, manifest extension design, alternatives comparison, phased roadmap, and 40+ source links

## Decisions Made

1. **Shadow DOM is incompatible with htmx** -- htmx does not process hx-* attributes inside Shadow DOM boundaries; light DOM Custom Elements are the only viable pattern for SemPKM's htmx-first architecture
2. **Three-phase adoption roadmap** -- Jinja2 macro bundles (lowest risk, immediate value) -> light DOM Web Components (medium risk, high extensibility) -> full component SDK (high investment, professional DX)
3. **Trust model with CSP sandboxing** -- Core code has no restrictions; trusted (published) models run JS with CSP restrictions (no eval, no external fetch); untrusted models get Jinja2 macros only (no client JS)
4. **nginx static path for serving model components** -- Preferred over API endpoint or inline templates; leverages existing volume mounts, proper MIME types, and browser caching
5. **Server-side component discovery** -- Base template injects model component <script>/<link> tags from server context rather than client-side fetch (no JS dependency for component loading)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - research task, no external service configuration required.

## Next Steps

- Phase 1 (Jinja2 macro bundles) could be implemented as a small enhancement to the existing renderer registry
- Phase 2 (Web Components) requires manifest.yaml schema changes and nginx configuration
- Phase 3 (SDK) is aspirational and depends on real model author adoption

---
*Quick Task: 18-research-web-components-for-mental-model*
*Completed: 2026-03-03*
