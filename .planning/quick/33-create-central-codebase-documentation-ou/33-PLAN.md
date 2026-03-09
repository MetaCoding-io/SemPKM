---
phase: quick-33
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - CODEBASE.md
  - .planning/codebase/STRUCTURE.md
  - .planning/codebase/ARCHITECTURE.md
autonomous: true
requirements: ["QUICK-33"]
must_haves:
  truths:
    - "A developer opening the repo can find a single CODEBASE.md at the root that explains all components, their purposes, and where they live"
    - "All modules added since 2026-02-25 (obsidian, indieauth, vfs, inference, lint, canvas, webid, monitoring, shell) are documented"
    - "The document covers backend modules, frontend assets, model bundles, e2e tests, config, and Docker services"
  artifacts:
    - path: "CODEBASE.md"
      provides: "Central developer-facing codebase documentation"
      min_lines: 200
    - path: ".planning/codebase/STRUCTURE.md"
      provides: "Updated directory structure with all current modules"
      contains: "indieauth"
    - path: ".planning/codebase/ARCHITECTURE.md"
      provides: "Updated architecture reflecting new subsystems"
      contains: "IndieAuth"
  key_links:
    - from: "CODEBASE.md"
      to: ".planning/codebase/"
      via: "Cross-references for deep-dive docs"
      pattern: "\\.planning/codebase/"
---

<objective>
Create a central CODEBASE.md at the project root that documents all components, file locations, and purposes for developer onboarding. Also update the existing `.planning/codebase/STRUCTURE.md` and `ARCHITECTURE.md` to reflect modules added since the original 2026-02-25 analysis.

Purpose: Give any developer (human or AI) opening the repo a single entry point to understand the full codebase — what exists, where it lives, what it does, and how the pieces connect.

Output: `CODEBASE.md` (root), updated `STRUCTURE.md` and `ARCHITECTURE.md` in `.planning/codebase/`
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@.planning/codebase/STRUCTURE.md
@.planning/codebase/ARCHITECTURE.md
@.planning/codebase/STACK.md
@.planning/codebase/CONVENTIONS.md
@.planning/codebase/INTEGRATIONS.md
@.planning/codebase/TESTING.md
@.planning/codebase/CONCERNS.md
</context>

<tasks>

<task type="auto">
  <name>Task 1: Audit current codebase and update .planning/codebase/ docs</name>
  <files>.planning/codebase/STRUCTURE.md, .planning/codebase/ARCHITECTURE.md</files>
  <action>
Scan the actual codebase to identify all modules/files that exist now but are missing from the 2026-02-25 analysis. The following modules were added after the original analysis and need to be documented:

**Backend modules to add to STRUCTURE.md:**
- `backend/app/obsidian/` — Obsidian vault import (scanner, models, broadcast) — 6 py files
- `backend/app/indieauth/` — IndieAuth OAuth2 provider (service, router, models, scopes, schemas, migration) — 6 py files
- `backend/app/inference/` — OWL inference engine (InferenceService, entailment, metadata) — 5 py files
- `backend/app/lint/` — Structured lint results (LintService, models, router, SSE broadcast) — 5 py files
- `backend/app/canvas/` — Spatial canvas workspace (RDF neighbor loading, markdown rendering) — 4 py files
- `backend/app/webid/` — WebID profile (data model, cryptographic service, settings) — 4 py files
- `backend/app/vfs/` — Virtual filesystem / WebDAV (provider, collections, resource rendering, write, cache) — 8 py files
- `backend/app/monitoring/` — PostHog error middleware and analytics client — 4 py files
- `backend/app/shell/` — Admin shell router — 2 py files

**Frontend files to add:**
- `frontend/static/js/canvas.js` — Spatial canvas interactions
- `frontend/static/js/vfs-browser.js` — VFS file browser panel
- `frontend/static/js/named-layouts.js` — Named layout persistence
- `frontend/static/js/workspace-layout.js` — Dockview workspace layout manager
- `frontend/static/js/posthog.js` — PostHog analytics SDK loader
- `frontend/static/js/tutorials.js` — Driver.js guided tour overlays
- `frontend/static/js/cleanup.js` — Resource cleanup utilities
- `frontend/static/css/dockview-sempkm-bridge.css` — Dockview theme bridge
- `frontend/static/css/import.css` — Obsidian import UI styles
- `frontend/static/css/vfs-browser.css` — VFS browser panel styles

**Template directories to add:**
- `backend/app/templates/obsidian/` — Obsidian import UI templates
- `backend/app/templates/indieauth/` — IndieAuth authorization UI
- `backend/app/templates/webid/` — WebID profile templates

**E2E test directories to add:**
- `e2e/tests/08-search/`
- `e2e/tests/09-inference/`
- `e2e/tests/10-lint-dashboard/`
- `e2e/tests/11-helptext/`
- `e2e/tests/12-bug-fixes/`
- `e2e/tests/13-v24-coverage/`
- `e2e/tests/14-obsidian-import/`
- `e2e/tests/15-webid/`
- `e2e/tests/16-indieauth/`

**Model to add:**
- `models/ppv/` — PPV (Personal Productivity Vault) model bundle

For each new module, read the `__init__.py` and/or main file (router.py, service.py) to extract a brief purpose description. Then update:

1. **STRUCTURE.md**: Add all new directories to the directory tree, add new "Directory Purposes" entries, update "Key File Locations" and "Where to Add New Code" sections as needed. Update the analysis date to 2026-03-09.

2. **ARCHITECTURE.md**: Add new subsystems to the Layers section where appropriate:
   - Inference engine under a new "Inference Layer" or added to Service Layer
   - IndieAuth under Auth Layer
   - VFS/WebDAV as a new layer or Integration
   - Lint as part of Service Layer
   - Canvas as part of Browser/UI
   - Update analysis date to 2026-03-09

Do NOT rewrite sections that are already accurate. Only add new entries and update dates. Preserve existing content and formatting.
  </action>
  <verify>
    <automated>grep -q "indieauth" .planning/codebase/STRUCTURE.md && grep -q "inference" .planning/codebase/STRUCTURE.md && grep -q "vfs" .planning/codebase/STRUCTURE.md && grep -q "IndieAuth" .planning/codebase/ARCHITECTURE.md && echo "PASS: New modules documented" || echo "FAIL: Missing modules"</automated>
  </verify>
  <done>STRUCTURE.md and ARCHITECTURE.md reflect all current modules as of 2026-03-09. Every backend module directory, frontend JS/CSS file, template directory, and e2e test directory that currently exists in the repo is represented in the docs.</done>
</task>

<task type="auto">
  <name>Task 2: Create consolidated CODEBASE.md at project root</name>
  <files>CODEBASE.md</files>
  <action>
Create a single-file developer reference at `CODEBASE.md` in the project root. This is the "open the repo and understand everything" document. Structure it as:

**1. Overview** (3-5 sentences)
- What SemPKM is (event-sourced RDF knowledge graph with HTMX SSR)
- The three services (FastAPI backend, nginx frontend, RDF4J triplestore)
- How writes work (POST /api/commands -> EventStore -> named graphs)
- How reads work (SPARQL -> Jinja2/htmx partials)

**2. Directory Layout** (ASCII tree)
- Full tree from updated STRUCTURE.md but more concise (1-line annotations)
- Include all current directories (backend modules, frontend, models, e2e, config, docs, scripts)

**3. Backend Modules** (table format)
For each module under `backend/app/`, list:
| Module | Purpose | Key Files | Line Count (approx) |

Group by domain:
- Core: main, config, dependencies, db, rdf, triplestore, sparql
- Commands & Events: commands, events
- Services: services, models, views, validation, labels, shapes
- Auth & Identity: auth, indieauth, webid
- UI Routers: browser, admin, debug, shell
- Features: inference, lint, canvas, obsidian, vfs, monitoring, health

**4. Frontend Assets** (table format)
| File | Purpose |
For each JS and CSS file.

**5. Templates** (brief tree with annotations)
Show the template directory structure with what each subdirectory renders.

**6. Mental Models** (brief)
Explain the model bundle structure (manifest.yaml, ontology/, shapes/, views/, seed/) and list installed models (basic-pkm, ppv).

**7. E2E Tests** (brief table)
| Directory | Test Area | Approx Tests |

**8. Docker Services** (brief)
The three services from docker-compose.yml with ports and key config.

**9. Data Flow Diagrams** (ASCII)
Include the write flow and read flow from ARCHITECTURE.md but condensed.

**10. Key Conventions** (bullet list)
- Naming conventions (brief)
- Module structure pattern
- Where to add new code (brief pointers to STRUCTURE.md for full details)

**11. Deep-Dive References**
Link to `.planning/codebase/` docs for detailed analysis:
- ARCHITECTURE.md — Layer details, data flows, key abstractions
- STACK.md — All dependencies and versions
- CONVENTIONS.md — Code style, naming, error handling
- INTEGRATIONS.md — External services, auth, webhooks
- TESTING.md — Test patterns, fixtures, helpers
- CONCERNS.md — Tech debt, security, performance

Keep the document concise but complete. Target 250-350 lines. Use tables over prose where possible. This is a reference document, not a narrative.

Important: Read actual module files (at minimum `__init__.py` or the main .py file) for any module whose purpose is unclear. Do not guess. Use `fd` and `rg` per CLAUDE.md conventions for file discovery.
  </action>
  <verify>
    <automated>test -f CODEBASE.md && wc -l CODEBASE.md | awk '{if ($1 >= 200) print "PASS: CODEBASE.md exists with " $1 " lines"; else print "FAIL: Too short (" $1 " lines)"}'</automated>
  </verify>
  <done>CODEBASE.md exists at project root with 200+ lines covering all components. A developer can open this single file and understand: what every directory does, how data flows through the system, what the key files are, and where to find detailed docs.</done>
</task>

</tasks>

<verification>
1. `CODEBASE.md` exists at project root and is 200+ lines
2. Every directory under `backend/app/` (excluding `__pycache__` and `templates`) appears in CODEBASE.md
3. Every JS file in `frontend/static/js/` appears in CODEBASE.md
4. `.planning/codebase/STRUCTURE.md` contains all current modules including indieauth, inference, vfs, obsidian, lint, canvas, webid
5. `.planning/codebase/ARCHITECTURE.md` references the new subsystems
</verification>

<success_criteria>
- CODEBASE.md at project root serves as single-entry-point developer documentation
- All 24 backend modules, 16 JS files, 9 CSS files, 2 model bundles, and 16 e2e test directories are documented
- .planning/codebase/STRUCTURE.md and ARCHITECTURE.md updated to 2026-03-09
- No module or file that currently exists in the repo is missing from the documentation
</success_criteria>

<output>
After completion, create `.planning/quick/33-create-central-codebase-documentation-ou/33-SUMMARY.md`
</output>
