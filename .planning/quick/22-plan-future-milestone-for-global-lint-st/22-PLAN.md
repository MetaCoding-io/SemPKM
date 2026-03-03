---
phase: 22-plan-future-milestone-for-global-lint-st
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - .planning/REQUIREMENTS.md
  - .planning/ROADMAP.md
  - .planning/research/future-milestones.md
autonomous: true
requirements: [DOC-22]

must_haves:
  truths:
    - "Future Global Lint Status milestone is fully documented with phases, requirements, and success criteria in the planning system"
    - "The milestone builds on existing SHACL validation infrastructure (ValidationService, AsyncValidationQueue, lint_panel.html) and captures all key feature areas: global lint dashboard, filtering/search, fix guidance messages, and click-to-edit inline workflow"
    - "Requirements are traceable and follow project conventions (requirement IDs, success criteria, phase mapping)"
  artifacts:
    - path: ".planning/REQUIREMENTS.md"
      provides: "New requirement IDs for Global Lint Status milestone under Future Requirements section"
      contains: "LINT-"
    - path: ".planning/ROADMAP.md"
      provides: "Future milestone entry with phase descriptions"
      contains: "Global Lint Status"
    - path: ".planning/research/future-milestones.md"
      provides: "Future milestone entry for Global Lint Status with phase descriptions"
      contains: "Global Lint"
  key_links:
    - from: ".planning/ROADMAP.md"
      to: ".planning/REQUIREMENTS.md"
      via: "requirement IDs referenced in phase details"
      pattern: "LINT-\\d+"
---

<objective>
Document a future milestone for a Global Lint Status View that provides a workspace-wide validation dashboard across all objects in the knowledge base. The milestone captures the user's vision across four feature areas: (1) a global lint/validation status view showing all SHACL violations, warnings, and infos across every object, (2) standard UI for filtering and searching lint results by severity, type, property path, and object, (3) helpful human-readable messages explaining how to fix each issue, and (4) click-to-navigate linking that opens the offending object in a dockview pane for inline editing.

This builds on the existing per-object SHACL validation infrastructure: `ValidationService` (pyshacl runner), `AsyncValidationQueue` (background validation on every commit), `ValidationReport`/`ValidationResult` dataclasses, `lint_panel.html` (per-object lint tab), and the `/api/validation/latest` polling endpoint.

Purpose: Capture the user's vision for a global lint status experience so it can be properly scoped, researched, and planned when the time comes. This is roadmap documentation, not implementation.

Output: Updated REQUIREMENTS.md (new LINT-* requirement IDs), updated ROADMAP.md (new future milestone entry), and updated future-milestones.md (detailed milestone section).
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/ROADMAP.md
@.planning/STATE.md
@.planning/REQUIREMENTS.md
@.planning/research/future-milestones.md
</context>

<interfaces>
<!-- Existing validation infrastructure the milestone builds on -->

From backend/app/validation/report.py:
```python
@dataclass
class ValidationResult:
    focus_node: str          # IRI of the object with the issue
    severity: str            # "Violation", "Warning", or "Info"
    path: Optional[str]      # Property path (e.g., dcterms:title)
    value: Optional[str]     # The problematic value
    message: str             # Human-readable message
    source_shape: Optional[str]       # SHACL shape that triggered this
    constraint_component: Optional[str]  # e.g., sh:MinCountConstraintComponent

@dataclass
class ValidationReportSummary:
    report_iri: str
    event_iri: str
    conforms: bool
    violation_count: int
    warning_count: int
    info_count: int
    timestamp: str
```

From backend/app/services/validation.py:
```python
class ValidationService:
    async def validate(self, event_iri: str, timestamp: str) -> ValidationReport
    async def get_latest_summary(self) -> Optional[ValidationReportSummary]
    async def get_report_by_event(self, event_iri: str) -> Optional[ValidationReportSummary]
```

From backend/app/validation/queue.py:
```python
class AsyncValidationQueue:
    # Background worker processes validation jobs after each EventStore.commit()
    # Queue coalescing: only validates latest when multiple jobs queued
    async def enqueue(self, event_iri: str, timestamp: str) -> None
    latest_report: Optional[ValidationReportSummary]  # In-memory cache
```

From backend/app/validation/router.py:
```python
GET /api/validation/latest    -> ValidationReportSummary (cached or from triplestore)
GET /api/validation/{event_id} -> ValidationReportSummary for specific event
```

From backend/app/templates/browser/lint_panel.html:
- Per-object lint tab showing violations, warnings, infos
- Click-to-jump via jumpToField(propertyPath)
- htmx auto-refresh every 10s
- Conformance gating notice (export blocked message)
</interfaces>

<tasks>

<task type="auto">
  <name>Task 1: Add Global Lint Status requirements to REQUIREMENTS.md</name>
  <files>.planning/REQUIREMENTS.md</files>
  <action>
Add a new section under "Future Requirements" in `.planning/REQUIREMENTS.md` titled `### Global Lint Status (future milestone)`.

Define the following requirement IDs, each with a one-line user-visible behavior description following the existing "User can..." pattern:

**Global Lint Dashboard:**
- **LINT-01**: User can open a Global Lint Status view (as a dockview panel or dedicated page) that shows all SHACL validation results across every object in the knowledge base, with summary counts by severity (violations, warnings, infos) and a per-object breakdown
- **LINT-02**: Global lint view updates automatically after each EventStore.commit() via the existing AsyncValidationQueue; user sees the latest validation state without manual refresh
- **LINT-03**: User can see a visual health indicator (e.g., status bar badge or sidebar icon) showing the overall knowledge base validation status at a glance (pass / N violations / N warnings)

**Filtering and Search:**
- **LINT-04**: User can filter lint results by severity level (violations only, warnings only, infos only, or combinations)
- **LINT-05**: User can filter lint results by object type (e.g., show only Note violations, only Project violations) using the Mental Model's type registry
- **LINT-06**: User can search/filter lint results by keyword across message text, property path, and object label
- **LINT-07**: User can sort lint results by severity, object name, property path, or timestamp

**Fix Guidance:**
- **LINT-08**: Each lint result displays a human-readable "how to fix" message that explains what the constraint expects and how to resolve the violation (not just "constraint violated" but "This field requires at least 1 value -- add a title to fix")
- **LINT-09**: Fix guidance messages are derived from SHACL shape metadata (sh:description, sh:name, constraint component type) and augmented with Mental Model-provided help text when available
- **LINT-10**: Common constraint violations (sh:minCount, sh:maxCount, sh:datatype, sh:pattern, sh:class) have built-in human-friendly message templates that produce actionable guidance without requiring shape authors to write custom messages

**Click-to-Edit Workflow:**
- **LINT-11**: User can click any lint result row and the corresponding object opens in a dockview pane (or focuses the existing pane if already open), scrolled/focused to the relevant field
- **LINT-12**: After editing and saving the object, the lint view updates to reflect whether the issue is resolved, removed from the list, or still present
- **LINT-13**: User can work through lint results sequentially: fix one issue, see it disappear from the global list, click the next issue, fix it -- a continuous triage workflow without navigating away from the lint view

Do NOT mark any of these as complete (no `[x]`). Use `- [ ]` for all. Do NOT add them to the Traceability table yet (no phases assigned).

Also add to the "Out of Scope" table:
| Automated lint auto-fix (programmatic correction of violations) | Too risky -- automated edits bypass user intent; fix guidance is sufficient |
| Custom user-defined validation rules beyond SHACL | SHACL shapes are the validation language; custom rules belong in Mental Model shapes |
| Cross-object relationship validation (e.g., orphan detection) | Distinct feature from per-object SHACL validation; future graph-level health check |
  </action>
  <verify>grep -c "LINT-" .planning/REQUIREMENTS.md should return 13. grep "Global Lint Status" .planning/REQUIREMENTS.md should match the section header.</verify>
  <done>13 LINT-* requirements defined across 4 feature areas under Future Requirements, plus 3 out-of-scope entries. No requirements marked complete. No traceability entries added.</done>
</task>

<task type="auto">
  <name>Task 2: Add Global Lint Status future milestone to ROADMAP.md and future-milestones.md</name>
  <files>.planning/ROADMAP.md, .planning/research/future-milestones.md</files>
  <action>
**Part A: Update ROADMAP.md**

Under the `## Milestones` list at the top, add after the existing future milestones:
```
- (future) **Global Lint Status** -- Workspace-wide SHACL validation dashboard with filtering, fix guidance, and click-to-edit inline triage workflow
```

Then add a new section after the existing "(Future) SPARQL Interface" section (before the Progress table):

```
### (Future) Global Lint Status

**Milestone Goal:** Provide a global view of SHACL validation health across the entire knowledge base. Users can see all violations, warnings, and infos at a glance, filter and search results, read actionable fix guidance for each issue, and click directly into the offending object's edit form to resolve issues in a continuous triage workflow.

**Depends on:** v2.3 complete (dockview panels provide the panel infrastructure for the lint view; object view redesign provides the field-focus jump target)

**Builds on existing infrastructure:**
- `ValidationService` + `AsyncValidationQueue` (backend/app/services/validation.py, backend/app/validation/queue.py) -- already runs pyshacl after every commit
- `ValidationReport` / `ValidationResult` dataclasses (backend/app/validation/report.py) -- already parse per-result severity, focus_node, path, message, source_shape, constraint_component
- `lint_panel.html` -- existing per-object lint tab with jumpToField() click handler
- `/api/validation/latest` endpoint -- existing polling endpoint for latest report summary
- SHACL shapes in Mental Model packages (orig_specs/models/*/shapes.ttl)

**Estimated Phases (sketch -- to be refined during milestone planning):**

1. **Global Validation API and Data Model** -- Extend the validation pipeline to store per-object, per-result detail (not just aggregate counts) in a queryable format; new API endpoints for listing all results with pagination
   - Requirements: LINT-01, LINT-02
   - Key risk: Performance of full-graph SHACL validation at scale (hundreds of objects); may need incremental validation (only re-validate objects touched by the commit) rather than full re-validation
   - Research needed: pyshacl incremental validation capabilities; whether to store individual ValidationResult triples in the triplestore or use SQLAlchemy for fast querying
   - Likely approach: Store individual ValidationResult records in a `urn:sempkm:lint-results` named graph with focus_node, severity, path, message, source_shape; or use a new SQLAlchemy model for SQL-level filtering/pagination

2. **Global Lint Dashboard UI** -- Dockview panel (or dedicated page accessible from sidebar/Command Palette) showing a filterable, searchable list of all validation results across all objects with summary counts
   - Requirements: LINT-03, LINT-04, LINT-05, LINT-06, LINT-07
   - Key risk: Rendering performance for large result sets; need virtual scrolling or pagination for 100+ results
   - Likely approach: htmx-driven table with server-side filtering/sorting; severity filter toggles, type dropdown from ModelRegistry, keyword search input; summary badges in status bar or sidebar
   - Design note: Follow existing SemPKM patterns (htmx partials, Lucide icons, CSS custom properties) -- not a JS framework component

3. **Fix Guidance Engine** -- Generate human-readable, actionable fix messages from SHACL constraint metadata; built-in templates for common constraint types; Mental Model shape authors can provide custom sh:description text
   - Requirements: LINT-08, LINT-09, LINT-10
   - Key risk: Message quality for complex constraints (sh:or, sh:qualifiedValueShape, custom SPARQL constraints); 80/20 rule -- handle the 10 most common constraint components well, fallback gracefully for exotic ones
   - Research needed: Full inventory of SHACL constraint components used in existing shapes; whether sh:description and sh:name are consistently populated in community SHACL shape sets
   - Likely approach: FixGuidanceService with a template registry mapping sh:sourceConstraintComponent URIs to message templates; templates use shape metadata (sh:name, sh:description, sh:minCount value, sh:datatype value) as interpolation variables

4. **Click-to-Edit Inline Triage Workflow** -- Each lint result row is a clickable link that opens (or focuses) the object in a dockview pane and scrolls to the relevant field; after save, lint view reflects the updated state
   - Requirements: LINT-11, LINT-12, LINT-13
   - Key risk: Field-focus accuracy (property path to DOM element mapping); the existing jumpToField() function uses property path matching which may need hardening for nested shapes or multi-valued fields
   - Depends on: Phase 1 (results data), Phase 2 (lint dashboard UI), Phase 3 (fix guidance)
   - Likely approach: Extend existing jumpToField() into a workspace-level function that can open-then-focus; use sempkm:tab-activated event to trigger scroll-to-field after panel loads; lint panel listens for save events to refresh its result list
```

Add to the roadmap footer:
```
*Future Global Lint Status milestone documented: 2026-03-03 -- 4 phase sketches, 13 requirements (LINT-01 through LINT-13)*
```

**Part B: Update future-milestones.md**

Add a new section in `.planning/research/future-milestones.md` BEFORE the "Research Artifacts" section at the bottom. Use the same structure as the existing "Collaboration & Federation" and "Identity & Authentication" sections:

```
## Milestone: (Future) Global Lint Status

**Goal:** Provide a workspace-wide SHACL validation dashboard so users can see every violation, warning, and info across all objects at a glance, filter and search results, read actionable fix guidance, and click directly into the offending object to fix issues in a continuous triage workflow.

**Depends on:** v2.3 (dockview panel infrastructure, object view redesign for field-focus targets). Can start research independently.

**Builds on:** Existing `ValidationService` + `AsyncValidationQueue` pipeline (runs pyshacl after every EventStore.commit()), `ValidationReport`/`ValidationResult` dataclasses, per-object `lint_panel.html`, `/api/validation/latest` endpoint.

### Phase A: Global Validation Data Model and API

Extend the validation pipeline to persist per-object, per-result detail and expose it via paginated API endpoints.

- New storage: individual `ValidationResult` records queryable by focus_node, severity, path, constraint_component
- Storage options: RDF named graph (`urn:sempkm:lint-results`) vs. SQLAlchemy model — research trade-offs
- API: `GET /api/lint/results?severity=Violation&type=Note&page=1` with filtering, sorting, pagination
- Incremental validation: only re-validate objects whose triples changed in the commit (performance at scale)
- Existing `ValidationReportSummary` for aggregate counts remains; new detail layer adds per-result access

### Phase B: Global Lint Dashboard UI

Dockview panel or dedicated page showing all validation results across all objects.

- Summary bar: total violations / warnings / infos with color-coded badges
- Result list: table or card layout with object label, severity icon, property path, message, timestamp
- Filters: severity toggles, type dropdown (from ModelRegistry), keyword search
- Sorting: by severity, object name, property path, timestamp
- Pagination or virtual scroll for large result sets
- Status bar indicator: persistent badge showing knowledge base health at a glance
- Design: htmx partials + CSS custom properties, following existing SemPKM patterns

### Phase C: Fix Guidance Engine

Generate human-readable, actionable fix messages from SHACL shape metadata.

- Template registry: maps `sh:sourceConstraintComponent` URIs to message templates
- Built-in templates for top 10 constraint types:
  - `sh:MinCountConstraintComponent` → "This field requires at least {minCount} value(s) -- add a {propertyName} to fix"
  - `sh:MaxCountConstraintComponent` → "This field allows at most {maxCount} value(s) -- remove extras to fix"
  - `sh:DatatypeConstraintComponent` → "Expected {datatype} but got {actualValue} -- update the value format"
  - `sh:PatternConstraintComponent` → "Value must match pattern {pattern} -- check formatting"
  - `sh:ClassConstraintComponent` → "Value must be an instance of {class} -- select the right type"
  - `sh:MinLengthConstraintComponent`, `sh:MaxLengthConstraintComponent`, `sh:InConstraintComponent`, `sh:NodeKindConstraintComponent`, `sh:HasValueConstraintComponent`
- Shape-author override: if `sh:description` is set on the property shape, use it as the guidance message
- Mental Model helptext: models can provide `sempkm:fixGuidance` annotations on shapes for domain-specific advice
- Graceful fallback: unknown constraint types get "Constraint violated on {path} -- check the value against the shape definition"

### Phase D: Click-to-Edit Triage Workflow

Wire the global lint dashboard to the object editing workflow for continuous issue resolution.

- Click a lint result row → open object in dockview pane (or focus existing pane) → scroll to field
- Extend `jumpToField()` to work cross-pane (currently only works within the active object's lint tab)
- After save: lint dashboard refreshes to show updated results (resolved issues disappear)
- Sequential triage: user works through list top-to-bottom, fixing each issue without leaving the lint view
- Keyboard navigation: arrow keys through lint results, Enter to open, Escape to return to lint view

### What NOT to Build
- Auto-fix engine (programmatic correction of violations) -- too risky, bypasses user intent
- Custom validation rules outside SHACL -- SHACL is the constraint language, extend via shapes
- Cross-object relationship validation (orphan detection, referential integrity) -- separate graph-health feature
- Real-time collaborative lint (multi-user live updates) -- depends on Collaboration milestone
```

Do NOT add phase numbers (these are future, unnumbered). Do NOT add these to the Progress table. Keep the "(Future)" prefix to distinguish from committed phases.
  </action>
  <verify>grep "Global Lint Status" .planning/ROADMAP.md should return at least 2 matches (milestone list + section header). grep -c "LINT-" .planning/ROADMAP.md should return at least 4 (one per phase sketch). grep "Global Lint" .planning/research/future-milestones.md should return at least 1 match.</verify>
  <done>Future Global Lint Status milestone documented in ROADMAP.md with milestone goal, dependency note, 4 phase sketches with requirement mappings, key risks, and research needs identified per phase. future-milestones.md updated with detailed phase descriptions including implementation approaches and "What NOT to Build" section.</done>
</task>

</tasks>

<verification>
1. `grep -c "LINT-" .planning/REQUIREMENTS.md` returns 13
2. `grep -c "LINT-" .planning/ROADMAP.md` returns >= 4
3. `grep "Global Lint Status" .planning/ROADMAP.md` matches milestone entry
4. `grep "Global Lint" .planning/research/future-milestones.md` matches milestone section
5. No `[x]` markers on any LINT-* requirement (all are future/unchecked)
6. No LINT-* entries in the Traceability table (no phases assigned yet)
7. Out of Scope table includes auto-fix, custom rules, and cross-object validation entries
8. Existing content in all three files is unchanged
</verification>

<success_criteria>
- 13 LINT-* requirements documented across 4 feature areas in REQUIREMENTS.md
- Future milestone with 4 phase sketches in ROADMAP.md
- Detailed milestone section with phase descriptions in future-milestones.md
- All requirements are `[ ]` (not started), none in traceability table
- Phase sketches include key risks, research needs, and implementation approaches
- References to existing validation infrastructure are accurate (ValidationService, AsyncValidationQueue, lint_panel.html, /api/validation/latest)
- Existing content in ROADMAP.md, REQUIREMENTS.md, and future-milestones.md is unchanged
</success_criteria>

<output>
After completion, create `.planning/quick/22-plan-future-milestone-for-global-lint-st/22-SUMMARY.md`
</output>
