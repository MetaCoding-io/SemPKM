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

  // Resolve fullcalendar URL: prefer data attribute from template, fall back to asset path
  var _fcConfig = document.getElementById('fullcalendar-loader-config');
  var CDN = _fcConfig ? _fcConfig.getAttribute('data-fullcalendar-src') : '/js/fullcalendar.js';

  // Named handlers for document-level events — stored here so we can
  // removeEventListener with the same reference on cleanup / reinit.
  var _commandHandler = null;
  var _scopeHandler = null;

  /**
   * Persist a calendar drag/resize via the PATCH endpoint.
   * Calls info.revert() on failure for optimistic rollback.
   */
  function patchCalendarEvent(info, actionLabel) {
    var iri = info.event.extendedProps && info.event.extendedProps.iri;
    if (!iri) return;

    var payload = { iri: iri, start: info.event.startStr };
    if (info.event.end) payload.end = info.event.endStr;

    SemPKM.debug('calendar', actionLabel + ':', iri,
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
      SemPKM.debug('calendar', actionLabel + ' persisted, event_iri:', result.event_iri);
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
    var payload = window.SemPKM.__calendarDragPayload;
    window.SemPKM.__calendarDragPayload = null;

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

    SemPKM.debug('calendar', 'external drop:', iri, 'start=' + scheduledStart, 'end=' + scheduledEnd);

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
    // Destroy any previous instance (handles reinit without panel close)
    if (window.SemPKM._sempkmCalendar) {
      try { window.SemPKM._sempkmCalendar.destroy(); } catch (e) { /* already destroyed */ }
      window.SemPKM._sempkmCalendar = null;
    }
    // Remove stale document-level listeners from a previous init
    if (_commandHandler) {
      document.removeEventListener('sempkm:command-executed', _commandHandler);
      _commandHandler = null;
    }
    if (_scopeHandler) {
      document.removeEventListener('sempkm:scope-changed', _scopeHandler);
      _scopeHandler = null;
    }

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
            SemPKM.debug('calendar', 'select range:',
              info.startStr, '→', info.endStr);
            /* Stash selected dates for future form pre-fill */
            window.SemPKM._calendarSelectedDates = {
              scheduledStart: info.startStr,
              scheduledEnd: info.endStr
            };
            if (typeof window.SemPKM.showCreateFormForType === 'function') {
              window.SemPKM.showCreateFormForType(
                'urn:sempkm:model:basic-pkm:Task', 'Task'
              );
            }
          }
        });

        cal.render();
        window.SemPKM._sempkmCalendar = cal;

        SemPKM.debug('calendar', 'rendered with',
          (data.events || []).length, 'events, editable=true, droppable=true');

        /* ── External drop visual feedback ── */
        el.addEventListener('dragover', function (e) {
          if (window.SemPKM.__calendarDragPayload || (e.dataTransfer && e.dataTransfer.types.indexOf('text/iri') !== -1)) {
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
        _commandHandler = function () {
          if (window.SemPKM._sempkmCalendar) {
            window.SemPKM._sempkmCalendar.refetchEvents();
          }
        };
        document.addEventListener('sempkm:command-executed', _commandHandler);

        /* ── Scope sync: re-fetch when a sibling view changes scope ── */
        _scopeHandler = function (e) {
          var detail = e.detail || {};
          // Compute own panel ID to avoid self-triggered re-fetch
          var ownPanel = el.closest('.dv-panel');
          var ownPanelId = ownPanel ? (ownPanel.id || '') : '';
          if (detail.sourcePanel && detail.sourcePanel === ownPanelId) return;

          SemPKM.debug('calendar', 'scope sync: scopeQuery=' + (detail.scopeQuery || '(none)') +
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
              SemPKM.debug('calendar', 'scope sync complete:', (data.events || []).length, 'events');
            })
            .catch(function (err) {
              console.error('[calendar] scope sync failed:', err);
            });
        };
        document.addEventListener('sempkm:scope-changed', _scopeHandler);

        /* ── Register cleanup for panel disposal ── */
        if (typeof window.SemPKM.registerCleanup === 'function') {
          window.SemPKM.registerCleanup(containerId, function () {
            if (window.SemPKM._sempkmCalendar) {
              try { window.SemPKM._sempkmCalendar.destroy(); } catch (e) { /* ignore */ }
              window.SemPKM._sempkmCalendar = null;
            }
            if (_commandHandler) {
              document.removeEventListener('sempkm:command-executed', _commandHandler);
              _commandHandler = null;
            }
            if (_scopeHandler) {
              document.removeEventListener('sempkm:scope-changed', _scopeHandler);
              _scopeHandler = null;
            }
          });
        }
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
  window.SemPKM.initCalendar = function (containerId, dataUrl) {
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
