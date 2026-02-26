# SemPKM Future Milestones Planning

**Created:** 2026-02-26
**Context:** Planning session after v2.0 completion. Captures feature ideas, milestone breakdown, dependency map, parallelization strategy, and architectural decisions.

---

## Key Architectural Decision: No VSCode/Theia

**Decision:** Stay with the current FastAPI + htmx + vanilla JS stack. Do NOT adopt Theia or VSCode as the IDE shell.

**Rationale:**
- Theming is already substantially done (theme.css, CSS custom properties, dark mode Phase 13, settings Phase 15). Full user-configurable themes are a CSS variable extension problem, not an architecture problem.
- Flexible panel layout (more than Split.js) is achievable with **GoldenLayout** (pure JS, no framework required) — handles arbitrary drag-to-dock panel rearrangement with saved layout configs. Integrates cleanly with htmx-rendered panel content.
- Adopting Theia/VSCode would mean a complete frontend rewrite, extension model, and a new paradigm with massive complexity. Not justified when the current stack can deliver the UX goals.

**What this means for future phases:**
- Theming: CSS variable token sets + theme picker in settings
- Flexible panels: GoldenLayout integration phase
- Dashboards: Store layout configs in RDF, apply via GoldenLayout API

---

## Parallelization Strategy

The biggest lever for parallel execution is **research milestones** where all phases run simultaneously, followed by **implementation milestones** where independent features overlap in plans.

**Research milestone pattern:**
- All research phases spawn in parallel (4+ agents at once)
- Each produces a RESEARCH.md and recommendation
- Synthesis phase reviews all research, makes final decisions
- Then plan implementation phases with confidence

**Implementation milestone pattern:**
- Features with independent backends (search, VFS, SPARQL) can be parallel plans within a phase
- Features that share UI components (dashboards, panels) must sequence after shared infrastructure

---

## Milestone: v2.1 — Research & Architecture Decisions

**Goal:** Resolve all major open questions before building. No implementation — research and decisions only.

**All phases run in parallel.**

### Phase 20: Full-Text Search + Vector Store Research
**Agent focus:** What is the right search technology for SemPKM?

Key questions:
- Are there open-source RDF triplestores with built-in FTS (RDF4J, Apache Jena, Oxigraph)?
- RDF4J's Lucene integration — current state, query syntax, config?
- OpenSearch as a sidecar: index `urn:sempkm:current` graph, sync via webhooks?
- pgvector / sentence-transformers for semantic similarity search?
- How does FTS compose with SPARQL filtering?
- What does the write path look like (index on EventStore.commit)?

Output: RESEARCH.md with recommended approach, indexing strategy, query API design.

### Phase 21: SPARQL Interface Research
**Agent focus:** What is the most modern, beautiful SPARQL UI to integrate?

Key questions:
- Zazuko Yasgui — current state (2025/2026), license, embed options?
- Other modern SPARQL UIs (SPARQL Playground, Triply, etc.)?
- Iframe embed vs. sidecar deployment vs. custom implementation?
- Autocomplete: how does it work in Yasgui (schema-aware, prefix-aware)?
- "Pills" / inline object rendering for query results — does Yasgui support it or do we build it?
- Saved queries + query history: server-side (user-scoped RDF storage) or localStorage?
- Integration with SemPKM's existing `/sparql` debug endpoint?

Output: RESEARCH.md with recommended approach, integration plan, UI mockup description.

### Phase 22: Virtual Filesystem — Technology Validation
**Agent focus:** Validate the WebDAV approach from `.planning/research/virtual-filesystem.md` and identify implementation risks.

Existing research: `.planning/research/virtual-filesystem.md` — comprehensive, covers prior art, design, protocol choices.

Key questions to validate:
- `wsgidav` + FastAPI integration — current state, async support?
- FUSE as alternative — `fusepy` / `pyfuse3` current state on Linux?
- What's the minimum viable MountSpec vocabulary (start with `flat` and `tag-groups` strategies)?
- How does the write path integrate with EventStore.commit?
- WebDAV discovery — will macOS Finder / Linux file managers mount it without config?
- Performance: SPARQL on every readdir() — acceptable? Caching strategy?

Output: RESEARCH.md with implementation plan, phased rollout (read-only first, then writes), risks.

### Phase 23: UI Shell Architecture Research
**Agent focus:** GoldenLayout for flexible panels + theming token system design.

Key questions:
- GoldenLayout 2.x vs alternatives (Flexlayout-model, Dockview) — feature comparison, bundle size, htmx compatibility?
- How does GoldenLayout interact with htmx partial renders inside panels?
- Layout persistence: JSON config → store in RDF as user preference, load on workspace init?
- Theme token system: what CSS custom property vocabulary covers all components (sidebar, tabs, editor, graph, forms, modals)?
- Model-contributed themes: how does a Mental Model declare a theme bundle?
- Can GoldenLayout handle the "Dashboards" use case (named saved layouts)?

Output: RESEARCH.md with GoldenLayout integration design, CSS token vocabulary, theme contribution spec.

---

## Milestone: v2.2 — Data Discovery

**Goal:** Make the knowledge graph findable and queryable. Three independent features, mostly parallel.

### Phase 24: Full-Text Search Implementation
Implement the technology chosen in Phase 20 research.

Likely plans:
- Backend: index integration (RDF4J Lucene or OpenSearch sidecar), EventStore hook, search API endpoint
- Frontend: search UI (command palette integration, search results panel, filter by type/date)

### Phase 25: SPARQL Interface Integration
Implement the approach chosen in Phase 21 research.

Likely plans:
- Integration: embed Yasgui (or chosen tool) as a special tab / bottom panel tab
- Enhancements: saved queries (RDF storage, user-scoped), query history, inline object pills in results
- Polish: autocomplete schema-aware, prefix auto-complete from PrefixRegistry

### Phase 26: Virtual Filesystem MVP
Implement the WebDAV approach validated in Phase 22 research.

Likely plans:
- Read-only WebDAV server: wsgidav + FastAPI mount, MountSpec model, SPARQL-to-directory mapping
- Markdown+frontmatter rendering: SHACL-driven frontmatter fields, body property rendering
- MountSpec UI: configure mounts via Settings page
- (Optional next milestone) Write support with SHACL validation on parse-back

---

## Milestone: v2.3 — Shell & Navigation

**Goal:** Dashboards, flexible panels, full theming. Depends on v2.2 UI shell research (Phase 23).

### Phase 27: GoldenLayout Integration
Replace or extend Split.js with GoldenLayout for arbitrary drag-to-dock panel rearrangement.

- GoldenLayout initialization, panel registry, htmx content loading into panels
- Layout persistence (JSON config in RDF as user preference)
- Migration from existing Split.js panel model

### Phase 28: Dashboards (Named Layouts)
User-defined and model-provided named workspace layouts (Bases equivalent).

- Dashboard data model (RDF storage, user-scoped + model-provided)
- Dashboard picker UI (sidebar section or command palette)
- Mental Model manifest: `dashboards` key for model-provided layouts
- Default dashboards for basic-pkm model (e.g. "Research Mode", "Writing Mode")

### Phase 29: Full Theming System
User-selectable themes; model-contributed theme bundles.

- CSS custom property token vocabulary (finalized from Phase 23 research)
- Built-in themes: Dark+, Light, High Contrast, Solarized
- Theme picker in settings
- Mental Model manifest: `theme` key for model-contributed themes
- Theme preview in settings

---

## Milestone: v2.4 — Low-Code & Workflows

**Goal:** SemPKM as a platform for structured user interactions. Depends on v2.3 shell being stable.

### Phase 30: Low-Code UI Builder
Users compose basic components tied to SemPKM actions. Notion + Airflow inspired.

- Component palette: form fields, buttons, text blocks, object references, view embeds
- Layout canvas: drag-and-drop component placement
- Action binding: bind components to SemPKM commands (object.create, object.patch, etc.)
- Save as Mental Model artifact (user-created "App")

Design principle: NOT a general-purpose UI builder. Components are SemPKM-native. No arbitrary HTML/JS injection.

### Phase 31: Minimal Workflow Orchestration
Orchestrated sequences of views/forms — not n8n (no business logic engine). Think CRM onboarding.

- Workflow definition: sequence of steps, each a form or view, with conditions
- Step types: form (SHACL-validated), confirmation, object reference picker, note append
- Example: "Add Client" → "Add Project" → "Add Invoice" → "Log success to note body"
- Trigger types: manual (sidebar entry), webhook (event-triggered), model-provided workflow
- State: workflow instance stored as RDF (current step, collected values, outcome)

Design principle: Complement n8n for complex business logic. SemPKM workflows are UI-orchestration only — for data collection and structured entry, not computation.

---

## Tech Debt Phases (schedule across milestones)

These are from CONCERNS.md. Schedule as plan slots within feature milestones rather than dedicated phases.

**High priority (Phase 19 scope):**
- Label cache invalidation after writes
- datetime.now() → datetime.now(timezone.utc) in browser router
- EventStore DI in browser router write handlers
- CORS wildcard + credentials fix
- Debug endpoint owner-only guard
- IRI validation before SPARQL interpolation

**Medium priority (schedule in v2.1-v2.2):**
- Alembic migration runner at startup (replace create_all)
- SMTP email delivery implementation
- Session cleanup job (expired sessions accumulate)
- ViewSpecService TTL cache (two SPARQL queries per lookup)
- source_model attribution for multi-model installs
- validation/report.py hash() fallback → raise instead

**Lower priority (v2.3+):**
- browser/router.py monolith split into sub-routers
- LabelService Redis cache for multi-worker deployments
- Dependency pinning in pyproject.toml

---

## Standing Decisions for All Future Phases

1. **E2E tests required**: Every phase with user-visible behavior must add/update Playwright tests in `e2e/tests/`. Gate enforced in execute-plan.md.
2. **User guide docs required**: Any user-visible feature must be reflected in `docs/`. Gate enforced in execute-plan.md.
3. **No VSCode/Theia**: Current stack handles theming and flexible panels. Do not revisit unless constraints change dramatically.
4. **VFS uses WebDAV first**: FUSE is an option but WebDAV is the starting point (cross-platform, existing HTTP infra).
5. **Workflows are UI-orchestration only**: Do not replicate n8n. Deep n8n integration is the answer for complex business logic.
6. **Mental Models stay the extensibility mechanism**: Themes, dashboards, workflows, apps — all contributed via Mental Model manifests.

---

## Research Artifacts

- `virtual-filesystem.md` — Comprehensive prior art + design for VFS feature (ready for Phase 22 validation)

---

*Created: 2026-02-26 — planning session after v2.0 milestone completion*
