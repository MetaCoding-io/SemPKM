/**
 * bmc.js — Business Model Canvas inline editing module.
 *
 * Initialises textarea editing with debounced saves for BMC sections.
 * Uses stopPropagation() on drag events to prevent dockview panel interference.
 * Follows the quadrant.js IIFE + command API pattern.
 */

(function () {
  'use strict';

  var DEBOUNCE_MS = 500;
  var SECTION_CONTENT_PREDICATE = 'urn:sempkm:model:business-planning:sectionContent';

  /* ── Debounce timers keyed by IRI ── */
  var _timers = {};

  /**
   * Initialise BMC inline editing on a board element.
   * @param {HTMLElement} boardEl - The .bmc-board container
   */
  function initBMC(boardEl) {
    if (!boardEl) return;

    /* Attach textarea listeners */
    boardEl.querySelectorAll('.bmc-item-textarea').forEach(function (textarea) {
      textarea.addEventListener('input', function () {
        _debounceSave(textarea);
      }, false);

      textarea.addEventListener('blur', function () {
        _immediateSave(textarea);
      }, false);
    });

    /* Prevent dockview from intercepting drag events inside the board */
    ['dragstart', 'dragover', 'drop', 'dragleave'].forEach(function (evtName) {
      boardEl.addEventListener(evtName, function (e) {
        e.stopPropagation();
      }, false);
    });
  }

  /* ── Debounced Save ── */

  function _debounceSave(textarea) {
    var iri = _getIri(textarea);
    if (!iri) return;

    if (_timers[iri]) {
      clearTimeout(_timers[iri]);
    }
    _timers[iri] = setTimeout(function () {
      delete _timers[iri];
      _saveSectionContent(textarea);
    }, DEBOUNCE_MS);
  }

  /* ── Immediate Save (blur) ── */

  function _immediateSave(textarea) {
    var iri = _getIri(textarea);
    if (!iri) return;

    /* Cancel any pending debounced save for this IRI */
    if (_timers[iri]) {
      clearTimeout(_timers[iri]);
      delete _timers[iri];
    }
    _saveSectionContent(textarea);
  }

  /* ── Save Content via Command API ── */

  function _saveSectionContent(textarea) {
    var iri = _getIri(textarea);
    if (!iri) return;

    var content = textarea.value;
    var payload = {
      command: 'object.patch',
      params: {
        iri: iri,
        properties: {}
      }
    };
    payload.params.properties[SECTION_CONTENT_PREDICATE] = content;

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
        textarea.classList.add('bmc-save-ok');
        setTimeout(function () { textarea.classList.remove('bmc-save-ok'); }, 600);
      })
      .catch(function (err) {
        console.error('bmc: failed to patch section content for', iri, err);
        textarea.classList.add('bmc-save-error');
        setTimeout(function () { textarea.classList.remove('bmc-save-error'); }, 1500);
        if (typeof showToast === 'function') {
          showToast('Failed to save section: ' + err.message);
        }
      });
  }

  /* ── Helpers ── */

  function _getIri(textarea) {
    var item = textarea.closest('.bmc-item');
    return item ? item.dataset.iri : (textarea.dataset.iri || '');
  }

  /* ── Export ── */
  window.initBMC = initBMC;

  /* ── Scope sync: re-fetch when a sibling view changes scope ── */
  document.addEventListener('sempkm:scope-changed', function (e) {
    var detail = e.detail || {};
    var boardEl = document.querySelector('.bmc-board');
    if (!boardEl) return;

    /* Avoid self-triggered re-fetch */
    var ownPanel = boardEl.closest('.dv-panel');
    var ownPanelId = ownPanel ? (ownPanel.id || '') : '';
    if (detail.sourcePanel && detail.sourcePanel === ownPanelId) return;

    console.log('[bmc] scope sync: scopeQuery=' + (detail.scopeQuery || '(none)') +
      ' from panel=' + (detail.sourcePanel || '(unknown)'));

    var typeIri = boardEl.dataset.typeIri || detail.selectedType || '';

    var url = '/browser/views/generic/bmc';
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
