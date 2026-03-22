---
estimated_steps: 7
estimated_files: 7
skills_used: []
---

# T02: Frontend — vendor FullCalendar, template, JS, CSS, explorer entry

**Slice:** S02 — Calendar View Renderer
**Milestone:** M033

## Description

All frontend work for the calendar view: vendor FullCalendar 6.x via the npm/build.js pipeline, create the Jinja2 template, write the JS init function, add CSS with dark mode support, add the explorer sidebar entry, and register the label in workspace.js. Follows established patterns from graph_view.html (tryInit polling), kanban_view.html (view-flex-column wrapper), and the Yasgui/Chart.js lazy-load approach (D272).

## Steps

1. **Add FullCalendar dependency** (`frontend/package.json`): Add `"fullcalendar": "^6.1.20"` to the `dependencies` object. Run `cd frontend && npm install` to install.

2. **Add FullCalendar to build pipeline** (`frontend/build.js`): Add a new section after the Chart.js section (section 6). Read `fullcalendar/index.global.min.js` from `node_modules`, content-hash it, write to `dist/`, add `fullcalendar.js` to the manifest. **No CSS file needed** — FullCalendar v6 self-injects its styles from the JS bundle. Pattern:
   ```javascript
   console.log('6. Building FullCalendar bundle...');
   const fullcalJs = fs.readFileSync(
     path.join(NODE_MODULES, 'fullcalendar/index.global.min.js')
   );
   const fullcalJsFile = writeHashed('fullcalendar', '.min.js', fullcalJs);
   manifest['fullcalendar.js'] = fullcalJsFile;
   console.log(`   ${fullcalJsFile}`);
   ```
   Increment the step numbers for subsequent sections (highlight.js themes, app JS, app CSS, manifest, gz).

3. **Create calendar template** (`backend/app/templates/browser/calendar_view.html`): Structure:
   - `.view-flex-column` wrapper (same as kanban/graph)
   - `{% if is_generic %}{% include "browser/type_filter_pills.html" %}{% endif %}`
   - `{% include "browser/view_toolbar.html" %}`
   - Error state: if no date properties detected and a type is selected, show `.view-empty-state` with message
   - `<div id="calendar-container" class="calendar-container"></div>`
   - Inline `<script>` with `tryInit()` polling (same pattern as `graph_view.html`):
     - Wait for `window.initCalendar` to be defined
     - Build data URL: `/browser/views/generic/calendar/data?type=<selected_type>&scope_query=<scope_query>`
     - Call `initCalendar('calendar-container', dataUrl, { startField, endField })` where startField/endField come from template context (`{{ start_field }}`, `{{ end_field }}`)
   - Load FullCalendar JS via `<script src="{{ 'fullcalendar.js' | asset_url }}"></script>` in the template. Add CDN fallback: `<script>window.FullCalendar || document.write('<script src="https://cdn.jsdelivr.net/npm/fullcalendar@6.1.20/index.global.min.js"><\/script>')</script>`

4. **Create calendar.js** (`frontend/static/js/calendar.js`): IIFE containing:
   - `initCalendar(containerId, dataUrl, options)` function:
     - `var container = document.getElementById(containerId);`
     - `var calendar = new FullCalendar.Calendar(container, { ... })` with:
       - `initialView: 'dayGridMonth'`
       - `headerToolbar: { left: 'prev,next today', center: 'title', right: 'dayGridMonth,timeGridWeek,timeGridDay' }`
       - `events: function(info, successCallback, failureCallback) { fetch(dataUrl).then(...) }` — fetches from data endpoint, passes result to successCallback
       - `eventClick: function(info) { var iri = info.event.extendedProps.iri; var title = info.event.title; if (typeof openTab === 'function') openTab(iri, title); }` — opens object tab
       - `height: '100%'` — fills the flex container
       - `themeSystem: 'standard'`
     - `calendar.render()` — must happen when container is visible (the tryInit polling ensures this)
   - Expose `window.initCalendar = initCalendar`
   - Listen for type filter pill htmx swaps to refetch: after any htmx swap targeting `.group-editor-area`, the calendar gets re-initialized by the new template's inline script

5. **Add calendar CSS** (`frontend/static/css/views.css`): Append at the end:
   ```css
   /* ── Calendar View ───────────────────────────────────── */
   .calendar-container {
       flex: 1;
       min-height: 0;
       padding: 8px;
   }
   
   /* Dark mode overrides for FullCalendar's CSS custom properties */
   .dark .calendar-container {
       --fc-border-color: var(--color-border);
       --fc-page-bg-color: var(--color-bg);
       --fc-neutral-bg-color: var(--color-bg-elevated);
       --fc-today-bg-color: var(--color-bg-accent-subtle);
       --fc-event-bg-color: var(--color-accent);
       --fc-event-text-color: var(--color-text-on-accent);
       --fc-button-bg-color: var(--color-bg-elevated);
       --fc-button-border-color: var(--color-border);
       --fc-button-text-color: var(--color-text);
       --fc-button-hover-bg-color: var(--color-bg-hover);
       --fc-button-hover-border-color: var(--color-border);
       --fc-button-active-bg-color: var(--color-accent);
       --fc-button-active-border-color: var(--color-accent);
   }
   ```

6. **Add explorer sidebar entry** (`backend/app/templates/browser/views_explorer.html`): Add a Calendar View tree-leaf entry after the Kanban View entry, before the Saved Views folder:
   ```html
   <a class="tree-leaf view-leaf" href="#"
      draggable="true"
      ondragstart="event.dataTransfer.setData('text/plain', 'Calendar View'); event.dataTransfer.effectAllowed = 'copy'; window.__canvasDragPayload = {type:'view', id:'generic-calendar', label:'Calendar View', url:'/browser/views/generic/calendar?embed=1'};"
      onclick="openGenericViewTab('calendar'); return false;">
       <span class="tree-leaf-icon">&#128197;</span>
       <span class="tree-leaf-label">Calendar View</span>
   </a>
   ```

7. **Register label in workspace.js** (`frontend/static/js/workspace.js`): In the `openGenericViewTab()` function, add `calendar: 'Calendar View'` to the `labels` dict (around line 3236).

## Must-Haves

- [ ] `fullcalendar` package installed and in `package.json`
- [ ] `fullcalendar.js` entry appears in `dist/manifest.json` after `node build.js`
- [ ] `calendar_view.html` template renders with type filter pills, view toolbar, and FullCalendar container
- [ ] `calendar.js` initializes FullCalendar with month/week/day views, eventClick → openTab()
- [ ] Dark mode CSS overrides for `--fc-*` custom properties in `views.css`
- [ ] Calendar View entry in explorer sidebar with openGenericViewTab('calendar') onclick
- [ ] `labels` dict in workspace.js includes `calendar: 'Calendar View'`
- [ ] CDN fallback script tag for FullCalendar in template

## Verification

- `cd frontend && npm ci && node build.js` — succeeds without errors
- `grep '"fullcalendar.js"' frontend/dist/manifest.json` — returns a manifest entry
- Calendar view renders at `/browser/views/generic/calendar` with FullCalendar grid
- Click an event → object tab opens (verify in browser)
- Month/Week/Day toolbar buttons switch the calendar view
- Explorer sidebar shows "Calendar View" entry

## Inputs

- `frontend/package.json` — existing dependencies to extend
- `frontend/build.js` — existing build pipeline to add FullCalendar vendor section
- `backend/app/templates/browser/graph_view.html` — reference for tryInit() polling and template structure
- `backend/app/templates/browser/kanban_view.html` — reference for view-flex-column wrapper
- `backend/app/templates/browser/views_explorer.html` — existing explorer entries to add calendar to
- `frontend/static/js/workspace.js` — openGenericViewTab() labels dict to extend
- `frontend/static/css/views.css` — existing view styles to append calendar section

## Expected Output

- `frontend/package.json` — fullcalendar dependency added
- `frontend/build.js` — FullCalendar vendor section added
- `backend/app/templates/browser/calendar_view.html` — new template created
- `frontend/static/js/calendar.js` — new JS file created
- `frontend/static/css/views.css` — calendar CSS appended
- `backend/app/templates/browser/views_explorer.html` — calendar tree-leaf added
- `frontend/static/js/workspace.js` — calendar label added to openGenericViewTab()
