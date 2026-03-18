/**
 * SemPKM Capture — popup logic.
 *
 * Handles the complete capture flow: load settings → check connection →
 * populate type selector → gather form data → create object → show feedback.
 *
 * @module popup/popup
 */

import { SemPKMClient, SemPKMError } from '../shared/api-client.js';
import { getSettings } from '../shared/storage.js';

/* ── DOM references ────────────────────────────────────────────── */
const $connectionDot   = document.getElementById('connection-dot');
const $unconfigured    = document.getElementById('unconfigured-state');
const $openSettings    = document.getElementById('open-settings');
const $captureForm     = document.getElementById('capture-form');
const $typeSelect      = document.getElementById('type-select');
const $titleInput      = document.getElementById('title-input');
const $titleError      = document.getElementById('title-error');
const $bodyInput       = document.getElementById('body-input');
const $urlInput        = document.getElementById('url-input');
const $saveBtn         = document.getElementById('save-btn');
const $saveBtnLabel    = document.querySelector('#save-btn .btn-label');
const $saveBtnSpinner  = document.querySelector('#save-btn .btn-spinner');
const $toastContainer  = document.getElementById('toast-container');

/** Active SemPKMClient instance (null until configured). */
let client = null;

/* ── Helpers ───────────────────────────────────────────────────── */

/** Show/hide an element via the `hidden` class. */
function setVisible(el, visible) {
  el.classList.toggle('hidden', !visible);
}

/**
 * Set the connection status dot color and tooltip.
 * @param {'connected'|'error'|'loading'} state
 * @param {string} [tooltip]
 */
function setConnectionDot(state, tooltip) {
  $connectionDot.className = 'connection-dot';
  if (state === 'connected') {
    $connectionDot.classList.add('dot-green');
    $connectionDot.title = tooltip || 'Connected';
  } else if (state === 'error') {
    $connectionDot.classList.add('dot-red');
    $connectionDot.title = tooltip || 'Connection error';
  } else {
    $connectionDot.classList.add('dot-loading');
    $connectionDot.title = tooltip || 'Checking connection…';
  }
}

/**
 * Display a toast notification at the bottom of the popup.
 * Auto-dismisses after 3 seconds.
 *
 * @param {string} message - Text to display
 * @param {'success'|'error'} type - Toast style
 */
function showToast(message, type) {
  // Remove any existing toast
  const existing = $toastContainer.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  $toastContainer.appendChild(toast);

  // Trigger reflow for CSS animation
  toast.offsetHeight; // eslint-disable-line no-unused-expressions

  toast.classList.add('toast-visible');

  setTimeout(() => {
    toast.classList.add('toast-fade-out');
    toast.addEventListener('animationend', () => toast.remove());
  }, 3000);
}

/**
 * Set the Save button to loading/idle state.
 * @param {boolean} loading
 */
function setSaving(loading) {
  $saveBtn.disabled = loading;
  setVisible($saveBtnLabel, !loading);
  setVisible($saveBtnSpinner, loading);
}

/**
 * Show or hide the title validation error.
 * @param {boolean} show
 */
function showTitleError(show) {
  setVisible($titleError, show);
  $titleInput.classList.toggle('input-error', show);
  if (show) {
    $titleInput.setAttribute('aria-invalid', 'true');
  } else {
    $titleInput.removeAttribute('aria-invalid');
  }
}

/**
 * Map a SemPKMError or generic error to a user-facing message.
 * @param {Error} err
 * @returns {string}
 */
function errorMessage(err) {
  if (err instanceof SemPKMError) {
    if (err.status === 401) return 'Invalid API key';
    if (err.status === 403) return 'API key lacks required permissions';
    return err.detail || `Server error (${err.status})`;
  }
  if (err instanceof TypeError) return 'Cannot reach SemPKM instance';
  return err.message || 'Unknown error';
}

/**
 * Populate the type <select> from an array of type objects.
 * Groups by model_name when available.
 *
 * @param {Array<{iri: string, label: string, model_name?: string}>} types
 * @param {string} [defaultIri] - IRI to pre-select
 */
function populateTypeSelector(types, defaultIri = '') {
  $typeSelect.innerHTML = '';

  // Group types by model_name
  const grouped = {};
  const ungrouped = [];

  for (const t of types) {
    if (t.model_name) {
      if (!grouped[t.model_name]) grouped[t.model_name] = [];
      grouped[t.model_name].push(t);
    } else {
      ungrouped.push(t);
    }
  }

  // Add blank first option
  const blank = document.createElement('option');
  blank.value = '';
  blank.textContent = '— Select type —';
  $typeSelect.appendChild(blank);

  // Add grouped options
  for (const [modelName, modelTypes] of Object.entries(grouped)) {
    const optgroup = document.createElement('optgroup');
    optgroup.label = modelName;
    for (const t of modelTypes) {
      const opt = document.createElement('option');
      opt.value = t.iri;
      opt.textContent = t.label || t.iri;
      optgroup.appendChild(opt);
    }
    $typeSelect.appendChild(optgroup);
  }

  // Add ungrouped options
  for (const t of ungrouped) {
    const opt = document.createElement('option');
    opt.value = t.iri;
    opt.textContent = t.label || t.iri;
    $typeSelect.appendChild(opt);
  }

  // Pre-select default type
  if (defaultIri) {
    $typeSelect.value = defaultIri;
  }
}

/* ── Core flows ────────────────────────────────────────────────── */

/**
 * Initialize the popup: load settings, check connection, populate form.
 */
async function init() {
  const settings = await getSettings();

  // No credentials → show unconfigured state
  if (!settings.instanceUrl || !settings.apiKey) {
    setVisible($unconfigured, true);
    setVisible($captureForm, false);
    setConnectionDot('error', 'Not configured');
    console.log('[SemPKM] Popup: no settings configured');
    return;
  }

  // Show the form, hide unconfigured
  setVisible($unconfigured, false);
  setVisible($captureForm, true);
  setConnectionDot('loading');

  client = new SemPKMClient(settings.instanceUrl, settings.apiKey);

  // Populate types
  try {
    const types = await client.getTypes();
    populateTypeSelector(types, settings.defaultType);
    setConnectionDot('connected', `Connected — ${types.length} types available`);
    console.log(`[SemPKM] Loaded ${types.length} types`);
  } catch (err) {
    const msg = errorMessage(err);
    setConnectionDot('error', msg);
    $typeSelect.innerHTML = '<option value="">— Connection failed —</option>';
    console.warn('[SemPKM] Failed to load types:', msg, err);
  }

  // Auto-fill URL from active tab
  try {
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
    if (tab && tab.url) {
      $urlInput.value = tab.url;
    }
    // Auto-fill title from page title if setting enabled
    if (settings.autoFillTitle && tab && tab.title) {
      $titleInput.value = tab.title;
    }
  } catch (tabErr) {
    console.warn('[SemPKM] Could not get active tab:', tabErr);
  }
}

/**
 * Handle save button click: validate, create object, show feedback.
 * @param {Event} e
 */
async function handleSave(e) {
  e.preventDefault();

  // Validate title
  const title = $titleInput.value.trim();
  if (!title) {
    showTitleError(true);
    $titleInput.focus();
    return;
  }
  showTitleError(false);

  // Gather form data
  const typeIri = $typeSelect.value;
  if (!typeIri) {
    showToast('Please select a type', 'error');
    $typeSelect.focus();
    return;
  }

  const body = $bodyInput.value.trim();
  const url = $urlInput.value.trim();

  // Build properties
  const properties = {
    'dcterms:title': title,
  };
  if (body) {
    properties['sempkm:body'] = body;
  }
  if (url) {
    properties['schema:url'] = url;
  }

  // Call API
  setSaving(true);

  try {
    const result = await client.createObject({
      type: typeIri,
      properties,
    });

    const createdIri = result.results?.[0]?.iri || 'unknown';
    showToast('✓ Object created!', 'success');
    console.log(`[SemPKM] Object created: ${createdIri}`);

    // Briefly disable to prevent double-submit, then close or reset
    setTimeout(() => {
      setSaving(false);
      // Clear form for next capture
      $titleInput.value = '';
      $bodyInput.value = '';
    }, 1500);
  } catch (err) {
    const msg = errorMessage(err);
    showToast(msg, 'error');
    console.warn(`[SemPKM] Save failed: ${msg}`, err);
    setSaving(false);
  }
}

/**
 * Populate form fields from page data.
 * Called by content script messaging (S03) or manually.
 *
 * @param {Object} data
 * @param {string} [data.title] - Page title
 * @param {string} [data.url] - Page URL
 * @param {string} [data.selectedText] - Selected text from page
 * @param {string} [data.author] - Page author if available
 */
export function populateFromPageData(data) {
  if (data.title && $titleInput) {
    $titleInput.value = data.title;
  }
  if (data.url && $urlInput) {
    $urlInput.value = data.url;
  }
  if (data.selectedText && $bodyInput) {
    $bodyInput.value = data.selectedText;
  }
  // author could populate a future field; for now, log it
  if (data.author) {
    console.log(`[SemPKM] Page author: ${data.author}`);
  }
}

/* ── Event binding ─────────────────────────────────────────────── */

// Open settings page
$openSettings.addEventListener('click', () => {
  chrome.runtime.openOptionsPage();
});

// Form submission
$captureForm.addEventListener('submit', handleSave);

// Clear title error on input
$titleInput.addEventListener('input', () => {
  if ($titleInput.value.trim()) {
    showTitleError(false);
  }
});

/* ── Init ──────────────────────────────────────────────────────── */
init();
console.log('[SemPKM] Popup loaded');
