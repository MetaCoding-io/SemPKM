/**
 * SemPKM Capture — background service worker.
 *
 * Registers the "Save to SemPKM" context menu item on extension install,
 * handles context menu clicks, and runs the context overlay pipeline:
 * tab navigation → debounce → context query → rank → cache → badge.
 *
 * @module background/service-worker
 */

// Load shared pure utilities (rankResults, groupByType, LRUCache)
importScripts('../shared/context-utils.js');

// ---------------------------------------------------------------------------
// State — survives within a single service worker lifecycle
// ---------------------------------------------------------------------------

/** @type {Map<number, number>} tabId → setTimeout timer ID */
const _debounceTimers = new Map();

/** @type {InstanceType<typeof SemPKMContextUtils.LRUCache>} URL → {results, timestamp} */
const contextCache = new SemPKMContextUtils.LRUCache(100);

// ---------------------------------------------------------------------------
// Settings helpers (inline fetch — can't import ES module in classic SW)
// ---------------------------------------------------------------------------

/**
 * Read API connection settings from chrome.storage.
 * Returns null if instanceUrl or apiKey are not configured.
 *
 * @returns {Promise<{instanceUrl: string, apiKey: string, autoCheckContext: boolean, contextCheckDelay: number, contextTimeout: number}|null>}
 */
async function _getApiConfig() {
  const defaults = {
    instanceUrl: '',
    apiKey: '',
    autoCheckContext: true,
    contextCheckDelay: 2000,
    contextTimeout: 5000,
  };

  return new Promise((resolve) => {
    const area = chrome.storage.sync || chrome.storage.local;
    area.get(defaults, (items) => {
      if (!items.instanceUrl || !items.apiKey) {
        resolve(null);
        return;
      }
      resolve({
        instanceUrl: items.instanceUrl.replace(/\/+$/, ''),
        apiKey: items.apiKey,
        autoCheckContext: items.autoCheckContext,
        contextCheckDelay: items.contextCheckDelay,
        contextTimeout: items.contextTimeout,
      });
    });
  });
}

/**
 * Call POST /api/context-query with Bearer auth.
 * Applies contextTimeout via AbortController.
 *
 * @param {string} url - Page URL
 * @param {string} title - Page title
 * @param {string} keywords - Extracted keywords
 * @returns {Promise<{results: Array, total: number}>}
 */
async function _queryContext(url, title, keywords) {
  const config = await _getApiConfig();
  if (!config) throw new Error('SemPKM not configured (missing instanceUrl or apiKey)');

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), config.contextTimeout);

  const body = {};
  if (url) body.url = url;
  if (title) body.title = title;
  if (keywords) body.keywords = keywords;

  try {
    const response = await fetch(`${config.instanceUrl}/api/context-query`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${config.apiKey}`,
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      },
      body: JSON.stringify(body),
      signal: controller.signal,
    });

    if (!response.ok) {
      let detail = response.statusText;
      try {
        const errBody = await response.json();
        detail = errBody.detail || errBody.error || detail;
      } catch { /* noop */ }
      throw new Error(`API ${response.status}: ${detail}`);
    }

    return await response.json();
  } finally {
    clearTimeout(timeoutId);
  }
}

// ---------------------------------------------------------------------------
// Keyword extraction
// ---------------------------------------------------------------------------

/**
 * Extract search keywords from a page title.
 * Splits on common separators, deduplicates, filters short words.
 *
 * @param {string} title
 * @returns {string} Space-joined keywords
 */
function _extractKeywords(title) {
  if (!title) return '';
  const words = title
    .split(/[-|—·/]/)
    .map((w) => w.trim())
    .filter((w) => w.length >= 3);
  return [...new Set(words)].join(' ');
}

// ---------------------------------------------------------------------------
// Badge helpers
// ---------------------------------------------------------------------------

/**
 * Set the extension badge for a specific tab.
 *
 * @param {number} tabId
 * @param {number|string} countOrIndicator - Number of results, or "!" for error
 */
function _setBadge(tabId, countOrIndicator) {
  const text =
    countOrIndicator === '!'
      ? '!'
      : countOrIndicator > 0
        ? String(countOrIndicator)
        : '';

  const color = countOrIndicator === '!' ? '#ef4444' : '#0d9488';

  chrome.action.setBadgeText({ text, tabId });
  chrome.action.setBadgeBackgroundColor({ color, tabId });
}

// ---------------------------------------------------------------------------
// Core pipeline — tab ready handler
// ---------------------------------------------------------------------------

/**
 * Called after debounce when a tab finishes loading.
 * Checks cache, queries API, ranks results, sets badge.
 *
 * @param {number} tabId
 * @param {string} url
 * @param {string} title
 */
async function _handleTabReady(tabId, url, title) {
  // Check cache first
  if (contextCache.has(url)) {
    const cached = contextCache.get(url);
    const count = cached.results.length;
    console.log(`[SemPKM] Cache hit for ${url}: ${count} results`);
    _setBadge(tabId, count);
    return;
  }

  const keywords = _extractKeywords(title);
  console.log(`[SemPKM] Querying context for ${url}`);

  try {
    const data = await _queryContext(url, title, keywords);
    const ranked = SemPKMContextUtils.rankResults(data.results || []);
    contextCache.set(url, { results: ranked, timestamp: Date.now() });
    console.log(`[SemPKM] Context query: ${ranked.length} results for ${url}`);
    _setBadge(tabId, ranked.length);
  } catch (err) {
    console.error(`[SemPKM] Context query error: ${err.message}`);
    _setBadge(tabId, '!');
  }
}

// ---------------------------------------------------------------------------
// Tab navigation listener with debounce
// ---------------------------------------------------------------------------

chrome.tabs.onUpdated.addListener(async (tabId, changeInfo, tab) => {
  // Only act on completed loads for http(s) URLs
  if (changeInfo.status !== 'complete') return;
  if (!tab.url || !tab.url.startsWith('http')) return;

  console.log(`[SemPKM] Tab ${tabId} loaded: ${tab.url}`);

  // Read settings to check if auto-check is enabled
  const config = await _getApiConfig();
  if (!config) return; // Not configured — skip silently
  if (!config.autoCheckContext) return;

  // Clear any pending debounce for this tab
  if (_debounceTimers.has(tabId)) {
    clearTimeout(_debounceTimers.get(tabId));
    _debounceTimers.delete(tabId);
  }

  // Debounce: wait contextCheckDelay before querying
  const delay = config.contextCheckDelay;
  const timerId = setTimeout(() => {
    _debounceTimers.delete(tabId);
    _handleTabReady(tabId, tab.url, tab.title);
  }, delay);
  _debounceTimers.set(tabId, timerId);
});

// ---------------------------------------------------------------------------
// Tab removal cleanup
// ---------------------------------------------------------------------------

chrome.tabs.onRemoved.addListener((tabId) => {
  if (_debounceTimers.has(tabId)) {
    clearTimeout(_debounceTimers.get(tabId));
    _debounceTimers.delete(tabId);
  }
});

// ---------------------------------------------------------------------------
// Message handlers for sidebar communication
// ---------------------------------------------------------------------------

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message.type === 'getContextResults') {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
      const tab = tabs[0];
      if (!tab || !tab.url) {
        sendResponse({ results: [], url: '', error: 'No active tab' });
        return;
      }

      if (contextCache.has(tab.url)) {
        const cached = contextCache.get(tab.url);
        sendResponse({
          results: cached.results,
          url: tab.url,
          cached: true,
        });
      } else {
        sendResponse({
          results: [],
          url: tab.url,
          error: 'No results cached',
        });
      }
    });
    return true; // Async sendResponse
  }

  if (message.type === 'refreshContextResults') {
    chrome.tabs.query({ active: true, currentWindow: true }, async (tabs) => {
      const tab = tabs[0];
      if (!tab || !tab.url) {
        sendResponse({ results: [], url: '', error: 'No active tab' });
        return;
      }

      const url = tab.url;
      const title = tab.title || '';
      const keywords = _extractKeywords(title);

      console.log(`[SemPKM] Refresh: querying context for ${url}`);

      try {
        const data = await _queryContext(url, title, keywords);
        const ranked = SemPKMContextUtils.rankResults(data.results || []);
        contextCache.set(url, { results: ranked, timestamp: Date.now() });
        _setBadge(tab.id, ranked.length);

        console.log(`[SemPKM] Refresh: ${ranked.length} results for ${url}`);
        sendResponse({ results: ranked, url, cached: false });
      } catch (err) {
        console.error(`[SemPKM] Refresh query error: ${err.message}`);
        _setBadge(tab.id, '!');
        sendResponse({ results: [], url, error: err.message });
      }
    });
    return true; // Async sendResponse
  }

  if (message.type === 'linkToPage') {
    (async () => {
      try {
        const config = await _getApiConfig();
        if (!config) {
          sendResponse({ error: 'SemPKM not configured' });
          return;
        }

        const response = await fetch(`${config.instanceUrl}/api/commands`, {
          method: 'POST',
          headers: {
            'Authorization': `Bearer ${config.apiKey}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json',
          },
          body: JSON.stringify({
            command: 'edge.create',
            params: {
              source: message.objectIri,
              target: message.pageUrl,
              predicate: 'schema:url',
            },
          }),
        });

        if (!response.ok) {
          let detail = response.statusText;
          try {
            const errBody = await response.json();
            detail = errBody.detail || errBody.error || detail;
          } catch { /* noop */ }
          console.error(`[SemPKM] linkToPage: error: ${detail}`);
          sendResponse({ error: detail });
          return;
        }

        console.log('[SemPKM] linkToPage: success');
        sendResponse({ success: true });
      } catch (err) {
        console.error(`[SemPKM] linkToPage: error: ${err.message}`);
        sendResponse({ error: err.message });
      }
    })();
    return true; // Async sendResponse
  }
});

// ---------------------------------------------------------------------------
// Alt+K command — open context sidebar
// ---------------------------------------------------------------------------

chrome.commands.onCommand.addListener(async (command) => {
  if (command === 'open-context-sidebar') {
    console.log('[SemPKM] Opening context sidebar');
    try {
      if (chrome.sidePanel && chrome.sidePanel.open) {
        const win = await chrome.windows.getCurrent();
        await chrome.sidePanel.open({ windowId: win.id });
      } else if (typeof browser !== 'undefined' && browser.sidebarAction) {
        // Firefox fallback
        browser.sidebarAction.open();
      } else {
        console.warn('[SemPKM] Side Panel API not available');
      }
    } catch (err) {
      console.error(`[SemPKM] Could not open sidebar: ${err.message}`);
    }
  }
});

// ---------------------------------------------------------------------------
// Context menu registration (existing)
// ---------------------------------------------------------------------------

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({
    id: 'save-to-sempkm',
    title: 'Save to SemPKM',
    contexts: ['selection'],
  });
  console.log('[SemPKM] Context menu "Save to SemPKM" registered');
});

// ---------------------------------------------------------------------------
// Context menu click handler (existing)
// ---------------------------------------------------------------------------

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId === 'save-to-sempkm') {
    await chrome.storage.session.set({
      contextMenuData: {
        selectionText: info.selectionText || '',
        pageUrl: info.pageUrl || '',
        pageTitle: tab?.title || '',
      },
    });
    console.log('[SemPKM] Context menu: stored selection data');

    try {
      await chrome.action.openPopup();
    } catch (err) {
      console.warn('[SemPKM] Could not open popup:', err.message);
      // Fallback: open popup.html as a new window
      chrome.windows.create({
        url: chrome.runtime.getURL('popup/popup.html'),
        type: 'popup',
        width: 420,
        height: 520,
      });
    }
  }
});
