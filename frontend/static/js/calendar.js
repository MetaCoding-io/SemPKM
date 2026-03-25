/**
 * calendar.js — Calendar view module.
 *
 * Extracted from the inline script in calendar_view.html.
 * Exports:
 *   window.initCalendar(containerId, dataUrl)  — boots the FullCalendar instance
 *   window._sempkmCalendar                     — reference for dev inspection
 */

(function () {
  'use strict';

  var CDN = 'https://cdn.jsdelivr.net/npm/fullcalendar@6.1.17/index.global.min.js';

  /**
   * Persist a calendar drag/resize via the PATCH endpoint.
   * Calls info.revert() on failure for optimistic rollback.
   */
  function patchCalendarEvent(info, actionLabel) {
    var iri = info.event.extendedProps && info.event.extendedProps.iri;
    if (!iri) return;

    var payload = { iri: iri, start: info.event.startStr };
    if (info.event.end) payload.end = info.event.endStr;

    console.log('[calendar] ' + actionLabel + ':', iri,
      'start=' + info.event.startStr,
      info.event.end ? 'end=' + info.event.endStr : '(no end)');

    apiFetch('/browser/views/calendar/patch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify(payload),
      silent: true
    }).then(function (r) {
      return r.json();
    }).then(function (result) {
      console.log('[calendar] ' + actionLabel + ' persisted, event_iri:', result.event_iri);
      if (typeof showToast === 'function') showToast(actionLabel === 'resize' ? 'Duration updated' : 'Task rescheduled');
      document.dispatchEvent(new CustomEvent('sempkm:command-executed'));
    }).catch(function (err) {
      console.error('[calendar] ' + actionLabel + ' patch failed:', err);
      info.revert();
      if (typeof showToast === 'function') showToast('Failed to save — reverted');
    });
  }

  /**
   * Handle an external drop onto the calendar (from kanban card or explorer tree).
   * Reads from the __calendarDragPayload side-channel first, then falls back to
   * the dragged element's data-iri attribute.
   */
  function handleExternalDrop(info, calendar) {
    var payload = window.__calendarDragPayload;
    window.__calendarDragPayload = null;

    var iri, title;
    if (payload && payload.iri) {
      iri = payload.iri;
      title = payload.title || iri;
    } else if (info.draggedEl && info.draggedEl.dataset && info.draggedEl.dataset.iri) {
      iri = info.draggedEl.dataset.iri;
      title = (info.draggedEl.dataset.title) || iri;
    } else {
      console.warn('[calendar] external drop: no IRI found in payload or element');
      return;
    }

    var scheduledStart = info.dateStr || info.date.toISOString();
    var scheduledEnd = new Date(info.date.getTime() + 3600000).toISOString();

    console.log('[calendar] external drop:', iri, 'start=' + scheduledStart, 'end=' + scheduledEnd);

    apiFetch('/browser/views/calendar/patch', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ iri: iri, start: scheduledStart, end: scheduledEnd }),
      silent: true
    }).then(function (r) {
      return r.json();
    }).then(function () {
      calendar.addEvent({
        id: iri,
        title: title,
        start: scheduledStart,
        end: scheduledEnd,
        extendedProps: { iri: iri, sourceType: 'Task' },
        classNames: ['fc-event-task']
      });
      if (typeof showToast === 'function') showToast('Task scheduled');
      document.dispatchEvent(new CustomEvent('sempkm:command-executed'));
    }).catch(function (err) {
      console.error('[calendar] external drop failed:', err);
      if (typeof showToast === 'function') showToast('Failed to schedule — ' + err.message);
    });
  }

  /**
   * Boot the FullCalendar instance inside the given container.
   *
   * @param {string} containerId   DOM id of the calendar container element
   * @param {string} dataUrl       URL to fetch calendar event JSON from
   */
  function _initCalendar(containerId, dataUrl) {
    apiFetch(dataUrl, { credentials: 'include', silent: true })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        var el = document.getElementById(containerId);
        if (!el) return;

        var cal = new FullCalendar.Calendar(el, {
          initialView: 'dayGridMonth',
          headerToolbar: {
            left: 'prev,next today',
            center: 'title',
            right: 'dayGridMonth,timeGridWeek,timeGridDay'
          },
          events: data.events || [],
          height: '100%',

          /* ── Editable / selectable ── */
          editable: true,
          selectable: true,
          eventStartEditable: true,
          eventDurationEditable: true,

          /* ── External drop support ── */
          droppable: true,
          drop: function (info) {
            handleExternalDrop(info, cal);
          },

          /* ── Color-code by sourceType + recurring indicator ── */
          eventClassNames: function (arg) {
            var ep = arg.event.extendedProps || {};
            var classes = [];
            if (ep.sourceType === 'Task' || ep.sourceType === 'task') classes.push('fc-event-task');
            if (ep.sourceType === 'Event' || ep.sourceType === 'event') classes.push('fc-event-event');
            if (ep.isVirtual) classes.push('fc-event-recurring');
            return classes;
          },

          /* ── Click to open object tab (virtual events → master) ── */
          eventClick: function (info) {
            var ep = info.event.extendedProps || {};
            var iri = ep.masterIri || ep.iri;  // virtual events point to master
            var title = info.event.title || '';
            if (iri && typeof openTab === 'function') {
              openTab(iri, title);
            }
          },

          /* ── Drag to reschedule ── */
          eventDrop: function (info) {
            patchCalendarEvent(info, 'drop');
          },

          /* ── Resize to change duration ── */
          eventResize: function (info) {
            patchCalendarEvent(info, 'resize');
          },

          /* ── Click empty slot to create Task ── */
          select: function (info) {
            console.log('[calendar] select range:',
              info.startStr, '→', info.endStr);
            /* Stash selected dates for future form pre-fill */
            window._calendarSelectedDates = {
              scheduledStart: info.startStr,
              scheduledEnd: info.endStr
            };
            if (typeof window.showCreateFormForType === 'function') {
              window.showCreateFormForType(
                'urn:sempkm:model:basic-pkm:Task', 'Task'
              );
            }
          }
        });

        cal.render();
        window._sempkmCalendar = cal;

        console.log('[calendar] rendered with',
          (data.events || []).length, 'events, editable=true, droppable=true');

        /* ── External drop visual feedback ── */
        el.addEventListener('dragover', function (e) {
          if (window.__calendarDragPayload || (e.dataTransfer && e.dataTransfer.types.indexOf('text/iri') !== -1)) {
            e.preventDefault();
            el.classList.add('calendar-drop-active');
          }
        });
        el.addEventListener('dragleave', function (e) {
          if (!el.contains(e.relatedTarget)) {
            el.classList.remove('calendar-drop-active');
          }
        });
        el.addEventListener('drop', function () {
          el.classList.remove('calendar-drop-active');
        });

        /* ── Auto-refresh on external mutations ── */
        document.addEventListener('sempkm:command-executed', function () {
          if (window._sempkmCalendar) {
            window._sempkmCalendar.refetchEvents();
          }
        });

        /* ── Scope sync: re-fetch when a sibling view changes scope ── */
        document.addEventListener('sempkm:scope-changed', function (e) {
          var detail = e.detail || {};
          // Compute own panel ID to avoid self-triggered re-fetch
          var ownPanel = el.closest('.dv-panel');
          var ownPanelId = ownPanel ? (ownPanel.id || '') : '';
          if (detail.sourcePanel && detail.sourcePanel === ownPanelId) return;

          console.log('[calendar] scope sync: scopeQuery=' + (detail.scopeQuery || '(none)') +
            ' from panel=' + (detail.sourcePanel || '(unknown)'));

          // Build the new data URL with the updated scope_query
          var baseUrl = dataUrl.replace(/[&?]scope_query=[^&]*/g, '');
          var sep = baseUrl.indexOf('?') === -1 ? '?' : '&';
          var newUrl = detail.scopeQuery
            ? baseUrl + sep + 'scope_query=' + encodeURIComponent(detail.scopeQuery)
            : baseUrl;

          // Visual feedback
          el.classList.add('scope-syncing');
          setTimeout(function () { el.classList.remove('scope-syncing'); }, 300);

          apiFetch(newUrl, { credentials: 'include', silent: true })
            .then(function (r) { return r.json(); })
            .then(function (data) {
              cal.removeAllEvents();
              (data.events || []).forEach(function (evt) {
                cal.addEvent(evt);
              });
              console.log('[calendar] scope sync complete:', (data.events || []).length, 'events');
            })
            .catch(function (err) {
              console.error('[calendar] scope sync failed:', err);
            });
        });
      })
      .catch(function (err) {
        console.error('[calendar] data fetch failed:', err);
        var el = document.getElementById(containerId);
        if (el) {
          el.innerHTML = '<div class="view-empty-state"><p>Failed to load calendar data.</p></div>';
        }
      });
  }

  /**
   * Public entry point — lazy-loads FullCalendar CDN if needed, then initializes.
   */
  window.initCalendar = function (containerId, dataUrl) {
    if (typeof FullCalendar !== 'undefined') {
      _initCalendar(containerId, dataUrl);
    } else {
      var script = document.createElement('script');
      script.src = CDN;
      script.onload = function () { _initCalendar(containerId, dataUrl); };
      script.onerror = function () {
        console.error('[calendar] failed to load FullCalendar CDN');
        var el = document.getElementById(containerId);
        if (el) {
          el.innerHTML = '<div class="view-empty-state"><p>Failed to load calendar library.</p></div>';
        }
      };
      document.head.appendChild(script);
    }
  };
})();
