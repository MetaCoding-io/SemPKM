/**
 * quadrant.js — Drag-to-reclassify module for the Quadrant board view.
 *
 * Initialises HTML5 drag-and-drop on .quadrant-card elements,
 * with stopPropagation() to prevent dockview panel drag interference.
 * On drop, issues an object.patch command updating both axis properties.
 */

(function () {
  'use strict';

  function initQuadrant(boardEl) {
    if (!boardEl) return;

    boardEl.querySelectorAll('.quadrant-card').forEach(function (card) {
      card.addEventListener('dragstart', onDragStart, false);
      card.addEventListener('dragend', onDragEnd, false);
    });

    boardEl.querySelectorAll('.quadrant-cell-body').forEach(function (body) {
      body.addEventListener('dragover', onDragOver, false);
      body.addEventListener('dragleave', onDragLeave, false);
      body.addEventListener('drop', onDrop, false);
    });
  }

  /* ── Drag Handlers ── */

  function onDragStart(e) {
    var card = e.currentTarget;
    var iri = card.dataset.iri;
    var title = card.dataset.title || (card.querySelector('.quadrant-card-title') ? card.querySelector('.quadrant-card-title').textContent.trim() : iri);

    e.dataTransfer.setData('text/plain', iri);
    e.dataTransfer.setData('text/iri', iri);
    e.dataTransfer.setData('text/label', title);
    e.dataTransfer.effectAllowed = 'move';

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
    var cell = e.currentTarget.closest('.quadrant-cell');
    if (cell) cell.classList.add('drag-over');
  }

  function onDragLeave(e) {
    var cell = e.currentTarget.closest('.quadrant-cell');
    // Only remove if cursor truly left the cell body (prevents flicker on child elements)
    if (cell && !e.currentTarget.contains(e.relatedTarget)) {
      cell.classList.remove('drag-over');
    }
  }

  function onDrop(e) {
    e.preventDefault();
    e.stopPropagation();

    var targetBody = e.currentTarget;
    var cell = targetBody.closest('.quadrant-cell');
    if (cell) cell.classList.remove('drag-over');

    var iri = e.dataTransfer.getData('text/plain');
    if (!iri) return;

    var boardEl = targetBody.closest('.quadrant-board');
    if (!boardEl) return;

    // Read axis predicates from board data attributes
    var xPredicate = boardEl.dataset.xPredicate;
    var yPredicate = boardEl.dataset.yPredicate;
    if (!xPredicate || !yPredicate || !cell) return;

    // Read target cell axis values
    var newXValue = cell.dataset.xValue;
    var newYValue = cell.dataset.yValue;

    // Find the dragged card
    var cardEl = boardEl.querySelector('.quadrant-card[data-iri="' + CSS.escape(iri) + '"]');
    if (!cardEl) return;

    // Skip if dropped in the same cell
    var sourceBody = cardEl.closest('.quadrant-cell-body');
    if (sourceBody === targetBody) return;

    patchQuadrant(iri, xPredicate, yPredicate, newXValue, newYValue, cardEl, targetBody, sourceBody, boardEl);
  }

  /* ── Quadrant Patch ── */

  function patchQuadrant(iri, xPredicate, yPredicate, newXValue, newYValue, cardEl, targetBody, sourceBody, boardEl) {
    // Optimistic DOM move
    targetBody.appendChild(cardEl);
    _updateCellCounts(boardEl);

    var payload = {
      command: 'object.patch',
      params: {
        iri: iri,
        properties: {}
      }
    };
    payload.params.properties[xPredicate] = newXValue;
    payload.params.properties[yPredicate] = newYValue;

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
        console.error('quadrant: failed to patch for', iri, err);
        // Revert: move card back to source cell
        if (sourceBody) {
          sourceBody.appendChild(cardEl);
          _updateCellCounts(boardEl);
        }
        // Show toast if available
        if (typeof showToast === 'function') {
          showToast('Failed to update quadrant: ' + err.message);
        }
      });
  }

  /* ── Helpers ── */

  function _updateCellCounts(boardEl) {
    if (!boardEl) return;
    boardEl.querySelectorAll('.quadrant-cell').forEach(function (cell) {
      var body = cell.querySelector('.quadrant-cell-body');
      var countEl = cell.querySelector('.quadrant-cell-count');
      if (body && countEl) {
        countEl.textContent = body.querySelectorAll('.quadrant-card').length;
      }
    });
  }

  /* ── Export ── */
  window.SemPKM.initQuadrant = initQuadrant;

  /* ── Scope sync: re-fetch when a sibling view changes scope ── */
  document.addEventListener('sempkm:scope-changed', function (e) {
    var detail = e.detail || {};
    var boardEl = document.querySelector('.quadrant-board');
    if (!boardEl) return;

    // Avoid self-triggered re-fetch
    var ownPanel = boardEl.closest('.dv-panel');
    var ownPanelId = ownPanel ? (ownPanel.id || '') : '';
    if (detail.sourcePanel && detail.sourcePanel === ownPanelId) return;

    console.log('[quadrant] scope sync: scopeQuery=' + (detail.scopeQuery || '(none)') +
      ' from panel=' + (detail.sourcePanel || '(unknown)'));

    var typeIri = boardEl.dataset.typeIri || detail.selectedType || '';

    var url = '/browser/views/generic/quadrant';
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
