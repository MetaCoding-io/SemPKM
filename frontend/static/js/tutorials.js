/**
 * tutorials.js — Driver.js guided tour definitions for SemPKM.
 *
 * Exposes:
 *   window.startWelcomeTour()       — "Welcome to SemPKM" workspace orientation
 *   window.startCreateObjectTour()  — "Creating Your First Object" htmx-gated tour
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

  window.startWelcomeTour = function () {
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
            description: 'The object you opened appears as a tab here. You can split the editor into multiple groups with Ctrl+\\.',
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
            description: 'Objects open in read mode by default. Click this button (or press Ctrl+E) to switch to edit mode where you can change properties and edit the body.',
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
            description: 'Press Ctrl+K (or Cmd+K on Mac) to open the command palette. Search for any action, object, or view.',
            side: 'bottom',
            align: 'center'
          }
        },
        {
          // Centered — no element — explains Ctrl+S saving
          popover: {
            title: 'Saving Your Work',
            description: 'When you have made edits, press <strong>Ctrl+S</strong> to save. The tab\'s dirty indicator (a colored dot) clears after a successful save, and SHACL validation runs automatically.'
          }
        },
        {
          // No element = centered popover (tour end)
          popover: {
            title: "You're all set!",
            description: 'Explore the other tutorials on this page, or start creating objects with Ctrl+N.',
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

  window.startCreateObjectTour = function () {
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
              var editorArea = typeof window.getActiveEditorArea === 'function'
                ? window.getActiveEditorArea()
                : document.getElementById('editor-area-group-1');

              // Trigger the type picker load via the global showTypePicker function
              if (typeof window.showTypePicker === 'function') {
                window.showTypePicker();
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

})();
