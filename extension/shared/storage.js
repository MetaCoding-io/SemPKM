/**
 * Settings persistence wrapper for chrome.storage.sync.
 *
 * Provides typed getSettings/saveSettings and a getClient() factory
 * that returns a configured SemPKMClient or null if unconfigured.
 *
 * @module shared/storage
 */

import { SemPKMClient } from './api-client.js';

/** Default settings applied when no stored value exists. */
const DEFAULTS = {
  instanceUrl: '',
  apiKey: '',
  defaultType: '',
  autoFillTitle: true,
  autoFillUrl: true,
  includeSelection: true,
  autoCheckContext: true,
  contextCheckDelay: 2000,
  contextTimeout: 5000,
};

/** All settings keys — used for chrome.storage.sync.get(). */
const SETTINGS_KEYS = Object.keys(DEFAULTS);

/**
 * Resolve the storage area to use.
 * Prefers chrome.storage.sync; falls back to chrome.storage.local
 * if sync is unavailable (e.g. in some testing environments).
 *
 * @returns {chrome.storage.StorageArea}
 */
function _storageArea() {
  if (typeof chrome !== 'undefined' && chrome.storage) {
    return chrome.storage.sync || chrome.storage.local;
  }
  // Fallback for non-extension contexts (testing)
  return null;
}

/**
 * Load persisted settings, merged with defaults.
 *
 * @returns {Promise<{instanceUrl: string, apiKey: string, defaultType: string, autoFillTitle: boolean, autoFillUrl: boolean, includeSelection: boolean}>}
 */
export async function getSettings() {
  const area = _storageArea();
  if (!area) {
    return { ...DEFAULTS };
  }

  return new Promise((resolve) => {
    area.get(DEFAULTS, (items) => {
      // Merge only known keys to avoid stale data leaking in
      const settings = {};
      for (const key of SETTINGS_KEYS) {
        settings[key] = items[key] !== undefined ? items[key] : DEFAULTS[key];
      }
      resolve(settings);
    });
  });
}

/**
 * Persist settings to chrome.storage.sync.
 *
 * @param {Object} settings - Partial or full settings object to save.
 *   Only provided keys are written; missing keys retain their stored value.
 * @returns {Promise<void>}
 */
export async function saveSettings(settings) {
  const area = _storageArea();
  if (!area) {
    console.warn('storage.saveSettings: no storage area available');
    return;
  }

  // Only persist known keys
  const toSave = {};
  for (const key of SETTINGS_KEYS) {
    if (settings[key] !== undefined) {
      toSave[key] = settings[key];
    }
  }

  return new Promise((resolve) => {
    area.set(toSave, () => {
      resolve();
    });
  });
}

/**
 * Create a SemPKMClient from stored settings.
 *
 * Returns null if instanceUrl or apiKey are not configured,
 * rather than constructing a client that will fail on every call.
 *
 * @returns {Promise<SemPKMClient|null>}
 */
export async function getClient() {
  const settings = await getSettings();

  if (!settings.instanceUrl || !settings.apiKey) {
    return null;
  }

  return new SemPKMClient(settings.instanceUrl, settings.apiKey);
}
