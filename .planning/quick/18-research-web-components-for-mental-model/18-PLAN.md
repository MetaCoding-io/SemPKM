---
plan: 18-01
objective: Research how Web Components (Custom Elements) could extend Mental Models to contribute custom UI
tasks: 2
wave: 1
---

# Plan 18-01: Research Web Components for Mental Model System Integration

## Objective

Investigate how the Mental Model system could be extended so that installed models contribute custom Web Components (Custom Elements, Shadow DOM) as part of their bundle — enabling model authors to ship specialized UI renderers, custom property editors, and interactive widgets alongside their ontologies and SHACL shapes.

**Purpose:** The current Mental Model system contributes backend-consumable artifacts (ontology, shapes, views, seed data, icons, settings). The frontend relies on generic renderers (table, card, graph) and SHACL-driven form generation. This research explores whether Web Components provide a viable path for models to also contribute custom frontend UI — for example, a "Kanban" model contributing a `<sempkm-kanban-board>` element, or a "Chemistry" model contributing a `<sempkm-molecule-viewer>`.

**Output:** Research document at `.planning/research/web-components-for-mental-models.md` with architecture analysis, security model, htmx integration strategy, manifest extension design, and comparison of alternatives (Web Components vs. Jinja2 macro bundles vs. iframe sandboxes).

## Context

@.planning/PROJECT.md
@.planning/codebase/ARCHITECTURE.md
@.planning/codebase/STACK.md
@backend/app/models/manifest.py
@backend/app/views/registry.py
@backend/app/views/service.py
@models/basic-pkm/manifest.yaml

## Task 1: Deep web research on Web Components in htmx-based and RDF/semantic systems

**Files:** (research notes, no files created yet)

**Action:** Research the following areas using web sources. For each area, capture specific findings with source URLs:

1. **Web Components + htmx interop** — How do Custom Elements work with htmx's DOM-swap model? Known issues with Shadow DOM and `hx-*` attributes? Does htmx process Custom Elements correctly after swap? Reference htmx docs, community discussions, and existing implementations.

2. **Web Components for plugin/extension systems** — Survey existing projects that use Web Components as a plugin mechanism where third-party code contributes UI elements. Examples: Grafana panels, Home Assistant cards, Backstage plugins, Obsidian. Document their loading strategy, registration patterns, and security boundaries.

3. **Security and sandboxing** — How to safely load and execute model-contributed JavaScript/Web Components. Options: CSP restrictions, iframe sandboxing with `srcdoc`, ShadowRealm proposal status, module-level sandboxing. What are the trust boundaries when a model author can contribute executable code?

4. **RDF/Linked Data + Web Components** — Any existing work on semantic-web-driven component rendering? LDP-based component discovery? Schema.org WebComponent? Projects like Solid that bridge RDF data and UI components.

5. **Alternative approaches** — Compare Web Components against: (a) Jinja2 macro/template bundles contributed by models, (b) iframe-sandboxed micro-frontends per model, (c) server-side renderer plugins (Python) that produce HTML, (d) declarative JSON-based component configs (like JSON Forms, RJSF).

6. **Registration and lifecycle** — How would model-contributed components be registered in the browser? Dynamic `import()` from model-served JS modules? `customElements.define()` at model install time? Lazy loading patterns for components that are only needed when a specific type is viewed?

**Verify:** Research notes captured with findings from all 6 areas, each with at least 2-3 source URLs

**Done:** Research complete with enough information to draft the architecture document

## Task 2: Write research document with architecture proposal and source links

**Files:** `.planning/research/web-components-for-mental-models.md`

**Action:** Write a comprehensive research document structured as follows:

### Document structure:

**1. Executive Summary** (2-3 paragraphs)
- The opportunity: models contributing custom UI alongside data/schema
- The primary recommendation and confidence level
- Key risks and open questions

**2. Current State** (brief)
- How Mental Models contribute artifacts today (manifest.yaml entrypoints)
- How the frontend consumes model data (ViewSpecService -> Jinja2 templates -> htmx)
- The gap: no model-contributed frontend code exists today

**3. Web Components + htmx Analysis**
- Findings from research on Custom Elements behavior during htmx DOM swaps
- Shadow DOM implications for htmx attribute processing
- Recommended pattern: light DOM Custom Elements (no Shadow DOM) for htmx compatibility
- Code example showing a model-contributed element that works with htmx

**4. Security Model**
- Trust levels: core (SemPKM), trusted (published models), untrusted (user-created)
- Sandboxing options analysis (CSP, iframe, ShadowRealm, none)
- Recommended approach for each trust level
- What model authors CAN and CANNOT do

**5. Manifest Extension Design**
- Proposed additions to manifest.yaml schema for component contribution
- File structure within model bundle (e.g., `components/` directory)
- Registration lifecycle: install -> serve -> load -> define -> render
- Example manifest.yaml with component declarations

**6. Integration Architecture**
- How model JS modules would be served (nginx static path? API endpoint? inline in template?)
- Component discovery: how does the frontend know which components a model provides?
- Data binding: how components receive RDF data (attributes? properties? events?)
- htmx integration: how components participate in htmx request/response cycle

**7. Alternatives Comparison Table**
- Web Components vs. Jinja2 macro bundles vs. iframe sandboxes vs. server-side plugins vs. declarative JSON configs
- Evaluate on: security, DX for model authors, htmx compatibility, performance, complexity

**8. Phased Adoption Roadmap**
- Phase 1: Custom renderer templates (Jinja2 macros from models — lowest risk)
- Phase 2: Light DOM Web Components (model-contributed Custom Elements — medium risk)
- Phase 3: Full component SDK (model author toolkit, dev server, type-safe data binding — highest investment)

**9. Source Links**
- All URLs referenced in the research, organized by topic

Throughout the document, include source links inline (not just at the end) so every claim is traceable.

**Verify:** `wc -l .planning/research/web-components-for-mental-models.md` shows 200+ lines; document contains all 9 sections; grep confirms source URLs present

**Done:** Research document committed with architecture analysis, security model, manifest extension design, alternatives comparison, and source links throughout
