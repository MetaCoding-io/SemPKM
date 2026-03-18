/**
 * SemPKM Capture — background service worker.
 *
 * Registers the "Save to SemPKM" context menu item on extension install
 * and handles context menu clicks. Stores selection data in session storage
 * and opens the popup for capture.
 *
 * @module background/service-worker
 */

import { getClient, getSettings } from '../shared/storage.js';

// ---------------------------------------------------------------------------
// Context menu registration
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
// Context menu click handler
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
