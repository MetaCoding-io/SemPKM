/**
 * SemPKM Capture — background service worker.
 *
 * Registers the "Save to SemPKM" context menu item on extension install
 * and handles context menu clicks. The click handler is a shell that
 * will be implemented in S03 (content scripts integration).
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
// Context menu click handler (shell — S03 will implement full behavior)
// ---------------------------------------------------------------------------

chrome.contextMenus.onClicked.addListener((info, tab) => {
  if (info.menuItemId === 'save-to-sempkm') {
    // S03 will implement: open popup with selected text pre-filled
    console.log('[SemPKM] Save to SemPKM clicked:', {
      selectionText: info.selectionText,
      pageUrl: info.pageUrl,
      tabId: tab?.id,
    });
  }
});
