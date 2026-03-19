/**
 * SemPKM Capture — options page logic.
 *
 * Loads saved settings on page open, tests connections against the
 * backend's /.well-known/sempkm endpoint, populates the type selector
 * from /api/types, and persists everything to chrome.storage.sync.
 *
 * @module options/options
 */

import { SemPKMClient, SemPKMError } from '../shared/api-client.js';
import { getSettings, saveSettings } from '../shared/storage.js';

/* ── DOM references ────────────────────────────────────────────── */
const $instanceUrl    = document.getElementById('instance-url');
const $apiKey         = document.getElementById('api-key');
const $testBtn        = document.getElementById('test-connection');
const $testLabel      = document.querySelector('#test-connection .btn-label');
const $testSpinner    = document.querySelector('#test-connection .btn-spinner');
const $statusBox      = document.getElementById('connection-status');
const $statusIcon     = document.querySelector('#connection-status .status-icon');
const $statusMessage  = document.querySelector('#connection-status .status-message');
const $defaultType    = document.getElementById('default-type');
const $autoFillTitle  = document.getElementById('auto-fill-title');
const $autoFillUrl    = document.getElementById('auto-fill-url');
const $includeSelect  = document.getElementById('include-selection');
const $autoCheckCtx   = document.getElementById('auto-check-context');
const $ctxCheckDelay  = document.getElementById('context-check-delay');
const $ctxTimeout     = document.getElementById('context-timeout');
const $saveBtn        = document.getElementById('save-settings');
const $saveConfirm    = document.getElementById('save-confirmation');
const $toggleKeyBtn   = document.getElementById('toggle-key-visibility');

/* ── Helpers ───────────────────────────────────────────────────── */

/** Show/hide an element via the `hidden` class. */
function setVisible(el, visible) {
  el.classList.toggle('hidden', !visible);
}

/** Show connection status (green/red). */
function showStatus(success, message) {
  setVisible($statusBox, true);
  $statusBox.classList.toggle('status-success', success);
  $statusBox.classList.toggle('status-error', !success);
  $statusIcon.textContent = success ? '✅' : '❌';
  $statusMessage.textContent = message;
}

/** Hide connection status. */
function hideStatus() {
  setVisible($statusBox, false);
}

/** Set the Test Connection button to loading state. */
function setTesting(testing) {
  $testBtn.disabled = testing;
  setVisible($testLabel, !testing);
  setVisible($testSpinner, testing);
}

/** Flash the "Settings saved ✓" confirmation. */
function flashSaveConfirmation() {
  setVisible($saveConfirm, true);
  $saveConfirm.classList.add('fade-in');
  setTimeout(() => {
    $saveConfirm.classList.remove('fade-in');
    $saveConfirm.classList.add('fade-out');
    setTimeout(() => {
      setVisible($saveConfirm, false);
      $saveConfirm.classList.remove('fade-out');
    }, 400);
  }, 2000);
}

/**
 * Populate the default-type `<select>` from an array of type objects.
 * Preserves the previously selected value if it still exists.
 *
 * @param {Array<{iri: string, label: string}>} types
 * @param {string} [selectedIri] - IRI to pre-select
 */
function populateTypeSelector(types, selectedIri = '') {
  // Clear existing options
  $defaultType.innerHTML = '';

  // Add a blank option
  const blank = document.createElement('option');
  blank.value = '';
  blank.textContent = '— Select a default type —';
  $defaultType.appendChild(blank);

  for (const t of types) {
    const opt = document.createElement('option');
    opt.value = t.iri;
    opt.textContent = t.label || t.iri;
    $defaultType.appendChild(opt);
  }

  // Restore selection
  if (selectedIri) {
    $defaultType.value = selectedIri;
  }

  $defaultType.disabled = false;
}

/** Disable the type selector and show placeholder text. */
function disableTypeSelector() {
  $defaultType.innerHTML = '<option value="">— Connect to load types —</option>';
  $defaultType.disabled = true;
}

/**
 * Map an error to a human-readable connection failure message.
 * @param {Error} err
 * @returns {string}
 */
function connectionErrorMessage(err) {
  if (err instanceof SemPKMError) {
    if (err.status === 401) return 'Invalid API key';
    if (err.status === 403) return 'API key lacks required permissions';
    return err.detail || `Server error (${err.status})`;
  }
  // Network errors — fetch throws TypeError for connection refused
  if (err instanceof TypeError) return 'Cannot reach instance';
  return err.message || 'Connection failed';
}

/* ── Core actions ──────────────────────────────────────────────── */

/**
 * Test connection using current form values.
 * On success, populates the type selector.
 */
async function testConnection() {
  const instanceUrl = $instanceUrl.value.trim();
  const apiKey = $apiKey.value.trim();

  if (!instanceUrl) {
    showStatus(false, 'Enter an instance URL first');
    return;
  }
  if (!apiKey) {
    showStatus(false, 'Enter an API key first');
    return;
  }

  setTesting(true);
  hideStatus();

  try {
    const client = new SemPKMClient(instanceUrl, apiKey);
    const info = await client.connect();
    const version = info.version || 'unknown';
    showStatus(true, `Connected — SemPKM v${version}`);
    console.log('[SemPKM] Connection test passed:', { version, endpoints: info.endpoints });

    // Fetch and populate types
    try {
      const types = await client.getTypes();
      const savedType = $defaultType.dataset.savedValue || '';
      populateTypeSelector(types, savedType);
      console.log(`[SemPKM] Loaded ${types.length} types`);
    } catch (typesErr) {
      console.warn('[SemPKM] Connected but failed to load types:', typesErr);
      // Connection succeeded — don't overwrite the green status, just warn
      disableTypeSelector();
    }
  } catch (err) {
    const msg = connectionErrorMessage(err);
    showStatus(false, msg);
    disableTypeSelector();
    console.warn('[SemPKM] Connection test failed:', msg, err);
  } finally {
    setTesting(false);
  }
}

/** Gather form values and persist to storage. */
async function saveCurrentSettings() {
  const settings = {
    instanceUrl: $instanceUrl.value.trim(),
    apiKey: $apiKey.value.trim(),
    defaultType: $defaultType.value,
    autoFillTitle: $autoFillTitle.checked,
    autoFillUrl: $autoFillUrl.checked,
    includeSelection: $includeSelect.checked,
    autoCheckContext: $autoCheckCtx.checked,
    contextCheckDelay: parseInt($ctxCheckDelay.value, 10) || 2000,
    contextTimeout: parseInt($ctxTimeout.value, 10) || 5000,
  };

  await saveSettings(settings);
  flashSaveConfirmation();
  console.log('[SemPKM] Settings saved');
}

/** Load persisted settings and populate form fields. */
async function loadSettings() {
  const settings = await getSettings();

  $instanceUrl.value = settings.instanceUrl || '';
  $apiKey.value = settings.apiKey || '';
  $autoFillTitle.checked = settings.autoFillTitle !== false;
  $autoFillUrl.checked = settings.autoFillUrl !== false;
  $includeSelect.checked = settings.includeSelection !== false;

  // Context overlay settings
  $autoCheckCtx.checked = settings.autoCheckContext !== false;
  $ctxCheckDelay.value = settings.contextCheckDelay || 2000;
  $ctxTimeout.value = settings.contextTimeout || 5000;

  // Stash the saved default type so populateTypeSelector can restore it
  $defaultType.dataset.savedValue = settings.defaultType || '';

  // Auto-test connection if both URL and key are present
  if (settings.instanceUrl && settings.apiKey) {
    testConnection();
  }
}

/* ── Event binding ─────────────────────────────────────────────── */

$testBtn.addEventListener('click', testConnection);
$saveBtn.addEventListener('click', saveCurrentSettings);

// Toggle API key visibility
$toggleKeyBtn.addEventListener('click', () => {
  const showing = $apiKey.type === 'text';
  $apiKey.type = showing ? 'password' : 'text';
  $toggleKeyBtn.querySelector('.icon-eye').classList.toggle('hidden', !showing);
  $toggleKeyBtn.querySelector('.icon-eye-off').classList.toggle('hidden', showing);
});

// Keyboard shortcut: Enter in URL or key field triggers test
$instanceUrl.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') testConnection();
});
$apiKey.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') testConnection();
});

/* ── Init ──────────────────────────────────────────────────────── */
loadSettings();
console.log('[SemPKM] Options page loaded');
