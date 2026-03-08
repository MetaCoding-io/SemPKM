---
phase: quick-29
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - e2e/tests/13-v24-coverage/vfs-browser.spec.ts
  - e2e/tests/13-v24-coverage/admin-entailment.spec.ts
  - e2e/tests/13-v24-coverage/crossfade-and-misc.spec.ts
autonomous: true
requirements: [VFS-BROWSER, ADMIN-ENTAILMENT, INFERRED-DISPLAY, CROSSFADE-TOGGLE, CLEAR-RELOAD]
must_haves:
  truths:
    - "VFS browser opens from sidebar and shows model/type/object tree"
    - "Admin entailment config loads with toggle checkboxes and examples"
    - "Inferred badge appears on relations panel after inference run"
    - "Read/edit crossfade toggle works (not 3D flip)"
    - "Clear & Reload button exists in user popover"
  artifacts:
    - path: "e2e/tests/13-v24-coverage/vfs-browser.spec.ts"
      provides: "VFS browser e2e tests"
    - path: "e2e/tests/13-v24-coverage/admin-entailment.spec.ts"
      provides: "Admin entailment config e2e tests"
    - path: "e2e/tests/13-v24-coverage/crossfade-and-misc.spec.ts"
      provides: "Crossfade toggle, inferred display, clear-reload tests"
  key_links:
    - from: "e2e/tests/13-v24-coverage/vfs-browser.spec.ts"
      to: "/browser/vfs"
      via: "page.goto and htmx navigation"
    - from: "e2e/tests/13-v24-coverage/admin-entailment.spec.ts"
      to: "/admin/models/basic-pkm/entailment"
      via: "page.goto"
---

<objective>
Add e2e test coverage for v2.4 features that currently have no or stale tests: VFS browser, admin entailment config, inferred triple display, crossfade toggle, and clear-reload button.

Purpose: Close coverage gaps identified in v2.4 gap analysis.
Output: 3 new test files in e2e/tests/13-v24-coverage/ covering all 5 gaps.
</objective>

<execution_context>
@/home/james/.claude/get-shit-done/workflows/execute-plan.md
@/home/james/.claude/get-shit-done/templates/summary.md
</execution_context>

<context>
@e2e/fixtures/auth.ts (auth fixtures: ownerPage, ownerSessionToken)
@e2e/fixtures/seed-data.ts (SEED objects, TYPES)
@e2e/helpers/selectors.ts (SEL shared selectors)
@e2e/helpers/wait-for.ts (waitForIdle, waitForWorkspace, waitForHtmxSettle)
@e2e/helpers/dockview.ts (openObjectTab, openViewTab)
@e2e/tests/09-inference/inference.spec.ts (inference test patterns)
@e2e/tests/05-admin/admin-models.spec.ts (admin test patterns)
@e2e/tests/01-objects/edit-object-ui.spec.ts (edit mode / crossfade patterns)

<interfaces>
<!-- Key selectors and patterns from existing tests -->

Auth fixtures provide: ownerPage (Page), ownerSessionToken (string), memberPage (Page)
BASE_URL = process.env.TEST_BASE_URL || 'http://localhost:3901'

VFS browser template selectors:
- data-testid="vfs-browser" on .vfs-container
- #vfs-tree-body (tree content area)
- .vfs-tree-loading (initial loading state)
- /browser/vfs (main route)
- /vfs/{model_id}/types (lazy-load types)
- /vfs/{model_id}/objects?type_iri=... (lazy-load objects)

Admin entailment config selectors:
- .entailment-config (form container)
- .entailment-toggle (each toggle row)
- .entailment-label (label with checkbox)
- .entailment-name (display name span)
- .entailment-type-label (code element with type label)
- .entailment-examples / .entailment-no-examples
- .entailment-example (individual example spans)
- Route: /admin/models/basic-pkm/entailment

Inferred badge:
- .inferred-badge on relations panel items (text: "inferred")
- Graph: edge.inferred-edge class with dashed line style

Crossfade toggle:
- .mode-toggle button (text: "Edit" / "Cancel")
- .object-face-edit.face-visible (edit mode active)
- .object-face-read:not(.face-hidden) (read mode active)
- Implementation is opacity crossfade, NOT 3D flip

Clear & Reload button:
- In sidebar user popover
- onclick="localStorage.clear(); location.reload();"
- Text: "Clear & Reload"
- .popover-item class
</interfaces>
</context>

<tasks>

<task type="auto">
  <name>Task 1: VFS browser and admin entailment config tests</name>
  <files>e2e/tests/13-v24-coverage/vfs-browser.spec.ts, e2e/tests/13-v24-coverage/admin-entailment.spec.ts</files>
  <action>
Create directory e2e/tests/13-v24-coverage/.

**vfs-browser.spec.ts** — VFS browser e2e tests:
1. Import from `../../fixtures/auth` (test, expect, BASE_URL) and `../../helpers/wait-for` (waitForIdle)
2. Test: "VFS browser page loads from direct URL" — `goto /browser/vfs`, wait for `[data-testid="vfs-browser"]`, verify `.vfs-tree-body` is visible
3. Test: "VFS browser loads from sidebar navigation" — goto `/browser/`, waitForSelector workspace, click sidebar link `a[href="/browser/vfs"]`, wait for `[data-testid="vfs-browser"]`
4. Test: "VFS tree shows model nodes after loading" — goto `/browser/vfs`, wait for tree body, wait for `.vfs-tree-loading` to disappear (use waitForFunction to check loading element is gone or tree has children), verify tree body contains model node elements (look for `.vfs-model-node` or tree item elements — inspect the JS that populates the tree). Since the tree is populated by `/js/vfs-browser.js`, wait up to 10s for child elements to appear in `#vfs-tree-body`. The model "Basic PKM" should appear as text content somewhere in the tree.
5. Test: "clicking a model node expands types" — After tree loads, find the Basic PKM model node and click it. Wait for type nodes to appear (Note, Project, Concept, Person). Verify at least one type label is visible.
6. Test: "clicking a type node shows objects" — After expanding model > type, click on a type (e.g., "Note"). Wait for object nodes to appear. Verify seed note titles appear (e.g., "Architecture Decision").

Note: The VFS tree uses htmx lazy-loading (`/vfs/{model_id}/types` and `/vfs/{model_id}/objects`). After clicking a node, use `waitForIdle(page)` then check for child content. If the tree uses `hx-trigger="click once"` or `hx-trigger="revealed"`, content loads on click/reveal. Use generous timeouts (10-15s) since the triplestore SPARQL queries may be slow.

**admin-entailment.spec.ts** — Admin entailment config e2e tests:
1. Import from `../../fixtures/auth` and `../../helpers/wait-for`
2. Test: "entailment config page loads for basic-pkm model" — `goto /admin/models/basic-pkm/entailment`, wait for `.entailment-config`, verify h1 contains "Inference Settings"
3. Test: "entailment toggles render with checkboxes" — On the entailment config page, verify `.entailment-toggle` count >= 2 (at least owl:inverseOf and sh:rule). Each toggle should have an `input[type="checkbox"]` inside `.entailment-label`.
4. Test: "entailment type labels show owl:inverseOf and sh:rule" — Verify `.entailment-type-label` elements contain text "owl:inverseOf" and "sh:rule" (or similar type labels from the template).
5. Test: "ontology examples render for inverseOf" — Find the entailment-toggle containing "inverseOf", verify it has `.entailment-examples` (not `.entailment-no-examples`), verify at least one `.entailment-example` span is visible.
6. Test: "save configuration button is present" — Verify `button[type="submit"]` with text "Save Configuration" exists in the form.

Note: The entailment config page may be loaded as a full page (with base.html extends) OR as an htmx partial (into #app-content). When navigating via goto, it renders as full page. Use `ownerPage.goto(BASE_URL + '/admin/models/basic-pkm/entailment')` for reliable full-page loads.
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM/e2e && npx playwright test tests/13-v24-coverage/vfs-browser.spec.ts tests/13-v24-coverage/admin-entailment.spec.ts --project=chromium --reporter=list 2>&1 | tail -30</automated>
  </verify>
  <done>VFS browser tests pass (page load, sidebar nav, tree hierarchy). Admin entailment config tests pass (page load, toggles, examples, save button).</done>
</task>

<task type="auto">
  <name>Task 2: Crossfade toggle, inferred display, and clear-reload tests</name>
  <files>e2e/tests/13-v24-coverage/crossfade-and-misc.spec.ts</files>
  <action>
**crossfade-and-misc.spec.ts** — Tests for crossfade toggle, inferred badge, and clear-reload button:

Import from `../../fixtures/auth` (test, expect, BASE_URL), `../../fixtures/seed-data` (SEED), `../../helpers/wait-for` (waitForIdle, waitForWorkspace), `../../helpers/dockview` (openObjectTab).

**Crossfade toggle tests (describe: "Read/Edit Crossfade Toggle"):**
1. Test: "crossfade toggle switches to edit mode" — goto /browser/, waitForWorkspace, openObjectTab with SEED.notes.architecture.iri. Click `.mode-toggle` (should say "Edit"). Wait for `.object-face-edit.face-visible`. Verify toggle text is "Cancel". Verify `[data-testid="object-form"]` is attached.
2. Test: "crossfade toggle returns to read mode" — Same setup, toggle to edit, then click Cancel. Wait for `.object-face-read:not(.face-hidden)`. Verify toggle text is "Edit". Verify `.markdown-body` is visible.
3. Test: "crossfade uses opacity transition not 3D transform" — After opening an object, check computed style of `.object-flip-container` — it should NOT have `transform-style: preserve-3d`. Check that `.object-face-read` and `.object-face-edit` use opacity for transitions. Use `page.evaluate` to check `getComputedStyle(el).transition` includes 'opacity'. This confirms the crossfade implementation, not 3D flip.

**Inferred badge tests (describe: "Inferred Triple Display"):**
1. Test: "inferred badge appears on relations panel after inference" — Create one-sided relationship via API (reuse the pattern from inference.spec.ts: create Project + Person, patch with hasParticipant, run inference). Then open the Person object in the workspace via openObjectTab. Wait for the relations panel to load (the right pane loads relations via htmx). Look for `.inferred-badge` in the relations panel. Verify it contains text "inferred".

Note: The relations panel loads lazily in the right pane. After opening an object tab, the right pane sections (relations, lint) load via htmx. Wait for `.relations-panel` to be visible, then check for `.inferred-badge`. If the right pane is not visible by default, it may need the object tab to be active — which it will be since we just opened it.

If the inferred badge test is flaky due to timing (inference must complete before viewing), use the API approach: POST /api/inference/run first, verify total_inferred > 0, THEN open the object.

**Clear & Reload button test (describe: "Clear & Reload Button"):**
1. Test: "clear and reload button exists in user popover" — goto /browser/, waitForWorkspace. Open the user popover by clicking the user avatar/button in the sidebar (look for `.user-avatar`, `.user-btn`, or the popover trigger — check sidebar template). The popover should contain a button with text "Clear & Reload". Verify the button has `.popover-item` class.

To find the user popover trigger, the sidebar has a user section. Look for elements like `#user-popover-trigger`, `.sidebar-user`, or a button that toggles the popover. The popover content is in `_sidebar.html` (not a separate file). The user popover is toggled by clicking on the user area in the sidebar bottom section.

Alternatively, just check that the popover content exists in the DOM (it may be hidden). Use `page.locator('.popover-item', { hasText: 'Clear' })` and verify it's attached (not necessarily visible until popover opens).
  </action>
  <verify>
    <automated>cd /home/james/Code/SemPKM/e2e && npx playwright test tests/13-v24-coverage/crossfade-and-misc.spec.ts --project=chromium --reporter=list 2>&1 | tail -30</automated>
  </verify>
  <done>Crossfade toggle tests pass (edit/cancel cycle, opacity check). Inferred badge test passes (badge visible after inference). Clear-reload button test passes (button exists in popover).</done>
</task>

</tasks>

<verification>
Run all new tests together:
```bash
cd /home/james/Code/SemPKM/e2e && npx playwright test tests/13-v24-coverage/ --project=chromium --reporter=list
```
All tests should pass. No existing tests should break (these are additive only).
</verification>

<success_criteria>
- 3 new test files created in e2e/tests/13-v24-coverage/
- VFS browser: page load, sidebar nav, model/type/object tree hierarchy tested
- Admin entailment config: page load, toggles, checkboxes, examples, save button tested
- Crossfade: edit/cancel toggle cycle tested, opacity (not 3D) verified
- Inferred badge: visible on relations panel after inference run
- Clear & Reload: button exists in user popover DOM
- All new tests pass on chromium project
</success_criteria>

<output>
After completion, create `.planning/quick/29-add-e2e-tests-for-v2-4-coverage-gaps-vfs/29-SUMMARY.md`
</output>
