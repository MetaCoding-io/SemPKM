# Phase 3: Mental Model System - Context

**Gathered:** 2026-02-21
**Status:** Ready for planning

<domain>
## Phase Boundary

Users can install, remove, and list Mental Model archives that bundle ontologies, SHACL shapes, view specs, and seed data into the system. The system validates archives on install, rejects invalid ones with detailed reports, and ships a fully-featured starter model (Basic PKM) that auto-installs on first run. Admin UI for model management is Phase 4 (ADMN-02) — this phase builds the backend service and the starter model content.

</domain>

<decisions>
## Implementation Decisions

### Starter Model Content
- Fully fleshed out: each type (Projects, People, Notes, Concepts) gets 8-15 properties covering common use cases
- Rich relationships pre-defined: Project hasParticipant Person, Note isAbout Concept, Project hasNote Note, etc. — shows the graph's power immediately
- Ship with example seed data (a sample project, a few people, some notes, linked concepts) so the system feels alive on first install
- Full view set: each type gets a default table view, a card view, and at least one graph query — Phase 5 renderers will consume these

### Archive Format & Contents
- Directory convention (not ZIP): manifest.yaml at root + subdirectories for ontology/, shapes/, views/, seed/. Easy to author and version control.
- JSON-LD (.jsonld) serialization for all RDF files (ontology, shapes, views, seed data)
- View specs stored as RDF in the triplestore (not JSON config files) — everything lives in the graph, consistent and queryable
- Starter model shipped in the repo at a known path (e.g., models/basic-pkm/), installed automatically on first startup

### Install/Remove Behavior
- Multiple models can be installed simultaneously — namespace prefixes prevent collisions
- Removing a model is blocked if user data exists for that model's types — warn and require explicit data deletion first
- No model upgrades in v1 — remove and reinstall only (per REQUIREMENTS.md: model migrations are out of scope)
- Basic PKM auto-installs on first run when no models are detected — user sees data immediately

### Validation & Error UX
- Detailed validation report on failure: structured list of every error (which file, what rule, what's wrong)
- Errors block install, warnings allow install to proceed — critical issues (missing manifest, broken references) vs minor issues (missing descriptions)
- Model-prefixed IRIs enforced: all IRIs must use a namespace derived from modelId (e.g., urn:sempkm:model:{modelId}:) to prevent cross-model collisions
- Full cross-file reference integrity checks: shapes must reference ontology classes, views must reference valid types, seed data must conform to shapes

### Claude's Discretion
- Exact properties for each type in Basic PKM (within the "fully fleshed out" constraint)
- manifest.yaml schema design
- Named graph strategy for model artifacts (how ontology/shapes/views/seed are stored)
- Validation rule severity assignments (which are errors vs warnings)

</decisions>

<specifics>
## Specific Ideas

No specific references — open to standard approaches within the decisions captured above.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 03-mental-model-system*
*Context gathered: 2026-02-21*
