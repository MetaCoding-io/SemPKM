/**
 * okr.js — OKR Progress View interactivity module.
 *
 * Initialises click-to-edit on Key Result current values,
 * with scope-changed sync and stopPropagation() for dockview isolation.
 * Follows the quadrant.js / bmc.js IIFE + command API pattern.
 */

(function () {
  'use strict';

  var CURRENT_VALUE_PREDICATE = 'urn:sempkm:model:business-planning:currentValue';

  /**
   * Initialise OKR interactivity on a board element.
   * @param {HTMLElement} boardEl - The .okr-board container
   */
  function initOKR(boardEl) {
    if (!boardEl) return;

    /* Click-to-edit on current value elements */
    boardEl.querySelectorAll('.okr-current-value').forEach(function (el) {
      el.addEventListener('click', function (e) {
        e.stopPropagation();
        _startEdit(el);
      }, false);
    });

    /* Prevent dockview from intercepting drag events inside the board */
    ['dragstart', 'dragover', 'drop', 'dragleave'].forEach(function (evtName) {
      boardEl.addEventListener(evtName, function (e) {
        e.stopPropagation();
      }, false);
    });
  }

  /* ── Click-to-edit ── */

  function _startEdit(span) {
    if (span.querySelector('.okr-edit-input')) return; // already editing

    var currentText = span.textContent.trim();
    var row = span.closest('.okr-kr-row');
    var iri = row ? row.dataset.iri : '';
    if (!iri) return;

    var input = document.createElement('input');
    input.type = 'number';
    input.className = 'okr-edit-input';
    input.value = currentText;
    input.step = 'any';
    input.setAttribute('aria-label', 'Edit current value');

    var originalHTML = span.innerHTML;
    span.textContent = '';
    span.appendChild(input);
    input.focus();
    input.select();

    function commit() {
      var newValue = input.value.trim();
      if (newValue === '' || newValue === currentText) {
        _cancelEdit(span, originalHTML);
        return;
      }
      _saveValue(iri, newValue, span, originalHTML, row);
    }

    input.addEventListener('blur', commit, false);
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        input.blur();
      } else if (e.key === 'Escape') {
        input.removeEventListener('blur', commit);
        _cancelEdit(span, originalHTML);
      }
    }, false);
  }

  function _cancelEdit(span, originalHTML) {
    span.innerHTML = originalHTML;
  }

  /* ── Save Value via Command API ── */

  function _saveValue(iri, newValue, span, originalHTML, row) {
    var numericValue = parseFloat(newValue);
    if (isNaN(numericValue)) {
      _cancelEdit(span, originalHTML);
      return;
    }

    span.textContent = newValue;

    var payload = {
      command: 'object.patch',
      params: {
        iri: iri,
        properties: {}
      }
    };
    payload.params.properties[CURRENT_VALUE_PREDICATE] = numericValue;

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
        /* Brief success flash */
        if (row) {
          row.classList.add('okr-save-ok');
          setTimeout(function () { row.classList.remove('okr-save-ok'); }, 600);
        }
        /* Re-compute progress bar width after value change */
        _updateProgressBar(row, numericValue);
      })
      .catch(function (err) {
        console.error('okr: failed to patch currentValue for', iri, err);
        _cancelEdit(span, originalHTML);
        if (row) {
          row.classList.add('okr-save-error');
          setTimeout(function () { row.classList.remove('okr-save-error'); }, 1500);
        }
        if (typeof showToast === 'function') {
          showToast('Failed to update value: ' + err.message);
        }
      });
  }

  /* ── Progress bar update after edit ── */

  function _updateProgressBar(row, newCurrentValue) {
    if (!row) return;

    var valuesEl = row.querySelector('.okr-kr-values');
    if (!valuesEl) return;

    /* Parse "current / target [unit]" text to extract target */
    var text = valuesEl.textContent.trim();
    var match = text.match(/[\d.]+\s*\/\s*([\d.]+)/);
    if (!match) return;

    var targetValue = parseFloat(match[1]);
    if (!targetValue || targetValue <= 0) return;

    var progress = Math.min(100, Math.max(0, Math.round((newCurrentValue / targetValue) * 100)));

    /* Update percent display */
    var percentEl = row.querySelector('.okr-kr-percent');
    if (percentEl) {
      percentEl.textContent = progress + '%';
    }

    /* Update values display */
    var parts = text.split('/');
    if (parts.length >= 2) {
      valuesEl.textContent = newCurrentValue + ' / ' + parts[1].trim();
    }

    /* Update progress bar fill width and color */
    var fill = row.querySelector('.okr-progress-fill');
    if (fill) {
      fill.style.width = progress + '%';
      fill.classList.remove('okr-progress--green', 'okr-progress--amber', 'okr-progress--red');
      if (progress >= 70) {
        fill.classList.add('okr-progress--green');
      } else if (progress >= 30) {
        fill.classList.add('okr-progress--amber');
      } else {
        fill.classList.add('okr-progress--red');
      }
    }
  }

  /* ── Export ── */
  window.SemPKM.initOKR = initOKR;

  /* ── Scope sync: re-fetch when a sibling view changes scope ── */
  document.addEventListener('sempkm:scope-changed', function (e) {
    var detail = e.detail || {};
    var boardEl = document.querySelector('.okr-board');
    if (!boardEl) return;

    /* Avoid self-triggered re-fetch */
    var ownPanel = boardEl.closest('.dv-panel');
    var ownPanelId = ownPanel ? (ownPanel.id || '') : '';
    if (detail.sourcePanel && detail.sourcePanel === ownPanelId) return;

    console.log('[okr] scope sync: scopeQuery=' + (detail.scopeQuery || '(none)') +
      ' from panel=' + (detail.sourcePanel || '(unknown)'));

    var typeIri = boardEl.dataset.typeIri || detail.selectedType || '';

    var url = '/browser/views/generic/okr';
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

  // ── backward-compat shims (remove in T03) ──
  window.initOKR = window.SemPKM.initOKR;
})();
