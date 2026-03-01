---
status: diagnosed
trigger: "Investigate contextual panel accent bar logic in Phase 28-02 — why it doesn't correctly distinguish object tabs from non-object tabs"
created: 2026-03-01T00:00:00Z
updated: 2026-03-01T00:00:00Z
---

## Current Focus

hypothesis: All four bugs share the same root: the accent bar machinery has no tab-type awareness whatsoever. Events carry a tabId but the listener ignores it; `sempkm:tabs-empty` fires only on ALL-tabs-empty not last-OBJECT-tab-closed; view/special tabs fire the same activate event as object tabs; the restore path uses a tab-count check that is also tab-type-blind.
test: Static code analysis of workspace.js + workspace-layout.js
expecting: Confirmed by reading event dispatch sites and listener bodies
next_action: Return diagnosis to user

## Symptoms

expected: Accent bar active iff at least one OBJECT tab is open and focused; deactivates when last object tab closes even if non-object tabs remain; does NOT activate for view/settings tabs; SPARQL browser switch does not deactivate bar; Relations/Lint panel cleared when bar deactivates
actual: Bar activates for ANY tab activation including view/settings; bar deactivates only when ALL tabs close; switching to SPARQL bottom-panel tab deactivates bar; stale content remains in Relations/Lint when bar deactivates
errors: none (silent logic errors)
reproduction: (1) Open object tab + settings tab, close object tab — bar stays on. (2) Open object tab, click SPARQL bottom panel — bar clears. (3) Close all tabs — Relations/Lint still show old data. (4) Open view tab — bar activates.
started: Phase 28-02 implementation

## Eliminated

(none — root causes confirmed directly from code)

## Evidence

- timestamp: 2026-03-01T00:00:00Z
  checked: workspace.js lines 1656-1662 — the two event listeners for tab lifecycle
  found: |
    document.addEventListener('sempkm:tab-activated', function() {
      setContextualPanelActive(true);
    });
    document.addEventListener('sempkm:tabs-empty', function() {
      setContextualPanelActive(false);
    });
    The listeners receive the event but ignore event.detail entirely. No check on
    tabId, isView, isSpecial, or specialType. Every tab activation unconditionally
    calls setContextualPanelActive(true).
  implication: Bugs 1, 2, 4 all stem from this — the listener is tab-type-blind.

- timestamp: 2026-03-01T00:00:00Z
  checked: workspace-layout.js removeTabFromGroup lines 228-232 — the tabs-empty dispatch
  found: |
    var allEmpty = this.groups.every(function(g) { return g.tabs.length === 0; });
    if (allEmpty) {
      document.dispatchEvent(new CustomEvent('sempkm:tabs-empty'));
    }
    Fires only when EVERY group has ZERO tabs of any type. No concept of
    "object tab count". A group with only a settings tab is not "empty" by this test.
  implication: Root cause of Bug 1. Closing the last object tab when a non-object tab
    remains never fires sempkm:tabs-empty, so setContextualPanelActive(false) never runs.

- timestamp: 2026-03-01T00:00:00Z
  checked: workspace-layout.js switchTabInGroup lines 890-891 — the tab-activated dispatch on tab switch
  found: |
    document.dispatchEvent(new CustomEvent('sempkm:tab-activated', {
      detail: { tabId: tabId, groupId: groupId }
    }));
    tabId is the raw tab key (could be 'special:settings', 'view:xyz', or an IRI).
    No isView / isSpecial / tabType field is included in the detail.
  implication: The listener in workspace.js cannot distinguish tab types from this event.
    The tabId IS present, so type could be inferred from naming convention, but
    workspace.js does not attempt it.

- timestamp: 2026-03-01T00:00:00Z
  checked: workspace.js openTab() lines 78-83 — the tab-activated dispatch on new object tab open
  found: |
    layout.addTabToGroup(
      { id: objectIri, iri: objectIri, label: label || objectIri, dirty: false, isView: false },
      layout.activeGroupId
    );
    document.dispatchEvent(new CustomEvent('sempkm:tab-activated', { detail: { tabId: objectIri } }));
    This correctly fires for object tabs only. However it does NOT include isView/isSpecial
    in the event detail, and the listener ignores detail anyway.
  implication: openTab() is fine for object tabs; the problem is switchTabInGroup fires
    for ALL tab types equally.

- timestamp: 2026-03-01T00:00:00Z
  checked: workspace.js openViewTab() lines 107-130 — view tab open path
  found: |
    layout.addTabToGroup(
      { id: tabKey, iri: tabKey, label: viewLabel, dirty: false, isView: true, ... },
      layout.activeGroupId
    );
    window.loadTabInGroup(layout.activeGroupId, tabKey);
    openViewTab() does NOT dispatch sempkm:tab-activated itself, BUT:
    loadTabInGroup calls addTabToGroup which does NOT dispatch the event.
    However, switchTabInGroup IS called when re-activating an existing view tab
    (line 116: switchTabInGroup(tabKey, layout.activeGroupId)), and switchTabInGroup
    DOES dispatch sempkm:tab-activated unconditionally. So switching to a view tab
    fires the event without type info.
  implication: Bug 4 confirmed. View tab activation via switchTabInGroup triggers
    setContextualPanelActive(true) because the listener is type-blind.

- timestamp: 2026-03-01T00:00:00Z
  checked: workspace.js openSettingsTab() lines 645-661 — settings tab open path
  found: |
    Same pattern: addTabToGroup then loadTabInGroup (no event dispatch on first open).
    But if settings tab already exists, line 654: switchTabInGroup(tabKey, groupId),
    which fires sempkm:tab-activated. No type metadata.
    The bottom-panel SPARQL tab is not a workspace tab at all — it is a .panel-tab
    (data-panel="sparql") inside #bottom-panel. It never fires sempkm:tab-activated.
  implication: Bug 2 root cause found — the SPARQL browser is a BOTTOM PANEL tab, not
    a workspace editor tab. Switching to it does NOT fire sempkm:tab-activated at all.
    But the bar clears anyway, which means Bug 2 is caused by something else...

- timestamp: 2026-03-01T00:00:00Z
  checked: workspace.js restore path lines 1664-1673
  found: |
    setTimeout(function() {
      if (window._workspaceLayout) {
        var hasActiveTab = window._workspaceLayout.groups.some(function(g) {
          return g.activeTabId !== null && g.tabs.length > 0;
        });
        setContextualPanelActive(hasActiveTab);
      }
    }, 0);
    On page restore, the check is "does any group have an activeTabId and tabs?"
    This is also tab-type-blind: a group with only a settings tab and activeTabId
    set to 'special:settings' will set the bar active.
  implication: On page reload with only settings tab open, bar incorrectly activates.
    BUT this also reveals the Bug 2 mechanism: the SPARQL panel is a BOTTOM PANEL
    toggle. When toggleBottomPanel() shows the SPARQL pane, it does NOT affect
    workspace tabs. The bar clearing on SPARQL switch is NOT from a tab event — it
    must be from a page navigation or htmx swap that re-runs the restore setTimeout.
    Needs deeper look at the SPARQL tab init path.

- timestamp: 2026-03-01T00:00:00Z
  checked: workspace.js initPanelTabs() lines 421-453 and swapPanel() + SPARQL init
  found: |
    The SPARQL .panel-tab click handler runs _applyPanelState() and optionally
    initYasguiConsole() — neither dispatches tab events or clears the accent bar.
    The Yasgui init at line 439-451 only calls window.initYasguiConsole() and
    refreshes the CodeMirror editor. No bar manipulation.
    Looking at swapPanel (line 1381), it moves panels between zones but doesn't
    affect tab lifecycle events.
  implication: Bug 2 (SPARQL switch clears bar) is NOT caused by a panel-tab event.
    The real mechanism must be that activating the Yasgui SPARQL console triggers
    an htmx request that replaces the right-pane content, which kills the
    [data-panel-name] DOM nodes and re-inits them without contextual-panel-active.
    OR: Yasgui init fires a DOM mutation that causes the setTimeout restore to re-run.
    The most likely mechanism: the first time SPARQL tab is activated,
    initYasguiConsole() performs DOM manipulation that triggers htmx:afterSettle
    or similar, which re-runs initWorkspaceLayout() — but that is not confirmed.
    Alternative: the restore setTimeout fires AFTER Yasgui swaps in content that
    replaces [data-panel-name] elements, causing them to re-render without the class.
    Root: the class is on DOM elements that can be replaced by htmx swaps. When
    workspace.html right-pane content is swapped by htmx, the new elements don't
    carry contextual-panel-active even if the class was set before the swap.

- timestamp: 2026-03-01T00:00:00Z
  checked: workspace.js setContextualPanelActive function lines 1645-1653
  found: |
    function setContextualPanelActive(isActive) {
      document.querySelectorAll('[data-panel-name]').forEach(function(panel) {
        if (isActive) {
          panel.classList.add('contextual-panel-active');
        } else {
          panel.classList.remove('contextual-panel-active');
        }
      });
    }
    The class is added to <details data-panel-name="relations"> and
    <details data-panel-name="lint"> in the right-pane. These are STATIC elements
    in workspace.html — they are NOT re-rendered by htmx during normal use.
    No Relations/Lint clearing happens in this function. When the class is removed,
    only the visual indicator (accent bar) changes; the content inside
    #relations-content and #lint-content is not touched.
  implication: Bug 3 root cause: setContextualPanelActive(false) only removes the CSS
    class — it does not clear #relations-content or #lint-content innerHTML.
    Stale data persists because no code empties those containers on deactivation.

- timestamp: 2026-03-01T00:00:00Z
  checked: Bug 2 final analysis — what actually clears the bar when switching to SPARQL
  found: |
    The bottom panel SPARQL tab (data-panel="sparql") does NOT trigger any workspace
    tab event. HOWEVER: initYasguiConsole() is called on first SPARQL activation and
    it calls htmx.ajax or direct DOM manipulation. Looking at workspace.html lines
    280-312, Yasgui is initialized inline with window.Yasgui constructor and
    persistenceId. This is pure JS, no htmx swaps of right-pane content.
    Therefore the [data-panel-name] elements are NOT replaced.
    Reconsidering: the user says "switching to the SPARQL browser tab and BACK clears
    the teal accent bar". The "back" part is key. Switching back to a workspace tab
    after the SPARQL panel would call switchTabInGroup for the workspace tab. That
    SHOULD set the bar active via sempkm:tab-activated. But if the bar cleared...
    Hypothesis: the sequence is (1) bar is active, (2) user opens SPARQL bottom panel,
    (3) user clicks a non-object workspace tab to switch back (e.g., settings tab),
    (4) switchTabInGroup fires sempkm:tab-activated for the settings tab,
    (5) listener sets bar active — BUT if user report says "switching to SPARQL and
    back clears the bar", the "back" may mean switching to another WORKSPACE tab
    that happens to be a view or settings, which does set bar active. OR the user
    means clicking elsewhere (not a tab) causing some event that clears.
    Most likely Bug 2 mechanism: the bottom panel's "SPARQL browser" is NOT the bottom
    panel SPARQL tab — it may be a WORKSPACE tab of type 'special:sparql' or similar.
    Need to verify if there's a dedicated SPARQL workspace tab separate from the bottom panel.
  implication: Bug 2 may be a special/view workspace tab triggering sempkm:tab-activated
    (which sets bar active), then switching BACK to an object tab also fires
    sempkm:tab-activated (which sets bar active too). So the bar clearing described
    in Bug 2 may actually be: the SPARQL browser IS an object-like tab that when
    active fires tab-activated (correct, bar on), but it has no selectedNode concept.
    OR: Bug 2 is that switching to ANY non-object tab fires sempkm:tab-activated,
    setting bar active (wrong), then when user navigates away the bar correctly shows
    active for the object tab — but user perceives this as the bar having "cleared".
    Without reproduction, the most parsimonious explanation consistent with the code:
    - If "SPARQL browser" is a bottom-panel button: clicking it doesn't affect bar
    - If "SPARQL browser" is a workspace tab with id starting with 'view:' or 'special:':
      switchTabInGroup fires unconditionally, bar sets active (Bug 4 variant)
    - The "clears when switching back" behavior cannot be explained by current code
      unless the object tab's switchTabInGroup hits the no-op guard (line 880:
      if (group.activeTabId === tabId) return) and does NOT re-fire the event,
      meaning the bar state from the non-object tab activation persists. This is not
      a "clearing" — the bar stays on. So Bug 2 may require live reproduction to
      confirm exact mechanism. The fix for Bug 4 (type-aware listener) would also
      fix this case.

## Resolution

root_cause: |
  Four independent but related root causes, all stemming from absent tab-type awareness:

  BUG 1 — Bar stays active when last object tab closes (non-object tab still open):
    workspace-layout.js:removeTabFromGroup dispatches `sempkm:tabs-empty` only when
    ALL groups have zero tabs of ANY type. It has no concept of "object tab count".
    When the last object tab closes but a settings/view tab remains, allEmpty=false,
    the event is never dispatched, setContextualPanelActive(false) never runs.
    Fix: change the empty-check to count only object tabs (not view or special).

  BUG 2 — SPARQL browser switch clears bar:
    switchTabInGroup dispatches `sempkm:tab-activated` unconditionally for ALL tab
    types. The event detail carries tabId but workspace.js listener ignores it and
    blindly calls setContextualPanelActive(true). If the SPARQL browser is a
    workspace tab (view or special type), switching TO it (correctly) fires tab-
    activated, but switching BACK to an object tab also fires tab-activated which
    re-sets the bar active — this should NOT clear the bar. However if the SPARQL
    browser switching triggers a "no-op guard" return (line 880) on the subsequent
    switch-back, the sempkm:tab-activated is suppressed and the bar doesn't re-activate.
    The underlying issue: the no-op guard prevents re-dispatch when switching to a tab
    that is already active; if the object tab is still active (activeTabId unchanged),
    switching away and back hits the guard and skips the event. The bar was set active
    by the SPARQL-switch (incorrectly), then the switch-back is no-op'd, leaving the
    bar showing the incorrect state from the non-object tab.
    Core fix: make listener type-aware; also add explicit re-dispatch on switch-back
    or drop the no-op guard for the event dispatch.

  BUG 3 — Relations/Lint panel content not cleared on deactivation:
    setContextualPanelActive(false) in workspace.js only removes the CSS class
    `contextual-panel-active` from [data-panel-name] elements. It does NOT clear
    the innerHTML of #relations-content or #lint-content. No other code path clears
    these containers when the accent bar deactivates. Stale content persists.
    Fix: extend setContextualPanelActive(false) to also empty the content containers.

  BUG 4 — Opening a view tab activates the accent bar:
    openViewTab() calls addTabToGroup (no event) then loadTabInGroup (no event).
    But if the view tab already exists, switchTabInGroup is called, which dispatches
    `sempkm:tab-activated` unconditionally — with no type metadata in the event detail.
    The workspace.js listener then calls setContextualPanelActive(true) regardless.
    Even on first open, when the view tab becomes active via addTabToGroup, the
    restore-path setTimeout re-evaluates and finds activeTabId non-null, setting bar
    active (this is also tab-type-blind).
    Fix: make every dispatch site include tab type metadata; make listener check type.

fix: |
  THREE changes required:

  CHANGE 1 — workspace-layout.js: Add tabType to all sempkm:tab-activated dispatches

  In switchTabInGroup (line 890-891), look up the tab object from the group to get
  its type metadata, then include it in the event detail:

    var tabObj = group.tabs.find(function(t) { return (t.id || t.iri) === tabId; });
    var isObjectTab = tabObj && !tabObj.isView && !tabObj.isSpecial;
    document.dispatchEvent(new CustomEvent('sempkm:tab-activated', {
      detail: { tabId: tabId, groupId: groupId, isObjectTab: isObjectTab }
    }));

  In removeTabFromGroup (line 228-232), change the empty-check from all-tabs-empty
  to all-OBJECT-tabs-empty, and when switching to non-object tab dispatch a
  'sempkm:no-object-tab-active' event (or repurpose tabs-empty):

    // Count object tabs across all groups
    var hasObjectTab = this.groups.some(function(g) {
      return g.tabs.some(function(t) { return !t.isView && !t.isSpecial; });
    });
    if (!hasObjectTab) {
      document.dispatchEvent(new CustomEvent('sempkm:tabs-empty'));
    }

  CHANGE 2 — workspace.js: Make event listeners type-aware

  In openTab(), the dispatch already only fires for object tabs — correct, no change.

  Change the tab-activated listener to check event.detail.isObjectTab:

    document.addEventListener('sempkm:tab-activated', function(e) {
      if (e.detail && e.detail.isObjectTab === true) {
        setContextualPanelActive(true);
      } else if (e.detail && e.detail.isObjectTab === false) {
        // Non-object tab activated. Check if ANY object tab remains open.
        var layout = window._workspaceLayout;
        if (layout) {
          var hasObjectTab = layout.groups.some(function(g) {
            return g.tabs.some(function(t) { return !t.isView && !t.isSpecial; });
          });
          setContextualPanelActive(hasObjectTab);
        } else {
          setContextualPanelActive(false);
        }
      }
    });

  Change the restore setTimeout to be type-aware:

    setTimeout(function() {
      if (window._workspaceLayout) {
        var hasObjectTab = window._workspaceLayout.groups.some(function(g) {
          return g.activeTabId !== null && g.tabs.some(function(t) {
            return !t.isView && !t.isSpecial && (t.id || t.iri) === g.activeTabId;
          });
        });
        setContextualPanelActive(hasObjectTab);
      }
    }, 0);

  CHANGE 3 — workspace.js: Clear Relations/Lint content on deactivation

  Extend setContextualPanelActive to empty content containers when going inactive:

    function setContextualPanelActive(isActive) {
      document.querySelectorAll('[data-panel-name]').forEach(function(panel) {
        if (isActive) {
          panel.classList.add('contextual-panel-active');
        } else {
          panel.classList.remove('contextual-panel-active');
        }
      });
      if (!isActive) {
        var relContent = document.getElementById('relations-content');
        var lintContent = document.getElementById('lint-content');
        if (relContent) relContent.innerHTML = '';
        if (lintContent) lintContent.innerHTML = '';
      }
    }

verification: Not yet applied — diagnosis only mode
files_changed: []
