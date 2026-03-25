/**
 * kanban.js — Drag-drop module for the Kanban board view.
 *
 * Initialises HTML5 drag-and-drop on .kanban-card elements,
 * with stopPropagation() to prevent dockview panel drag interference.
 * On drop, issues an object.patch command to update the status property.
 */

(function () {
  'use strict';

  function initKanban(boardEl) {
    if (!boardEl) return;

    boardEl.querySelectorAll('.kanban-card').forEach(function (card) {
      card.addEventListener('dragstart', onDragStart, false);
      card.addEventListener('dragend', onDragEnd, false);
    });

    boardEl.querySelectorAll('.kanban-column-body').forEach(function (col) {
      col.addEventListener('dragover', onDragOver, false);
      col.addEventListener('dragleave', onDragLeave, false);
      col.addEventListener('drop', onDrop, false);
    });
  }

  /* ── Drag Handlers ── */

  function onDragStart(e) {
    var card = e.currentTarget;
    var iri = card.dataset.iri;
    var title = card.dataset.title || (card.querySelector('.kanban-card-title') ? card.querySelector('.kanban-card-title').textContent.trim() : iri);

    e.dataTransfer.setData('text/plain', iri);
    e.dataTransfer.setData('text/iri', iri);
    e.dataTransfer.setData('text/label', title);
    e.dataTransfer.effectAllowed = 'move';

    // Side-channel for calendar / canvas external drop handlers
    window.SemPKM.__calendarDragPayload = { iri: iri, title: title };
    window.SemPKM.__canvasDragPayload = { iri: iri, label: title };

    card.classList.add('dragging');
    // Prevent dockview from intercepting the drag
    e.stopPropagation();
  }

  function onDragEnd(e) {
    e.currentTarget.classList.remove('dragging');
  }

  function onDragOver(e) {
    e.preventDefault();
    e.stopPropagation();
    var column = e.currentTarget.closest('.kanban-column');
    if (column) column.classList.add('drag-over');
  }

  function onDragLeave(e) {
    var column = e.currentTarget.closest('.kanban-column');
    // Only remove if we actually left the column body
    if (column && !e.currentTarget.contains(e.relatedTarget)) {
      column.classList.remove('drag-over');
    }
  }

  function onDrop(e) {
    e.preventDefault();
    e.stopPropagation();

    var targetBody = e.currentTarget;
    var column = targetBody.closest('.kanban-column');
    if (column) column.classList.remove('drag-over');

    var iri = e.dataTransfer.getData('text/plain');
    if (!iri) return;

    var boardEl = targetBody.closest('.kanban-board');
    if (!boardEl) return;

    var newStatus = column ? column.dataset.status : '';
    var predicate = boardEl.dataset.statusPredicate;

    // Find the card being dragged
    var cardEl = boardEl.querySelector('.kanban-card[data-iri="' + CSS.escape(iri) + '"]');
    if (!cardEl) return;

    // Skip if dropped in the same column
    var sourceBody = cardEl.closest('.kanban-column-body');
    if (sourceBody === targetBody) return;

    patchStatus(iri, predicate, newStatus, cardEl, targetBody, sourceBody, boardEl);
  }

  /* ── Status Patch ── */

  function patchStatus(iri, predicate, newStatus, cardEl, targetBody, sourceBody, boardEl) {
    // Optimistic DOM move
    targetBody.appendChild(cardEl);
    _updateColumnCounts(boardEl);

    var payload = {
      command: 'object.patch',
      params: {
        iri: iri,
        properties: {}
      }
    };
    payload.params.properties[predicate] = newStatus;

    apiFetch('/api/commands', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      silent: true
    })
      .then(function (resp) {
        if (!resp.ok) {
          throw new Error('Patch failed with status ' + resp.status);
        }
        return resp.json();
      })
      .then(function () {
        document.dispatchEvent(new CustomEvent('sempkm:command-executed'));
      })
      .catch(function (err) {
        console.error('kanban: failed to patch status for', iri, err);
        // Revert: move card back to source column
        if (sourceBody) {
          sourceBody.appendChild(cardEl);
          _updateColumnCounts(boardEl);
        }
        // Show toast if available
        if (typeof showToast === 'function') {
          showToast('Failed to update status: ' + err.message);
        }
      });
  }

  /* ── Helpers ── */

  function _updateColumnCounts(boardEl) {
    if (!boardEl) return;
    boardEl.querySelectorAll('.kanban-column').forEach(function (col) {
      var body = col.querySelector('.kanban-column-body');
      var countEl = col.querySelector('.kanban-column-count');
      if (body && countEl) {
        countEl.textContent = body.querySelectorAll('.kanban-card').length;
      }
    });
  }

  /* ── Export ── */
  window.SemPKM.initKanban = initKanban;

  /* ── Scope sync: re-fetch when a sibling view changes scope ── */
  document.addEventListener('sempkm:scope-changed', function (e) {
    var detail = e.detail || {};
    var boardEl = document.querySelector('.kanban-board');
    if (!boardEl) return;

    // Compute own panel ID to avoid self-triggered re-fetch
    var ownPanel = boardEl.closest('.dv-panel');
    var ownPanelId = ownPanel ? (ownPanel.id || '') : '';
    if (detail.sourcePanel && detail.sourcePanel === ownPanelId) return;

    console.log('[kanban] scope sync: scopeQuery=' + (detail.scopeQuery || '(none)') +
      ' from panel=' + (detail.sourcePanel || '(unknown)'));

    // Determine the type IRI from the board's context or the event detail
    var typeIri = boardEl.dataset.typeIri || detail.selectedType || '';

    // Build the kanban URL with the updated scope_query
    var url = '/browser/views/generic/kanban';
    var params = [];
    if (detail.scopeQuery) params.push('scope_query=' + encodeURIComponent(detail.scopeQuery));
    if (typeIri) params.push('type=' + encodeURIComponent(typeIri));
    if (params.length) url += '?' + params.join('&');

    // Visual feedback
    boardEl.classList.add('scope-syncing');
    setTimeout(function () { boardEl.classList.remove('scope-syncing'); }, 300);

    var target = boardEl.closest('.group-editor-area') || boardEl.parentElement;
    if (target && typeof htmx !== 'undefined') {
      htmx.ajax('GET', url, { target: target, swap: 'innerHTML' });
    }
  });

})();
