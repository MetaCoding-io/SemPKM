/**
 * SemPKM Context Sidebar — renders grouped context results.
 *
 * Communicates with the service worker via chrome.runtime.sendMessage
 * to fetch cached (or fresh) context results, then renders them
 * grouped by type using SemPKMContextUtils.groupByType().
 *
 * Loaded as a plain script (not ES module) so it can access
 * globalThis.SemPKMContextUtils set by context-utils.js.
 *
 * @module sidebar/sidebar
 */

/* global SemPKMContextUtils, chrome */

(function () {
  'use strict';

  // ── Constants ──────────────────────────────────────────────────
  const LOG_PREFIX = '[SemPKM Sidebar]';

  /** Match-type → display config */
  const MATCH_BADGES = {
    url:     { label: 'URL',     cls: 'badge-url' },
    title:   { label: 'Title',   cls: 'badge-title' },
    keyword: { label: 'Keyword', cls: 'badge-keyword' },
  };

  // ── DOM refs ───────────────────────────────────────────────────
  const $loading  = document.getElementById('loading');
  const $error    = document.getElementById('error');
  const $errorMsg = document.getElementById('error-message');
  const $empty    = document.getElementById('empty');
  const $emptyMsg = document.getElementById('empty-message');
  const $results  = document.getElementById('results');
  const $retryBtn = document.getElementById('retry-btn');
  const $refreshBtn = document.getElementById('refresh-btn');
  const $footerLink = document.getElementById('footer-link');
  const $toastContainer = document.getElementById('toast-container');

  // ── State ──────────────────────────────────────────────────────
  let _instanceUrl = '';
  let _currentTabUrl = '';
  let _currentTabTitle = '';

  // ── State switching ────────────────────────────────────────────

  /** Show exactly one state panel, hide the rest. */
  function _showState(name) {
    $loading.hidden = name !== 'loading';
    $error.hidden   = name !== 'error';
    $empty.hidden   = name !== 'empty';
    $results.hidden = name !== 'results';
  }

  // ── Toast notification ─────────────────────────────────────────

  /**
   * Show a brief toast notification at the bottom of the sidebar.
   * Auto-dismisses after 3 seconds.
   *
   * @param {string} message
   * @param {'info'|'error'} [type='info']
   */
  function showToast(message, type) {
    type = type || 'info';
    const el = document.createElement('div');
    el.className = 'toast toast-' + type;
    el.textContent = message;
    $toastContainer.appendChild(el);

    // Trigger reflow then animate in
    void el.offsetWidth;
    el.classList.add('toast-visible');

    setTimeout(function () {
      el.classList.add('toast-fade-out');
      el.addEventListener('animationend', function () {
        el.remove();
      });
    }, 3000);
  }

  // ── Rendering ──────────────────────────────────────────────────

  /**
   * Truncate text to maxLen, appending ellipsis if truncated.
   * @param {string} text
   * @param {number} maxLen
   * @returns {string}
   */
  function _truncate(text, maxLen) {
    if (!text || text.length <= maxLen) return text || '';
    return text.slice(0, maxLen).trimEnd() + '…';
  }

  /**
   * Render a single result card.
   *
   * @param {Object} item - Ranked result from context-utils
   * @returns {HTMLElement}
   */
  function _renderCard(item) {
    const card = document.createElement('div');
    card.className = 'result-card';

    // ── Top row: label + match badge ──
    const topRow = document.createElement('div');
    topRow.className = 'card-top';

    const label = document.createElement('a');
    label.className = 'card-label';
    label.href = '#';
    label.textContent = item.label || item.iri;
    label.title = item.label || item.iri;
    label.addEventListener('click', function (e) {
      e.preventDefault();
      _openObject(item.iri);
    });

    const badgeInfo = MATCH_BADGES[item.match_type] || MATCH_BADGES.keyword;
    const badge = document.createElement('span');
    badge.className = 'match-badge ' + badgeInfo.cls;
    badge.textContent = badgeInfo.label;

    topRow.appendChild(label);
    topRow.appendChild(badge);
    card.appendChild(topRow);

    // ── Snippet ──
    if (item.snippet) {
      const snippet = document.createElement('p');
      snippet.className = 'card-snippet';
      snippet.textContent = _truncate(item.snippet, 120);
      card.appendChild(snippet);
    }

    // ── Action bar ──
    const actions = document.createElement('div');
    actions.className = 'card-actions';

    const openBtn = _actionButton('Open', 'action-open', function () {
      _openObject(item.iri);
    });

    const linkBtn = _actionButton('Link to page', 'action-link', function () {
      _linkToPage(item.iri, linkBtn);
    });

    const evidenceBtn = _actionButton('Add Evidence', 'action-stub', function () {
      showToast('Add Evidence — coming in next update');
    });

    actions.appendChild(openBtn);
    actions.appendChild(linkBtn);
    actions.appendChild(evidenceBtn);
    card.appendChild(actions);

    return card;
  }

  /**
   * Create a compact action button.
   *
   * @param {string} text
   * @param {string} cls - Extra CSS class
   * @param {Function} handler
   * @returns {HTMLButtonElement}
   */
  function _actionButton(text, cls, handler) {
    const btn = document.createElement('button');
    btn.className = 'card-action-btn ' + cls;
    btn.textContent = text;
    btn.addEventListener('click', handler);
    return btn;
  }

  /**
   * Render a collapsible type group section.
   *
   * @param {Object} group - {typeLabel, typeIri, results}
   * @returns {HTMLElement}
   */
  function _renderGroup(group) {
    const section = document.createElement('div');
    section.className = 'type-group';

    // Header (click to toggle)
    const header = document.createElement('button');
    header.className = 'group-header';
    header.setAttribute('aria-expanded', 'true');

    const chevron = document.createElement('span');
    chevron.className = 'group-chevron';
    chevron.textContent = '▾';

    const title = document.createElement('span');
    title.className = 'group-title';
    title.textContent = group.typeLabel;

    const count = document.createElement('span');
    count.className = 'group-count';
    count.textContent = group.results.length;

    header.appendChild(chevron);
    header.appendChild(title);
    header.appendChild(count);

    const body = document.createElement('div');
    body.className = 'group-body';

    for (var i = 0; i < group.results.length; i++) {
      body.appendChild(_renderCard(group.results[i]));
    }

    header.addEventListener('click', function () {
      var expanded = header.getAttribute('aria-expanded') === 'true';
      header.setAttribute('aria-expanded', String(!expanded));
      body.hidden = expanded;
      chevron.textContent = expanded ? '▸' : '▾';
    });

    section.appendChild(header);
    section.appendChild(body);
    return section;
  }

  /**
   * Render all results into grouped sections.
   *
   * @param {Array} results - Ranked results array
   */
  function renderResults(results) {
    $results.innerHTML = '';
    var groups = SemPKMContextUtils.groupByType(results);
    console.log(LOG_PREFIX, 'Rendering', results.length, 'results in', groups.length, 'groups');

    for (var i = 0; i < groups.length; i++) {
      $results.appendChild(_renderGroup(groups[i]));
    }
    _showState('results');
  }

  // ── Object open action ─────────────────────────────────────────

  /**
   * Open a SemPKM object in a new browser tab.
   *
   * @param {string} iri - The object IRI
   */
  function _openObject(iri) {
    if (!_instanceUrl) {
      showToast('Configure SemPKM instance in extension settings', 'error');
      console.warn(LOG_PREFIX, 'Cannot open object: instanceUrl not configured');
      return;
    }

    var url = _instanceUrl + '/browser/objects/' + encodeURIComponent(iri);
    console.log(LOG_PREFIX, 'Opening object:', url);
    chrome.tabs.create({ url: url });
  }

  // ── Link-to-page action ────────────────────────────────────────

  /**
   * Create a schema:url edge from the given object to the current tab URL.
   *
   * @param {string} objectIri - The source object IRI
   * @param {HTMLButtonElement} btn - The button element (for loading state)
   */
  function _linkToPage(objectIri, btn) {
    if (!_currentTabUrl) {
      showToast('Navigate to a page first', 'error');
      return;
    }

    btn.disabled = true;
    btn.textContent = 'Linking…';

    chrome.runtime.sendMessage(
      { type: 'linkToPage', objectIri: objectIri, pageUrl: _currentTabUrl },
      function (response) {
        if (chrome.runtime.lastError) {
          console.error(LOG_PREFIX, 'linkToPage error:', chrome.runtime.lastError.message);
          showToast(chrome.runtime.lastError.message || 'Failed to link', 'error');
          btn.disabled = false;
          btn.textContent = 'Link to page';
          return;
        }

        if (response && response.success) {
          showToast('✓ Linked to this page');
        } else {
          showToast((response && response.error) || 'Failed to link', 'error');
        }
        btn.disabled = false;
        btn.textContent = 'Link to page';
      }
    );
  }

  // ── Data fetching ──────────────────────────────────────────────

  /**
   * Request context results from the service worker.
   *
   * @param {boolean} [forceRefresh=false] - Send refreshContextResults instead of getContextResults
   */
  function fetchResults(forceRefresh) {
    _showState('loading');

    var msgType = forceRefresh ? 'refreshContextResults' : 'getContextResults';
    console.log(LOG_PREFIX, 'Requesting results:', msgType);

    chrome.runtime.sendMessage({ type: msgType }, function (response) {
      if (chrome.runtime.lastError) {
        console.error(LOG_PREFIX, 'Message error:', chrome.runtime.lastError.message);
        $errorMsg.textContent = 'Could not reach service worker. Try reloading the extension.';
        _showState('error');
        return;
      }

      if (!response) {
        console.warn(LOG_PREFIX, 'Empty response from service worker');
        $errorMsg.textContent = 'No response from service worker.';
        _showState('error');
        return;
      }

      if (response.error) {
        // Distinguish between "no cached results" and real errors
        if (response.error === 'No results cached' || response.error === 'No active tab') {
          console.log(LOG_PREFIX, 'No cached results — showing empty');
          $emptyMsg.textContent = 'Navigate to a page to see related objects.';
          _showState('empty');
        } else {
          console.error(LOG_PREFIX, 'Error:', response.error);
          $errorMsg.textContent = response.error;
          _showState('error');
        }
        return;
      }

      if (response.results && response.results.length > 0) {
        renderResults(response.results);
      } else {
        $emptyMsg.textContent = 'No related objects found for this page.';
        _showState('empty');
      }
    });
  }

  // ── Initialization ─────────────────────────────────────────────

  function init() {
    console.log(LOG_PREFIX, 'Initializing');

    // Read instanceUrl from storage
    var area = chrome.storage.sync || chrome.storage.local;
    area.get({ instanceUrl: '' }, function (items) {
      _instanceUrl = (items.instanceUrl || '').replace(/\/+$/, '');

      // Set footer link if configured
      if (_instanceUrl) {
        $footerLink.href = _instanceUrl;
      }
    });

    // Track the current tab URL
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
      if (tabs[0]) {
        _currentTabUrl = tabs[0].url || '';
        _currentTabTitle = tabs[0].title || '';
      }
    });

    // Bind retry button
    $retryBtn.addEventListener('click', function () {
      fetchResults(true);
    });

    // Bind refresh button
    $refreshBtn.addEventListener('click', function () {
      fetchResults(true);
    });

    // Fetch initial results
    fetchResults(false);
  }

  // ── Message listener for live updates ──────────────────────────

  chrome.runtime.onMessage.addListener(function (message) {
    if (message.type === 'contextResultsUpdated') {
      console.log(LOG_PREFIX, 'Received contextResultsUpdated — re-fetching');
      // Refresh current tab URL in case of navigation
      chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
        if (tabs[0]) {
          _currentTabUrl = tabs[0].url || '';
          _currentTabTitle = tabs[0].title || '';
        }
      });
      fetchResults(false);
    }
  });

  // ── Boot ───────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', init);
})();
