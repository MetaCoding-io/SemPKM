/**
 * tutorials.js — Driver.js guided tour definitions for SemPKM.
 *
 * Exposes:
 *   window.startWelcomeTour()       — "Welcome to SemPKM" workspace orientation
 *   window.startCreateObjectTour()  — "Creating Your First Object" htmx-gated tour
 *   window.startDemoTour()          — "Demo Tour" 7-step auto-navigating tour for demo mode
 *   SemPKM.walkthroughPersonas      — persona walkthrough registry ("A day in the graph")
 *   SemPKM.startWalkthrough(personaId, chapterId?) — play one chapter or a persona's whole day
 *   SemPKM.startTourById(id)        — dispatcher used by ?tour=<id> and the command palette
 *   SemPKM.renderWalkthroughPicker(el) — persona/chapter picker for the Docs & Tutorials page
 *
 * Driver.js IIFE namespace: window['driver.js'].driver (not window.driver.driver)
 * Loaded after driver.js.iife.js in base.html.
 *
 * DOM selectors confirmed from template inspection (Phase 18 Plan 02):
 *   #app-sidebar        — _sidebar.html <aside id="app-sidebar">
 *   #nav-pane           — workspace.html <div id="nav-pane">
 *   #section-objects    — workspace.html <div id="section-objects">
 *   #editor-pane        — workspace.html <div id="editor-pane">
 *   .mode-toggle        — object_tab.html <button class="btn btn-sm mode-toggle">
 *   #right-pane         — workspace.html <div id="right-pane">
 *   ninja-keys          — workspace.html <ninja-keys>
 *   .type-picker        — type_picker.html <div class="type-picker">
 *   #object-form        — object_form.html <form id="object-form">
 */

(function () {
  'use strict';

  /**
   * Returns the Driver.js driver constructor from the IIFE global.
   * The IIFE exports as window.driver.js.driver (verified at runtime).
   */
  function getDriver() {
    return window.driver && window.driver.js && window.driver.js.driver;
  }

  // ---------------------------------------------------------------------------
  // Tour 1: Welcome to SemPKM
  // ---------------------------------------------------------------------------
  //
  // All elements in this tour are always-present stable DOM IDs in
  // workspace.html and _sidebar.html. No htmx gating needed.
  // The read/edit toggle and command palette steps use function form because:
  //   - The toggle button (.mode-toggle) only exists in the DOM when an object tab is open
  //   - ninja-keys registration timing is variable (custom element)
  //
  // Steps (10 total):
  //   1. sidebar             — workspace overview
  //   2. explorer pane       — nav tree introduction
  //   3. objects section     — expand a type node
  //   4. objects section     — click a leaf to open an object (instruction only, same element)
  //   5. editor pane         — objects open as tabs here
  //   6. read/edit toggle    — lazy (.mode-toggle), only present when object is open
  //   7. right pane          — context panel (relations + lint)
  //   8. command palette     — lazy, ninja-keys custom element
  //   9. save shortcut       — centered, no element, explains Ctrl+S
  //  10. closing card        — centered, done button only

  window.SemPKM.startWelcomeTour = function () {
    var driver = getDriver();
    if (!driver) {
      console.warn('[SemPKM] Driver.js not loaded — cannot start Welcome tour');
      return;
    }

    var driverObj = driver({
      showProgress: true,
      steps: [
        {
          element: '#app-sidebar',
          popover: {
            title: 'Welcome to SemPKM',
            description: 'This is your workspace sidebar. Use it to navigate between sections of your knowledge base.',
            side: 'right',
            align: 'start'
          }
        },
        {
          element: '#nav-pane',
          popover: {
            title: 'Explorer',
            description: 'Browse and open your knowledge objects here. Types are grouped into collapsible sections.',
            side: 'right',
            align: 'start'
          }
        },
        {
          element: '#section-objects',
          popover: {
            title: 'Object Types',
            description: 'Click any type header to expand it and reveal the objects of that type.',
            side: 'right',
            align: 'start'
          }
        },
        {
          element: '#section-objects',
          popover: {
            title: 'Opening an Object',
            description: 'Once a type is expanded, click any object in the list to open it in the editor. Try it now — click an item in the explorer, then press Next.',
            side: 'right',
            align: 'start'
          }
        },
        {
          element: '#editor-pane',
          popover: {
            title: 'Editor Area',
            description: 'The object you opened appears as a tab here. You can split the editor into multiple groups with Alt+\\.',
            side: 'left',
            align: 'start'
          }
        },
        {
          // Lazy: the read/edit toggle button (.mode-toggle) only exists in the DOM
          // when an object tab is open. Uses function form so Driver.js resolves
          // the element at step-render time, not at init.
          element: function () {
            return document.querySelector('.mode-toggle');
          },
          popover: {
            title: 'Read / Edit Toggle',
            description: 'Objects open in read mode by default. Click this button (or press Alt+E) to switch to edit mode where you can change properties and edit the body.',
            side: 'bottom',
            align: 'center'
          }
        },
        {
          element: '#right-pane',
          popover: {
            title: 'Context Panel',
            description: 'Related objects and validation results appear here for the active tab.',
            side: 'left',
            align: 'start'
          }
        },
        {
          // Lazy: ninja-keys custom element registration timing is variable.
          element: function () {
            return document.querySelector('ninja-keys');
          },
          popover: {
            title: 'Command Palette',
            description: 'Press Alt+K (or F1) to open the command palette. Search for any action, object, or view.',
            side: 'bottom',
            align: 'center'
          }
        },
        {
          // Centered — no element — explains Ctrl+S saving
          popover: {
            title: 'Saving Your Work',
            description: 'When you have made edits, press <strong>Alt+S</strong> to save. The tab\'s dirty indicator (a colored dot) clears after a successful save, and SHACL validation runs automatically.'
          }
        },
        {
          // No element = centered popover (tour end)
          popover: {
            title: "You're all set!",
            description: 'Explore the other tutorials on this page, or start creating objects with Alt+N.',
            showButtons: ['done']
          }
        }
      ]
    });

    driverObj.drive();
  };

  // ---------------------------------------------------------------------------
  // Tour 2: Creating Your First Object
  // ---------------------------------------------------------------------------
  //
  // This tour contains one htmx-gated step: after step 1 the user clicks Next
  // and the tour triggers showTypePicker() (htmx GET /browser/types → active
  // editor area innerHTML swap). The tour waits for htmx:afterSwap targeting
  // the active editor area before advancing to step 2 (type picker).
  //
  // Pitfall guard: check e.detail.target matches the active editor area element
  // (not just any htmx swap on the page) to prevent spurious advances from
  // unrelated swaps.
  //
  // Steps:
  //   1. Objects section → "click Next to open the type picker"
  //   2. Type picker (.type-picker) → "select a type"
  //   3. Object form (#object-form) → "fill in the fields"
  //   4. Save button (#object-form button[type=submit]) → "save your object"

  window.SemPKM.startCreateObjectTour = function () {
    var driver = getDriver();
    if (!driver) {
      console.warn('[SemPKM] Driver.js not loaded — cannot start Create Object tour');
      return;
    }

    var driverObj;

    driverObj = driver({
      showProgress: true,
      steps: [
        {
          element: '#section-objects',
          popover: {
            title: 'Step 1: Open Type Picker',
            description: 'The type picker lets you choose what kind of object to create. Click <strong>Next</strong> to open it now.',
            side: 'right',
            align: 'start',
            onNextClick: function () {
              // Get the active editor area (the htmx swap target for showTypePicker)
              var editorArea = typeof window.SemPKM.getActiveEditorArea === 'function'
                ? window.SemPKM.getActiveEditorArea()
                : document.getElementById('editor-area-group-1');

              // Trigger the type picker load via the global showTypePicker function
              if (typeof window.SemPKM.showTypePicker === 'function') {
                window.SemPKM.showTypePicker();
              }

              // Wait for the htmx swap that populates the editor area with the
              // type picker. Check target identity to avoid spurious advances
              // from unrelated swaps on the page.
              function afterSwapHandler(e) {
                if (e.detail && e.detail.target && editorArea && e.detail.target === editorArea) {
                  document.body.removeEventListener('htmx:afterSwap', afterSwapHandler);
                  driverObj.moveNext();
                }
              }
              document.body.addEventListener('htmx:afterSwap', afterSwapHandler);
            }
          }
        },
        {
          // Lazy: type picker is loaded asynchronously via htmx swap.
          element: function () {
            return document.querySelector('.type-picker');
          },
          popover: {
            title: 'Step 2: Choose a Type',
            description: 'Each card represents an object type from your installed Mental Model. Click the type you want to create.',
            side: 'right',
            align: 'start'
          }
        },
        {
          // Lazy: object form loads after selecting a type card.
          element: function () {
            return document.querySelector('#object-form');
          },
          popover: {
            title: 'Step 3: Fill In the Form',
            description: 'Complete the property fields. Required fields are marked. The body field at the bottom accepts Markdown.',
            side: 'right',
            align: 'start'
          }
        },
        {
          // Lazy: save button is inside the object form.
          element: function () {
            return document.querySelector('#object-form button[type="submit"]');
          },
          popover: {
            title: 'Step 4: Save Your Object',
            description: 'Click Save to create your object. It will appear in the explorer tree under its type.',
            side: 'top',
            align: 'center',
            showButtons: ['prev', 'done']
          }
        }
      ]
    });

    driverObj.drive();
  };

  // ---------------------------------------------------------------------------
  // Tour 3: Demo Tour (auto-navigation across workspace views)
  // ---------------------------------------------------------------------------
  //
  // 7-step guided demo for anonymous visitors on the public demo instance.
  // Auto-navigates between workspace views using existing globals:
  //   openGenericViewTab, openTab, toggleBottomPanel, openCanvasTab, openDashboardTab
  //
  // Each navigation step uses onNextClick + lazy element + setTimeout to handle
  // asynchronous DOM loading after view switches.
  //
  // Completion sets localStorage flag and dispatches custom event so the CTA
  // banner (rendered in workspace.html) can react.
  //
  // Steps:
  //   1. Explorer — browse objects by type
  //   2. Graph View — visualise knowledge graph
  //   3. Open an Object — typed properties and body
  //   4. Validation/Lint — SHACL data quality
  //   5. Spatial Canvas — infinite canvas
  //   6. Dashboard — cross-filtering views
  //   7. CTA — install prompt (centered, no element)

  // Well-known demo dashboard (must match seed script Phase 5)
  var DEMO_DASHBOARD_ID = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';
  var DEMO_DASHBOARD_NAME = 'Demo Dashboard';

  window.SemPKM.startDemoTour = function () {
    var driver = getDriver();
    if (!driver) {
      console.warn('[SemPKM] Driver.js not loaded — cannot start Demo tour');
      return;
    }

    SemPKM.debug('SemPKM', 'Demo tour started');

    var driverObj;

    driverObj = driver({
      showProgress: true,
      onDestroyStarted: function () {
        // Mark tour as completed and notify CTA banner
        localStorage.setItem('sempkm_demo_tour_done', '1');
        document.dispatchEvent(new CustomEvent('sempkm:demo-tour-done'));
        SemPKM.debug('SemPKM', 'Demo tour completed');
        driverObj.destroy();
      },
      steps: [
        // Step 1 — Explorer (always-present DOM element)
        // onNextClick navigates to graph view before advancing to step 2
        {
          element: '#section-objects',
          popover: {
            title: 'Your Knowledge Base',
            description: 'Your knowledge base has objects across 4 Mental Models — browse them by type, hierarchy, or tags.',
            side: 'right',
            align: 'start',
            onNextClick: function () {
              if (typeof window.SemPKM.openGenericViewTab === 'function') {
                window.SemPKM.openGenericViewTab('graph');
              }
              setTimeout(function () {
                driverObj.moveNext();
              }, 500);
            }
          }
        },
        // Step 2 — Graph View (navigated to by step 1's onNextClick)
        // onNextClick opens a seed object before advancing to step 3
        {
          element: function () {
            return document.querySelector('.group-editor-area');
          },
          popover: {
            title: 'Graph View',
            description: 'See your knowledge as an interconnected graph. Nodes represent objects and edges show relationships.',
            side: 'left',
            align: 'start',
            onPrevClick: function () {
              driverObj.movePrevious();
            },
            onNextClick: function () {
              if (typeof window.SemPKM.openTab === 'function') {
                window.SemPKM.openTab('urn:sempkm:model:basic-pkm:seed-note-architecture', 'Architecture Decision Records');
              }
              setTimeout(function () {
                driverObj.moveNext();
              }, 500);
            }
          }
        },
        // Step 3 — Object View (navigated to by step 2's onNextClick)
        // onNextClick opens the bottom panel before advancing to step 4
        {
          element: function () {
            return document.querySelector('.group-editor-area');
          },
          popover: {
            title: 'Object View',
            description: 'Every object has typed properties and a rich markdown body. Click the Edit button to modify.',
            side: 'left',
            align: 'start',
            onPrevClick: function () {
              driverObj.movePrevious();
            },
            onNextClick: function () {
              if (typeof window.SemPKM.toggleBottomPanel === 'function') {
                window.SemPKM.toggleBottomPanel();
              }
              setTimeout(function () {
                driverObj.moveNext();
              }, 500);
            }
          }
        },
        // Step 4 — Validation / Lint (opened by step 3's onNextClick)
        // onNextClick opens canvas before advancing to step 5
        {
          element: function () {
            return document.querySelector('#bottom-panel');
          },
          popover: {
            title: 'Validation & Lint',
            description: 'SHACL validation catches data quality issues automatically — overdue tasks, stale contacts, and more.',
            side: 'top',
            align: 'center',
            onPrevClick: function () {
              driverObj.movePrevious();
            },
            onNextClick: function () {
              if (typeof window.SemPKM.openCanvasTab === 'function') {
                window.SemPKM.openCanvasTab();
              }
              setTimeout(function () {
                driverObj.moveNext();
              }, 500);
            }
          }
        },
        // Step 5 — Spatial Canvas (navigated to by step 4's onNextClick)
        // onNextClick opens demo dashboard before advancing to step 6
        {
          element: function () {
            return document.querySelector('.group-editor-area');
          },
          popover: {
            title: 'Spatial Canvas',
            description: 'Arrange knowledge spatially on an infinite canvas. Add embeds, draw connections, resize freely.',
            side: 'left',
            align: 'start',
            onPrevClick: function () {
              driverObj.movePrevious();
            },
            onNextClick: function () {
              if (typeof window.SemPKM.openDashboardTab === 'function') {
                window.SemPKM.openDashboardTab(DEMO_DASHBOARD_ID, DEMO_DASHBOARD_NAME);
              }
              setTimeout(function () {
                driverObj.moveNext();
              }, 500);
            }
          }
        },
        // Step 6 — Dashboard (navigated to by step 5's onNextClick)
        {
          element: function () {
            return document.querySelector('.group-editor-area');
          },
          popover: {
            title: 'Dashboards',
            description: 'Build dashboards that combine views with cross-filtering. Click a table row to filter the connected graph.',
            side: 'left',
            align: 'start'
          }
        },
        // Step 7 — CTA (centered, no element)
        {
          popover: {
            title: 'Ready to Try SemPKM?',
            description: 'Install with Docker in 2 minutes. Visit <a href="https://github.com/SemPKM/sempkm" target="_blank" style="color:#60a5fa;text-decoration:underline;">github.com/SemPKM</a> to get started.',
            showButtons: ['done']
          }
        }
      ]
    });

    driverObj.drive();
  };

  // ---------------------------------------------------------------------------
  // Persona walkthroughs — "A day in the graph"
  // ---------------------------------------------------------------------------
  //
  // In-app counterpart of the website's scrollytelling walkthroughs
  // (docs/walkthroughs/index.html). Each *persona* (Alice the project lead,
  // Maya the researcher, ...) has an ordered list of *chapters*, each stamped
  // with a time of day. A chapter is a short Driver.js tour that auto-navigates
  // the real workspace (opens seed objects, views, bottom-panel tabs) and
  // narrates what the persona is doing at that hour.
  //
  // Chapters can be played one at a time or as the whole day in one run.
  // Completion is remembered per chapter in localStorage so the picker on the
  // Docs & Tutorials page shows progress.
  //
  // NOTE: "persona" here means a *user archetype* for onboarding. It is
  // unrelated to Workspace Personas (saved panel layouts, see persona/ and
  // docs/guide/30-personas.md).
  //
  // Public API (all on window.SemPKM):
  //   walkthroughPersonas            — the registry (array of persona objects)
  //   startWalkthrough(personaId, chapterId?) — play one chapter, or the whole day
  //   startTourById(id)              — 'welcome' | 'create-object' | 'demo' | '<persona>[:<chapter>]'
  //   renderWalkthroughPicker(el)    — render the persona/chapter picker into an element
  //   getWalkthroughProgress()       — { personaId: { chapterId: true } }
  //   resetWalkthroughProgress(personaId?)
  //
  // Adding a persona = adding one entry to PERSONAS below. Each chapter needs:
  //   id, time, title, summary      — copy shown in the picker and the chapter card
  //   enter(ctx)   (optional)       — navigation to perform when the chapter starts
  //   steps(ctx)                    — function returning Driver.js step objects
  // ctx exposes moveNext()/movePrevious() bound to the running driver, plus
  // helpers: open(iri,label), openView(renderer,typeIri), bottomTab(name),
  // editor() (active editor area element).

  var PROGRESS_KEY = 'sempkm_walkthrough_progress';
  var ACTIVE_PERSONA_KEY = 'sempkm_walkthrough_persona';
  var NAV_DELAY = 600; // ms to let htmx/dockview settle after a navigation call

  var BPKM = 'urn:sempkm:model:basic-pkm:';
  var RES = 'urn:sempkm:model:research:';

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // --- Progress persistence ---------------------------------------------------

  function readProgress() {
    try {
      return JSON.parse(localStorage.getItem(PROGRESS_KEY) || '{}') || {};
    } catch (e) {
      return {};
    }
  }

  function writeProgress(progress) {
    try {
      localStorage.setItem(PROGRESS_KEY, JSON.stringify(progress));
    } catch (e) { /* storage unavailable — progress is a convenience only */ }
    document.dispatchEvent(new CustomEvent('sempkm:walkthrough-progress', { detail: progress }));
  }

  function markChapterDone(personaId, chapterId) {
    var progress = readProgress();
    if (!progress[personaId]) progress[personaId] = {};
    if (progress[personaId][chapterId]) return;
    progress[personaId][chapterId] = true;
    writeProgress(progress);
  }

  function isChapterDone(personaId, chapterId) {
    var progress = readProgress();
    return Boolean(progress[personaId] && progress[personaId][chapterId]);
  }

  window.SemPKM.getWalkthroughProgress = readProgress;
  window.SemPKM.resetWalkthroughProgress = function (personaId) {
    if (!personaId) {
      writeProgress({});
      return;
    }
    var progress = readProgress();
    delete progress[personaId];
    writeProgress(progress);
  };

  // --- Navigation helpers shared by chapters ----------------------------------

  function callGlobal(name) {
    var fn = window.SemPKM[name];
    if (typeof fn !== 'function') return undefined;
    return fn.apply(null, Array.prototype.slice.call(arguments, 1));
  }

  function activeEditorArea() {
    return callGlobal('getActiveEditorArea')
      || document.querySelector('.group-editor-area')
      || document.getElementById('editor-pane');
  }

  // Select (and open) a bottom-panel tab by its data-panel name. Clicking the
  // tab button runs the same handler as a user click (initPanelTabs), so the
  // panel opens if collapsed and lazy content (event log, lint) loads.
  function selectBottomTab(panelName) {
    var btn = document.querySelector('.panel-tab[data-panel="' + panelName + '"]');
    if (btn) {
      btn.click();
      return true;
    }
    return false;
  }

  function isWorkspacePage() {
    return Boolean(window.SemPKM._dockview || document.getElementById('workspace'));
  }

  function findPersona(personaId) {
    for (var i = 0; i < PERSONAS.length; i++) {
      if (PERSONAS[i].id === personaId) return PERSONAS[i];
    }
    return null;
  }

  function findChapter(persona, chapterId) {
    for (var i = 0; i < persona.chapters.length; i++) {
      if (persona.chapters[i].id === chapterId) return persona.chapters[i];
    }
    return null;
  }

  // Resolve whether a Mental Model is installed. Resolves true on any error so
  // a transient API problem never blocks a walkthrough.
  function isModelInstalled(modelId) {
    if (!modelId) return Promise.resolve(true);
    var doFetch = typeof window.SemPKM.apiFetch === 'function'
      ? window.SemPKM.apiFetch('/api/models', { credentials: 'include', silent: true })
      : fetch('/api/models', { credentials: 'include' });
    return doFetch
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data || !Array.isArray(data.models)) return true;
        return data.models.some(function (m) { return m.model_id === modelId; });
      })
      .catch(function () { return true; });
  }

  function makeCtx(personaId, chapterId) {
    var ctx = {
      personaId: personaId,
      chapterId: chapterId,
      driver: null,
      moveNext: function () { if (ctx.driver) ctx.driver.moveNext(); },
      movePrevious: function () { if (ctx.driver) ctx.driver.movePrevious(); },
      // Run a navigation call, then advance once the DOM has settled.
      go: function (navigate) {
        return function () {
          try { navigate(); } catch (e) { SemPKM.debug('SemPKM', 'walkthrough navigation failed', e); }
          setTimeout(ctx.moveNext, NAV_DELAY);
        };
      },
      open: function (iri, label) { callGlobal('openTab', iri, label); },
      openView: function (renderer, typeIri) { callGlobal('openGenericViewTab', renderer, '', '', typeIri || ''); },
      bottomTab: selectBottomTab,
      editor: activeEditorArea
    };
    return ctx;
  }

  // --- Persona registry ---------------------------------------------------------

  var PERSONAS = [
    {
      id: 'alice',
      name: 'Alice',
      role: 'Project lead',
      icon: 'briefcase',
      model: 'basic-pkm',
      modelName: 'Basic PKM',
      tagline: 'From a stray standup note to a decision the whole team can trust — one day, one graph.',
      chapters: [
        {
          id: 'capture',
          time: '9:02',
          title: 'Capture without breaking stride',
          summary: 'Standup surfaces a decision worth keeping. Create a note in seconds — structure can wait until the meeting ends.',
          enter: function (ctx) {
            // Open the type picker in the active editor group. Advance is
            // handled by the chapter card's onNextClick (htmx-gated below).
          },
          steps: function (ctx) {
            return [
              {
                popover: {
                  title: 'Alt+N — create from anywhere',
                  description: 'Press <strong>Alt+K</strong> for the command palette or <strong>Alt+N</strong> to create an object straight away. Click <strong>Next</strong> and we\'ll open the type picker for you.',
                  onNextClick: function () {
                    var editorArea = activeEditorArea();
                    function afterSwap(e) {
                      if (e.detail && e.detail.target && editorArea && e.detail.target === editorArea) {
                        document.body.removeEventListener('htmx:afterSwap', afterSwap);
                        ctx.moveNext();
                      }
                    }
                    document.body.addEventListener('htmx:afterSwap', afterSwap);
                    if (typeof window.SemPKM.showTypePicker === 'function') {
                      window.SemPKM.showTypePicker();
                    } else {
                      document.body.removeEventListener('htmx:afterSwap', afterSwap);
                      ctx.moveNext();
                    }
                  }
                }
              },
              {
                element: function () { return document.querySelector('.type-picker'); },
                popover: {
                  title: 'Pick "Note"',
                  description: 'Every card is a type from an installed Mental Model. For a quick capture, <strong>Note</strong> is enough — click it, then press Next.',
                  side: 'right',
                  align: 'start'
                }
              },
              {
                element: function () { return document.querySelector('#object-form'); },
                popover: {
                  title: 'Type the thought',
                  description: 'A title is all Alice needs right now: <em>"Standup: switch persistence to event sourcing?"</em>. The body accepts Markdown whenever she comes back to it.',
                  side: 'right',
                  align: 'start'
                }
              },
              {
                element: function () { return document.querySelector('#object-form button[type="submit"]'); },
                popover: {
                  title: 'Save and move on',
                  description: 'Click <strong>Save</strong> (or press <strong>Alt+S</strong>). The note lands in the explorer under its type. Capture took seconds; the meeting goes on.',
                  side: 'top',
                  align: 'center'
                }
              }
            ];
          }
        },
        {
          id: 'type',
          time: '9:15',
          title: 'Give it a type',
          summary: 'Coffee in hand, the stray note becomes a real object. The form is generated from the schema — required fields, hints and validation included.',
          enter: function (ctx) {
            ctx.open(BPKM + 'seed-note-architecture', 'Architecture Decision: Event Sourcing');
          },
          steps: function (ctx) {
            return [
              {
                element: ctx.editor,
                popover: {
                  title: 'A typed object, not a loose file',
                  description: 'This is the decision Alice captured, now a <strong>Note</strong> from the Basic PKM model. Typed properties sit above a Markdown body — no template to maintain, no frontmatter convention to remember.',
                  side: 'left',
                  align: 'start'
                }
              },
              {
                element: function () { return document.querySelector('.mode-toggle'); },
                popover: {
                  title: 'Alt+E — edit mode',
                  description: 'Flip the card to edit. SemPKM generates the form from the model\'s SHACL shapes: required fields are marked, hints are inline, and validation runs when you save.',
                  side: 'bottom',
                  align: 'center'
                }
              }
            ];
          }
        },
        {
          id: 'connect',
          time: '11:30',
          title: 'Say how things connect',
          summary: 'Not just linked — typed. Every edge means something you can query later, and inference draws some of them for you.',
          enter: function (ctx) {
            ctx.open(BPKM + 'seed-note-architecture', 'Architecture Decision: Event Sourcing');
          },
          steps: function (ctx) {
            return [
              {
                element: '#relations-content',
                popover: {
                  title: 'Typed relations',
                  description: 'The decision <code>isAbout</code> Event Sourcing. Inbound, the <em>SemPKM Development</em> project <code>hasNote</code> it. Outbound and inbound edges are listed for the active object — click any target to jump to it.',
                  side: 'left',
                  align: 'start',
                  onNextClick: ctx.go(function () { ctx.bottomTab('inference'); })
                }
              },
              {
                element: '#panel-inference',
                popover: {
                  title: 'Edges Alice never draws',
                  description: 'Inference rules add edges from what is already true — a note about a concept that belongs to a project becomes related to that project\'s other notes. Inferred edges are marked so you always know which ones you wrote.',
                  side: 'top',
                  align: 'center'
                }
              }
            ];
          }
        },
        {
          id: 'views',
          time: '14:00',
          title: 'Same graph, your lens',
          summary: 'Afternoon planning: the same objects as a table for triage, a kanban for flow, a graph to see the shape of the project.',
          enter: function (ctx) {
            ctx.openView('table', BPKM + 'Task');
          },
          steps: function (ctx) {
            return [
              {
                element: ctx.editor,
                popover: {
                  title: 'Table — triage',
                  description: 'Every <strong>Task</strong> in the graph as rows. Sort by status or priority, pick the columns you care about; column preferences persist per view.',
                  side: 'left',
                  align: 'start',
                  onNextClick: ctx.go(function () { ctx.openView('kanban', BPKM + 'Task'); })
                }
              },
              {
                element: ctx.editor,
                popover: {
                  title: 'Kanban — flow',
                  description: 'Same tasks, now as columns. The columns come from the schema\'s allowed status values, so dragging a card is a real property change — not a copy drifting away from the source.',
                  side: 'left',
                  align: 'start',
                  onNextClick: ctx.go(function () { ctx.openView('graph', BPKM + 'Task'); })
                }
              },
              {
                element: ctx.editor,
                popover: {
                  title: 'Graph — shape',
                  description: 'And the shape of the project: nodes are objects, edges are the typed relations from this morning. One graph, many lenses — nothing exported, nothing duplicated.',
                  side: 'left',
                  align: 'start'
                }
              }
            ];
          }
        },
        {
          id: 'validate',
          time: '16:45',
          title: 'Catch drift before it becomes debt',
          summary: 'Lint notices what got skipped. Assistive, not blocking — nothing stopped Alice from saving, but nothing lets it rot silently either.',
          enter: function (ctx) {
            ctx.open(BPKM + 'seed-note-architecture', 'Architecture Decision: Event Sourcing');
            ctx.bottomTab('lint-dashboard');
          },
          steps: function (ctx) {
            return [
              {
                element: '#panel-lint-dashboard',
                popover: {
                  title: 'The lint dashboard',
                  description: 'SHACL validation runs on every save and in the background. Overdue tasks, missing review dates, stale contacts — every warning names the object and the rule that produced it.',
                  side: 'top',
                  align: 'center'
                }
              },
              {
                element: '#lint-content',
                popover: {
                  title: 'Fix it in place',
                  description: 'The same results also sit next to the active object. Open it, fill the missing field, save — and watch it go green. Press <strong>Alt+Shift+V</strong> to run validation on demand.',
                  side: 'left',
                  align: 'start'
                }
              }
            ];
          }
        },
        {
          id: 'trust',
          time: '18:00',
          title: 'Close the laptop with a clear conscience',
          summary: 'Everything that happened today is an immutable event — attributed, diffable, undoable.',
          enter: function (ctx) {
            ctx.bottomTab('event-log');
          },
          steps: function (ctx) {
            return [
              {
                element: '#panel-event-log',
                popover: {
                  title: 'The event log',
                  description: 'Every create, update, edge and delete is an event with a user and a timestamp. Expand one for a property-level diff; <strong>Undo</strong> writes a compensating event rather than rewriting history.',
                  side: 'top',
                  align: 'center'
                }
              },
              {
                popover: {
                  title: 'That was Alice\'s day',
                  description: 'Tomorrow\'s Alice can trust what today\'s Alice wrote — and see exactly how it got that way. Try Maya\'s day next, or explore the User Guide from the Docs &amp; Tutorials page.'
                }
              }
            ];
          }
        }
      ]
    },
    {
      id: 'maya',
      name: 'Maya',
      role: 'Researcher',
      icon: 'flask-conical',
      model: 'research',
      modelName: 'Research',
      tagline: 'Papers become objects, highlights become claims, and the literature\'s disagreements become structure you can query.',
      chapters: [
        {
          id: 'source',
          time: '9:30',
          title: 'A paper becomes an object',
          summary: 'The morning reading pile. Each paper goes in as a Paper with authors, year and DOI as real fields — not a PDF with a hopeful filename.',
          enter: function (ctx) {
            ctx.open(RES + 'seed-paper-kg-survey', 'Knowledge Graphs: A Survey');
          },
          steps: function (ctx) {
            return [
              {
                element: ctx.editor,
                popover: {
                  title: 'A Paper with real fields',
                  description: 'Title, authors, year, venue — typed properties from the <strong>Research</strong> model, consistent across every entry. The Markdown body holds Maya\'s reading notes.',
                  side: 'left',
                  align: 'start'
                }
              },
              {
                element: function () { return document.querySelector('.mode-toggle'); },
                popover: {
                  title: 'Alt+E — the schema keeps it honest',
                  description: 'Edit mode shows the generated form. Because the fields come from the model, every paper in the lab\'s graph looks the same — and can be queried the same way.',
                  side: 'bottom',
                  align: 'center'
                }
              }
            ];
          }
        },
        {
          id: 'claims',
          time: '10:15',
          title: 'Claims, not highlights',
          summary: 'Instead of highlighting passages, Maya extracts claims — each one an object that cites its source and takes a stance.',
          enter: function (ctx) {
            ctx.open(RES + 'seed-claim-pkm-failure', 'Claim: PKM systems are abandoned within 6 months');
          },
          steps: function (ctx) {
            return [
              {
                element: ctx.editor,
                popover: {
                  title: 'A Claim is an object',
                  description: '<em>"Most PKM systems are abandoned within 6 months of initial setup."</em> A claim has a statement, a confidence, and a paper it was <code>extractedFrom</code>.',
                  side: 'left',
                  align: 'start'
                }
              },
              {
                element: '#relations-content',
                popover: {
                  title: 'Evidence takes a stance',
                  description: 'Evidence objects <code>supports</code> or <code>refutes</code> this claim — here a survey supports it and a longitudinal study refutes it. The disagreement in the literature is now structure, not vibes.',
                  side: 'left',
                  align: 'start'
                }
              }
            ];
          }
        },
        {
          id: 'debate',
          time: '13:00',
          title: 'See the debate',
          summary: 'Switch to graph view and the claims sit with evidence pulling for and against them. A glance shows where the evidence piles up.',
          enter: function (ctx) {
            ctx.openView('graph', RES + 'Claim');
          },
          steps: function (ctx) {
            return [
              {
                element: ctx.editor,
                popover: {
                  title: 'The literature as a graph',
                  description: 'Claims and the papers and evidence around them. Which position stands alone? Which thread is still open? Click a node to open it; drag to rearrange.',
                  side: 'left',
                  align: 'start'
                }
              }
            ];
          }
        },
        {
          id: 'query',
          time: '15:30',
          title: 'Ask a precise question',
          summary: 'Time to write the related-work section. One SPARQL query pulls every piece of evidence that refutes a claim, citation attached.',
          enter: function (ctx) {
            ctx.bottomTab('sparql');
          },
          steps: function (ctx) {
            return [
              {
                element: function () { return document.getElementById('panel-sparql'); },
                popover: {
                  title: 'SPARQL console',
                  description: 'Paste this into the console and run it:<pre class="wt-code">PREFIX res: &lt;urn:sempkm:model:research:&gt;\nSELECT ?evidence ?claim WHERE {\n  ?evidence res:refutes ?claim .\n}</pre>Try that with full-text search over a folder of PDFs. (The SPARQL tab is available to members and owners.)',
                  side: 'top',
                  align: 'center'
                }
              }
            ];
          }
        },
        {
          id: 'share',
          time: '17:00',
          title: 'Share it with the lab',
          summary: 'The claims graph syncs to the lab\'s shared graph — federated, signed, and everyone keeps their own copy.',
          steps: function (ctx) {
            return [
              {
                element: function () { return document.getElementById('section-shared'); },
                popover: {
                  title: 'Shared graphs',
                  description: 'A shared graph is a slice of the knowledge base that syncs between SemPKM instances as signed RDF patches. Priya picks up where Maya left off — without a <em>final_v3_REAL.docx</em> in sight.',
                  side: 'right',
                  align: 'start'
                }
              },
              {
                element: function () { return document.getElementById('collab-content'); },
                popover: {
                  title: 'Who is here right now',
                  description: 'The collaboration panel shows who else has the active object open. Comments on the object stay attached to it — and land in the event log like everything else.',
                  side: 'left',
                  align: 'start'
                }
              },
              {
                popover: {
                  title: 'That was Maya\'s day',
                  description: 'Every claim added today makes tomorrow\'s query richer. Read more in the User Guide chapters on the SPARQL console and Federation &amp; Shared Graphs.'
                }
              }
            ];
          }
        }
      ]
    }
  ];

  window.SemPKM.walkthroughPersonas = PERSONAS;

  // --- Runner -------------------------------------------------------------------

  function chapterCardStep(persona, chapter, ctx, index, total) {
    return {
      popover: {
        title: chapter.time + ' · ' + chapter.title,
        description:
          '<span class="wt-card-tag">' + escapeHtml(persona.name) + ' · ' + escapeHtml(persona.role) +
          (total > 1 ? ' · chapter ' + (index + 1) + ' of ' + total : '') + '</span>' +
          escapeHtml(chapter.summary),
        onNextClick: ctx.go(function () {
          if (typeof chapter.enter === 'function') chapter.enter(ctx);
        })
      }
    };
  }

  function buildSteps(persona, chapters) {
    var steps = [];
    var ctxs = [];
    chapters.forEach(function (chapter, index) {
      var ctx = makeCtx(persona.id, chapter.id);
      ctxs.push(ctx);
      steps.push(chapterCardStep(persona, chapter, ctx, index, chapters.length));
      var body = chapter.steps(ctx) || [];
      body.forEach(function (step, i) {
        if (i === body.length - 1) {
          var original = step.onHighlightStarted;
          step.onHighlightStarted = function () {
            markChapterDone(persona.id, chapter.id);
            if (typeof original === 'function') original.apply(this, arguments);
          };
        }
        steps.push(step);
      });
    });
    return { steps: steps, ctxs: ctxs };
  }

  function showPrerequisiteCard(persona) {
    var driver = getDriver();
    if (!driver) return;
    driver({
      steps: [{
        popover: {
          title: 'Install the ' + persona.modelName + ' Mental Model first',
          description: escapeHtml(persona.name) + '\'s day uses the sample objects that ship with the <strong>' +
            escapeHtml(persona.modelName) + '</strong> Mental Model. Install it under <strong>Admin → Mental Models</strong>, then come back to this page.',
          showButtons: ['done']
        }
      }]
    }).drive();
  }

  /**
   * Start a persona walkthrough.
   * @param {string} personaId   e.g. 'alice'
   * @param {string} [chapterId] play only this chapter; omit for the whole day
   */
  window.SemPKM.startWalkthrough = function (personaId, chapterId) {
    var persona = findPersona(personaId);
    if (!persona) {
      console.warn('[SemPKM] Unknown walkthrough persona: ' + personaId);
      return;
    }
    // Outside the workspace (e.g. the standalone /guide page) hand off to the
    // workspace, which auto-starts tours from ?tour=.
    if (!isWorkspacePage()) {
      window.location.href = '/browser/?tour=' + encodeURIComponent(personaId + (chapterId ? ':' + chapterId : ''));
      return;
    }
    var driver = getDriver();
    if (!driver) {
      console.warn('[SemPKM] Driver.js not loaded — cannot start walkthrough');
      return;
    }
    var chapters = persona.chapters;
    if (chapterId) {
      var chapter = findChapter(persona, chapterId);
      if (!chapter) {
        console.warn('[SemPKM] Unknown walkthrough chapter: ' + personaId + ':' + chapterId);
        return;
      }
      chapters = [chapter];
    }

    isModelInstalled(persona.model).then(function (installed) {
      if (!installed) {
        showPrerequisiteCard(persona);
        return;
      }
      try { localStorage.setItem(ACTIVE_PERSONA_KEY, personaId); } catch (e) { /* ignore */ }
      SemPKM.debug('SemPKM', 'Walkthrough started', personaId, chapterId || '(whole day)');

      var built = buildSteps(persona, chapters);
      var driverObj = driver({
        showProgress: true,
        steps: built.steps,
        onDestroyStarted: function () {
          document.dispatchEvent(new CustomEvent('sempkm:walkthrough-ended', {
            detail: { personaId: personaId, chapterId: chapterId || null }
          }));
          driverObj.destroy();
        }
      });
      built.ctxs.forEach(function (ctx) { ctx.driver = driverObj; });
      driverObj.drive();
    });
  };

  /**
   * Generic dispatcher used by ?tour=<id> and the command palette.
   * Ids: 'welcome', 'create-object', 'demo', '<persona>' or '<persona>:<chapter>'.
   */
  window.SemPKM.startTourById = function (id) {
    if (!id) return false;
    if (id === 'welcome') { window.SemPKM.startWelcomeTour(); return true; }
    if (id === 'create-object') { window.SemPKM.startCreateObjectTour(); return true; }
    if (id === 'demo') { window.SemPKM.startDemoTour(); return true; }
    var parts = id.split(':');
    if (findPersona(parts[0])) {
      window.SemPKM.startWalkthrough(parts[0], parts[1] || undefined);
      return true;
    }
    console.warn('[SemPKM] Unknown tour id: ' + id);
    return false;
  };

  // --- Picker UI (Docs & Tutorials page) --------------------------------------

  function activePersonaId() {
    var stored = null;
    try { stored = localStorage.getItem(ACTIVE_PERSONA_KEY); } catch (e) { /* ignore */ }
    return findPersona(stored) ? stored : PERSONAS[0].id;
  }

  function renderPickerHtml(selectedId) {
    var progress = readProgress();
    var html = '<div class="wt-tabs" role="tablist" aria-label="Choose a persona">';
    PERSONAS.forEach(function (p) {
      var done = Object.keys(progress[p.id] || {}).filter(function (c) { return findChapter(p, c); }).length;
      var on = p.id === selectedId;
      html += '<button type="button" class="wt-tab' + (on ? ' wt-tab-active' : '') + '" role="tab" aria-selected="' + on + '" data-wt-persona="' + escapeHtml(p.id) + '">' +
        '<i data-lucide="' + escapeHtml(p.icon || 'user') + '"></i>' +
        '<span class="wt-tab-text"><strong>' + escapeHtml(p.name) + '</strong><span>' + escapeHtml(p.role) + '</span></span>' +
        (done ? '<span class="wt-tab-count">' + done + '/' + p.chapters.length + '</span>' : '') +
        '</button>';
    });
    html += '</div>';

    PERSONAS.forEach(function (p) {
      var personaProgress = progress[p.id] || {};
      var doneCount = p.chapters.filter(function (c) { return personaProgress[c.id]; }).length;
      html += '<div class="wt-persona" role="tabpanel" data-wt-persona-panel="' + escapeHtml(p.id) + '"' + (p.id === selectedId ? '' : ' hidden') + '>';
      html += '<div class="wt-persona-head"><div class="wt-persona-copy">' +
        '<p class="wt-tagline">' + escapeHtml(p.tagline) + '</p>' +
        '<p class="wt-meta">Uses the <strong>' + escapeHtml(p.modelName) + '</strong> Mental Model · ' +
        (doneCount === p.chapters.length ? 'All chapters done' : doneCount + ' of ' + p.chapters.length + ' chapters done') + '</p>' +
        '</div><div class="wt-persona-actions">' +
        '<button type="button" class="btn docs-card-btn wt-play-all" data-wt-start="' + escapeHtml(p.id) + '">' +
        '<i data-lucide="play"></i> Play the whole day</button>' +
        (doneCount ? '<button type="button" class="wt-reset" data-wt-reset="' + escapeHtml(p.id) + '" title="Reset progress">Reset</button>' : '') +
        '</div></div>';
      html += '<ol class="wt-chapters">';
      p.chapters.forEach(function (c) {
        var done = Boolean(personaProgress[c.id]);
        html += '<li class="wt-chapter' + (done ? ' wt-chapter-done' : '') + '">' +
          '<span class="wt-time">' + escapeHtml(c.time) + '</span>' +
          '<div class="wt-chapter-body"><h4 class="wt-chapter-title">' +
          (done ? '<i data-lucide="check-circle-2" class="wt-check"></i>' : '') +
          escapeHtml(c.title) + '</h4><p class="wt-chapter-summary">' + escapeHtml(c.summary) + '</p></div>' +
          '<button type="button" class="btn docs-card-btn wt-chapter-btn" data-wt-start="' + escapeHtml(p.id) + '" data-wt-chapter="' + escapeHtml(c.id) + '">' +
          (done ? 'Replay' : 'Start') + '</button>' +
          '</li>';
      });
      html += '</ol></div>';
    });
    return html;
  }

  /**
   * Render the persona/chapter picker into a container element.
   * Safe to call repeatedly (re-renders in place). Listens for progress
   * changes so completed chapters get ticked while the page is open.
   */
  window.SemPKM.renderWalkthroughPicker = function (container) {
    if (!container) return;
    var selected = container.getAttribute('data-wt-selected') || activePersonaId();

    function draw() {
      container.innerHTML = renderPickerHtml(selected);
      container.setAttribute('data-wt-selected', selected);
      if (typeof lucide !== 'undefined' && lucide.createIcons) {
        lucide.createIcons({ attrs: { class: ['lucide'] } });
      }
    }

    if (!container._wtBound) {
      container._wtBound = true;
      container.addEventListener('click', function (e) {
        var tab = e.target.closest('[data-wt-persona]');
        if (tab) {
          selected = tab.getAttribute('data-wt-persona');
          try { localStorage.setItem(ACTIVE_PERSONA_KEY, selected); } catch (err) { /* ignore */ }
          draw();
          return;
        }
        var start = e.target.closest('[data-wt-start]');
        if (start) {
          window.SemPKM.startWalkthrough(start.getAttribute('data-wt-start'), start.getAttribute('data-wt-chapter') || undefined);
          return;
        }
        var reset = e.target.closest('[data-wt-reset]');
        if (reset) {
          window.SemPKM.resetWalkthroughProgress(reset.getAttribute('data-wt-reset'));
        }
      });
      document.addEventListener('sempkm:walkthrough-progress', function () {
        if (document.body.contains(container)) draw();
      });
    }
    draw();
  };

  // Auto-render any picker containers present at load (standalone /guide page).
  // Workspace tab fragments call renderWalkthroughPicker from their inline script.
  function renderPresentPickers() {
    document.querySelectorAll('[data-walkthrough-picker]').forEach(function (el) {
      window.SemPKM.renderWalkthroughPicker(el);
    });
  }
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', renderPresentPickers);
  } else {
    renderPresentPickers();
  }

})();
