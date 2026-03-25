/**
 * decision-matrix.js — Decision Matrix weighted scoring module.
 *
 * Initialises client-side column sorting on the scoring table,
 * with scope-changed sync and stopPropagation() for dockview isolation.
 * Follows the quadrant.js / bmc.js IIFE + command API pattern.
 */

(function () {
  'use strict';

  /**
   * Initialise Decision Matrix interactivity on a board element.
   * @param {HTMLElement} boardEl - The .dm-board container
   */
  function initDecisionMatrix(boardEl) {
    if (!boardEl) return;

    var table = boardEl.querySelector('.dm-table');
    if (!table) return;

    /* Attach sort handlers to criterion headers and total header */
    table.querySelectorAll('.dm-th-criterion, .dm-th-total').forEach(function (th) {
      th.addEventListener('click', function () {
        _toggleSort(table, th);
      }, false);
    });

    /* Prevent dockview from intercepting drag events inside the board */
    ['dragstart', 'dragover', 'drop', 'dragleave'].forEach(function (evtName) {
      boardEl.addEventListener(evtName, function (e) {
        e.stopPropagation();
      }, false);
    });
  }

  /* ── Column Sorting ── */

  function _toggleSort(table, clickedTh) {
    var thead = table.querySelector('thead tr');
    if (!thead) return;

    var allThs = thead.querySelectorAll('th');
    var colIndex = Array.prototype.indexOf.call(allThs, clickedTh);
    if (colIndex < 0) return;

    /* Determine sort direction */
    var isAsc = clickedTh.classList.contains('sort-asc');
    var newDir = isAsc ? 'desc' : 'asc';

    /* Clear all sort indicators */
    allThs.forEach(function (th) {
      th.classList.remove('sort-asc', 'sort-desc', 'sort-active');
    });

    /* Set new sort indicator */
    clickedTh.classList.add('sort-' + newDir, 'sort-active');

    /* Sort tbody rows */
    var tbody = table.querySelector('tbody');
    if (!tbody) return;

    var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr.dm-row'));

    rows.sort(function (a, b) {
      var cellA = a.querySelectorAll('td')[colIndex];
      var cellB = b.querySelectorAll('td')[colIndex];
      if (!cellA || !cellB) return 0;

      var valA = _parseNumeric(cellA);
      var valB = _parseNumeric(cellB);

      if (newDir === 'asc') {
        return valA - valB;
      }
      return valB - valA;
    });

    /* Re-append sorted rows and update ranks */
    rows.forEach(function (row, i) {
      tbody.appendChild(row);
    });

    _updateRanks(tbody, newDir);
  }

  function _parseNumeric(td) {
    var text = td.textContent.trim();
    /* Handle emoji rank cells — extract number after emoji or plain number */
    var num = parseFloat(text.replace(/[^\d.\-]/g, ''));
    return isNaN(num) ? 0 : num;
  }

  function _updateRanks(tbody, sortDir) {
    var rows = Array.prototype.slice.call(tbody.querySelectorAll('tr.dm-row'));
    var rank = 1;
    var prevScore = null;

    rows.forEach(function (row, i) {
      /* Get weighted total from last real td */
      var cells = row.querySelectorAll('td');
      var totalCell = null;
      for (var c = cells.length - 1; c >= 0; c--) {
        if (cells[c].classList.contains('dm-cell-total')) {
          totalCell = cells[c];
          break;
        }
      }

      var score = totalCell ? _parseNumeric(totalCell) : 0;

      /* Tie-aware ranking (only meaningful for desc/total sort) */
      if (sortDir === 'desc') {
        if (prevScore !== null && score < prevScore) {
          rank = i + 1;
        }
        prevScore = score;
      } else {
        rank = i + 1;
      }

      row.dataset.rank = rank;

      /* Update rank cell display */
      var rankCell = row.querySelector('.dm-cell-rank');
      if (rankCell) {
        if (rank === 1) rankCell.textContent = '🥇';
        else if (rank === 2) rankCell.textContent = '🥈';
        else if (rank === 3) rankCell.textContent = '🥉';
        else rankCell.textContent = rank;
      }
    });
  }

  /* ── Export ── */
  window.SemPKM.initDecisionMatrix = initDecisionMatrix;

  /* ── Scope sync: re-fetch when a sibling view changes scope ── */
  document.addEventListener('sempkm:scope-changed', function (e) {
    var detail = e.detail || {};
    var boardEl = document.querySelector('.dm-board');
    if (!boardEl) return;

    /* Avoid self-triggered re-fetch */
    var ownPanel = boardEl.closest('.dv-panel');
    var ownPanelId = ownPanel ? (ownPanel.id || '') : '';
    if (detail.sourcePanel && detail.sourcePanel === ownPanelId) return;

    SemPKM.debug('decision-matrix', 'scope sync: scopeQuery=' + (detail.scopeQuery || '(none)') +
      ' from panel=' + (detail.sourcePanel || '(unknown)'));

    var typeIri = boardEl.dataset.typeIri || detail.selectedType || '';

    var url = '/browser/views/generic/decision-matrix';
    var params = [];
    if (detail.scopeQuery) params.push('scope_query=' + encodeURIComponent(detail.scopeQuery));
    if (typeIri) params.push('type=' + encodeURIComponent(typeIri));
    if (params.length) url += '?' + params.join('&');

    /* Visual feedback */
    boardEl.classList.add('scope-syncing');
    setTimeout(function () { boardEl.classList.remove('scope-syncing'); }, 300);

    var target = boardEl.closest('.group-editor-area') || boardEl.parentElement;
    if (target && typeof htmx !== 'undefined') {
      htmx.ajax('GET', url, { target: target, swap: 'innerHTML' });
    }
  });

})();
