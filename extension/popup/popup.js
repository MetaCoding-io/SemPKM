/**
 * SemPKM Capture — popup logic.
 *
 * Handles the complete capture flow: load settings → check connection →
 * populate type selector → fetch SHACL shape → render dynamic form →
 * gather form data → create object → show feedback.
 *
 * @module popup/popup
 */

import { SemPKMClient, SemPKMError } from '../shared/api-client.js';
import { getSettings } from '../shared/storage.js';
import { renderForm, getFormValues } from '../shared/shacl-renderer.js';
import { suggestType, mapSchemaOrgToFormValues } from '../shared/schema-mapper.js';
import { extractPageData } from '../content/extractor.js';
import { initReferencePickers, initSinglePicker, getSelectedReferences } from '../shared/reference-picker.js';

/* ── DOM references ────────────────────────────────────────────── */
const $connectionDot   = document.getElementById('connection-dot');
const $unconfigured    = document.getElementById('unconfigured-state');
const $openSettings    = document.getElementById('open-settings');
const $captureForm     = document.getElementById('capture-form');
const $typeSelect      = document.getElementById('type-select');
const $typeIcon        = document.getElementById('selected-type-icon');
const $dynamicForm     = document.getElementById('dynamic-form');
const $formLoading     = document.getElementById('form-loading');
const $formFallback    = document.getElementById('form-fallback');
const $fallbackTitle   = document.getElementById('fallback-title-input');
const $titleError      = document.getElementById('title-error');
const $notesInput      = document.getElementById('body-input');
const $urlInput        = document.getElementById('url-input');
const $saveBtn         = document.getElementById('save-btn');
const $saveBtnLabel    = document.querySelector('#save-btn .btn-label');
const $saveBtnSpinner  = document.querySelector('#save-btn .btn-spinner');
const $toastContainer  = document.getElementById('toast-container');

/** Active SemPKMClient instance (null until configured). */
let client = null;

/** Full type objects from getTypes(), including icon and icon_color. */
let loadedTypes = [];

/** Currently loaded shape response (null when in fallback mode). */
let currentShape = null;

/** Pending page data from content script extraction or context menu. */
let pendingPageData = null;

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
  const existing = $toastContainer.querySelector('.toast');
  if (existing) existing.remove();

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  $toastContainer.appendChild(toast);

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
  if ($fallbackTitle) {
    $fallbackTitle.classList.toggle('input-error', show);
    if (show) {
      $fallbackTitle.setAttribute('aria-invalid', 'true');
    } else {
      $fallbackTitle.removeAttribute('aria-invalid');
    }
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

/* ── Type selector & icon ──────────────────────────────────────── */

/**
 * Populate the type <select> from an array of type objects.
 * Groups by model_name when available. Stores full type data in loadedTypes.
 *
 * @param {Array<{iri: string, label: string, icon?: string, icon_color?: string, model_name?: string}>} types
 * @param {string} [defaultIri] - IRI to pre-select
 */
function populateTypeSelector(types, defaultIri = '') {
  loadedTypes = types;
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

/**
 * Update the type icon indicator next to the select.
 * Shows a colored dot using the type's icon_color, or hides if no type selected.
 * @param {string} typeIri
 */
function updateTypeIcon(typeIri) {
  if (!typeIri) {
    setVisible($typeIcon, false);
    return;
  }
  const typeInfo = loadedTypes.find((t) => t.iri === typeIri);
  if (typeInfo && typeInfo.icon_color) {
    $typeIcon.style.background = typeInfo.icon_color;
    $typeIcon.title = typeInfo.icon || typeInfo.label || '';
    setVisible($typeIcon, true);
  } else if (typeInfo && typeInfo.icon) {
    $typeIcon.style.background = '#4f46e5';
    $typeIcon.title = typeInfo.icon;
    setVisible($typeIcon, true);
  } else {
    setVisible($typeIcon, false);
  }
}

/* ── Shape loading & form rendering ────────────────────────────── */

/**
 * Handle type selector change: fetch shape and render dynamic form.
 */
async function handleTypeChange() {
  const typeIri = $typeSelect.value;

  updateTypeIcon(typeIri);

  // No type selected — show fallback
  if (!typeIri) {
    $dynamicForm.innerHTML = '';
    currentShape = null;
    setVisible($formLoading, false);
    setVisible($formFallback, true);
    return;
  }

  // Show loading, hide fallback
  setVisible($formLoading, true);
  setVisible($formFallback, false);
  $dynamicForm.innerHTML = '';

  try {
    const shape = await client.getShape(typeIri);
    currentShape = shape;

    const fragment = renderForm(shape);
    $dynamicForm.appendChild(fragment);
    initReferencePickers($dynamicForm, client);

    const propCount = (shape.properties || []).length;
    const groupCount = (shape.groups || []).length;
    console.log(`[SemPKM] Shape loaded for ${typeIri}: ${propCount} properties, ${groupCount} groups`);
  } catch (err) {
    const msg = errorMessage(err);
    showToast(`Failed to load form: ${msg}`, 'error');
    console.warn('[SemPKM] Shape fetch failed:', msg, err);

    // Fall back to simple title input
    currentShape = null;
    setVisible($formFallback, true);
  }

  setVisible($formLoading, false);

  // Apply schema.org data to the newly rendered form
  applySchemaOrgToForm();
}

/* ── Schema.org form filling ───────────────────────────────────── */

/**
 * Apply schema.org data from pendingPageData to the current dynamic form.
 * Called at the end of handleTypeChange() so it re-applies when the user
 * switches types.
 */
function applySchemaOrgToForm() {
  if (!pendingPageData || !currentShape) return;

  const schemaEntities = pendingPageData.schemaOrg;
  if (!Array.isArray(schemaEntities) || schemaEntities.length === 0) return;

  // Find the best matching entity for the current type
  const suggestion = suggestType(schemaEntities, loadedTypes);
  const entity = suggestion ? suggestion.schemaEntity : schemaEntities[0];

  const mapped = mapSchemaOrgToFormValues(entity, currentShape.properties);

  // Also map basic page data to common form paths
  if (pendingPageData.title) {
    const titlePath = 'http://purl.org/dc/terms/title';
    if (!(titlePath in mapped)) {
      const hasPath = currentShape.properties.some((p) => p.path === titlePath);
      if (hasPath) mapped[titlePath] = pendingPageData.title;
    }
  }
  if (pendingPageData.url) {
    const urlPath = 'https://schema.org/url';
    if (!(urlPath in mapped)) {
      const hasPath = currentShape.properties.some((p) => p.path === urlPath);
      if (hasPath) mapped[urlPath] = pendingPageData.url;
    }
  }

  let applied = 0;
  for (const [path, value] of Object.entries(mapped)) {
    const input = $dynamicForm.querySelector(`[data-path="${path}"]`);
    if (input && !input.value) {
      input.value = value;
      applied++;
    }
  }

  if (applied > 0) {
    console.log(`[SemPKM] Applied ${applied} schema.org values to form`);
  }
}

/* ── Title extraction ──────────────────────────────────────────── */

/**
 * Find the title value from dynamic form properties.
 * Checks property paths in priority order:
 *   1. Path containing "title" (e.g. dcterms:title)
 *   2. Path ending with "Name" or "name" (e.g. dealName, firstName)
 *   3. First required (min_count > 0) string property from the shape
 *
 * @param {Object} properties - {path: value} from getFormValues()
 * @returns {string|null}
 */
function extractTitle(properties) {
  // Priority 1: explicit "title" in path
  for (const [path, value] of Object.entries(properties)) {
    if (path.toLowerCase().includes('title')) {
      const str = Array.isArray(value) ? value.find((v) => v && v.trim()) : value;
      if (str && str.trim()) return str.trim();
    }
  }

  // Priority 2: path ending in "name" or "Name" (dealName, firstName, etc.)
  for (const [path, value] of Object.entries(properties)) {
    const segment = path.split('/').pop().split(':').pop();
    if (segment && segment.toLowerCase().includes('name')) {
      const str = Array.isArray(value) ? value.find((v) => v && v.trim()) : value;
      if (str && str.trim()) return str.trim();
    }
  }

  // Priority 3: any non-empty required field from the shape
  if (currentShape) {
    for (const prop of currentShape.properties) {
      if (prop.min_count > 0 && properties[prop.path]) {
        const val = properties[prop.path];
        const str = Array.isArray(val) ? val.find((v) => v && v.trim()) : val;
        if (str && str.trim()) return str.trim();
      }
    }
  }

  // Priority 4: any non-empty value at all
  for (const value of Object.values(properties)) {
    const str = Array.isArray(value) ? value.find((v) => v && v.trim()) : value;
    if (str && str.trim()) return str.trim();
  }

  return null;
}

/* ── Core flows ────────────────────────────────────────────────── */

/**
 * Initialize the popup: load settings, check connection, populate form,
 * extract page data via content script, and apply schema.org suggestions.
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

  // ── Extract page data (context menu or content script) ────────

  try {
    // Check for context menu pre-fill data first
    const stored = await chrome.storage.session.get('contextMenuData');
    if (stored && stored.contextMenuData) {
      const cm = stored.contextMenuData;
      await chrome.storage.session.remove('contextMenuData');

      pendingPageData = {
        title: cm.pageTitle || null,
        url: cm.pageUrl || '',
        selectedText: cm.selectionText || '',
        author: null,
        description: null,
        schemaOrg: [],
      };
      console.log('[SemPKM] Extracted page data (context menu):', {
        title: pendingPageData.title,
        url: pendingPageData.url,
        selectedText: pendingPageData.selectedText.length,
        schemaOrg: 0,
      });
    } else {
      // Inject content script to extract rich page data
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      if (tab && tab.id) {
        try {
          const results = await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            func: extractPageData,
          });
          if (results && results[0] && results[0].result) {
            pendingPageData = results[0].result;
            console.log('[SemPKM] Extracted page data:', {
              title: pendingPageData.title,
              url: pendingPageData.url,
              selectedText: (pendingPageData.selectedText || '').length,
              schemaOrg: (pendingPageData.schemaOrg || []).length,
            });
          }
        } catch (injectionErr) {
          console.warn('[SemPKM] Content script injection failed:', injectionErr.message, '— falling back to tab data');
          // Graceful fallback to tab-level data
          pendingPageData = {
            title: tab.title || null,
            url: tab.url || '',
            selectedText: '',
            author: null,
            description: null,
            schemaOrg: [],
          };
        }
      }
    }
  } catch (extractErr) {
    console.warn('[SemPKM] Page data extraction failed:', extractErr);
  }

  // ── Apply basic fields from extracted data ────────────────────

  if (pendingPageData) {
    if (settings.autoFillTitle && pendingPageData.title && $fallbackTitle) {
      $fallbackTitle.value = pendingPageData.title;
    }
    if (settings.autoFillUrl && pendingPageData.url && $urlInput) {
      $urlInput.value = pendingPageData.url;
    }
    if (settings.includeSelection && pendingPageData.selectedText && $notesInput) {
      $notesInput.value = pendingPageData.selectedText;
    }
  }

  // ── Populate types and apply schema.org suggestion ────────────

  try {
    const types = await client.getTypes();
    populateTypeSelector(types, settings.defaultType);
    setConnectionDot('connected', `Connected — ${types.length} types available`);
    console.log(`[SemPKM] Loaded ${types.length} types`);

    // Schema.org type suggestion — auto-select if a match exists
    let typeAutoSelected = false;
    if (pendingPageData && pendingPageData.schemaOrg && pendingPageData.schemaOrg.length > 0) {
      const suggestion = suggestType(pendingPageData.schemaOrg, loadedTypes);
      if (suggestion) {
        // Check that the suggested type exists as an option in the selector
        const optionExists = Array.from($typeSelect.options).some((o) => o.value === suggestion.typeIri);
        if (optionExists) {
          $typeSelect.value = suggestion.typeIri;
          const schemaType = suggestion.schemaEntity['@type'] || 'unknown';
          console.log(`[SemPKM] Schema.org type suggestion: ${schemaType} → ${suggestion.typeIri}`);
          typeAutoSelected = true;
        }
      }
    }

    // Render the form for the selected type (auto-suggested or default)
    if (typeAutoSelected || (settings.defaultType && $typeSelect.value === settings.defaultType)) {
      await handleTypeChange();
    } else {
      // No default — show fallback title input
      setVisible($formFallback, true);
    }
  } catch (err) {
    const msg = errorMessage(err);
    setConnectionDot('error', msg);
    $typeSelect.innerHTML = '<option value="">— Connection failed —</option>';
    console.warn('[SemPKM] Failed to load types:', msg, err);
    // Show fallback so user can still attempt a save after reconnecting
    setVisible($formFallback, true);
  }
}

/**
 * Handle save button click: validate, create object, show feedback.
 * @param {Event} e
 */
async function handleSave(e) {
  e.preventDefault();

  // Validate type selection
  const typeIri = $typeSelect.value;
  if (!typeIri) {
    showToast('Please select a type', 'error');
    $typeSelect.focus();
    return;
  }

  let properties;
  let title;

  if (currentShape) {
    // ── Dynamic form mode ──
    properties = getFormValues($dynamicForm);

    // Find title from shape properties
    title = extractTitle(properties);
    if (!title) {
      showToast('At least one identifying field is required', 'error');
      // Try to focus the first required input in the dynamic form
      const firstRequired = $dynamicForm.querySelector('.form-field.required input, .form-field.required select');
      if (firstRequired) firstRequired.focus();
      return;
    }
  } else {
    // ── Fallback mode ──
    title = $fallbackTitle.value.trim();
    if (!title) {
      showTitleError(true);
      $fallbackTitle.focus();
      return;
    }
    showTitleError(false);
    properties = {
      'dcterms:title': title,
    };
  }

  // Append body (notes) if present
  const body = $notesInput.value.trim();
  if (body) {
    properties['sempkm:body'] = body;
  }

  // Append URL if present
  const url = $urlInput.value.trim();
  if (url) {
    properties['schema:url'] = url;
  }

  console.log(`[SemPKM] Saving object — type: ${typeIri}, properties:`, Object.keys(properties));

  // Call API
  setSaving(true);

  try {
    const result = await client.createObject({
      type: typeIri,
      properties,
    });

    const createdIri = result.results?.[0]?.iri || null;
    console.log(`[SemPKM] Object created: ${createdIri || 'unknown'}`);

    // ── Two-step save: create edges for selected references ────
    const refs = getSelectedReferences($dynamicForm);
    let edgeFails = 0;

    if (refs.length > 0 && createdIri) {
      for (const ref of refs) {
        try {
          await client.createEdge({
            source: createdIri,
            target: ref.targetIri,
            predicate: ref.path,
          });
          console.log(`[SemPKM] Edge created: ${createdIri} → ${ref.path} → ${ref.targetIri}`);
        } catch (edgeErr) {
          edgeFails++;
          console.warn(`[SemPKM] Edge creation failed: ${ref.path} → ${ref.targetIri}`, edgeErr);
        }
      }
    }

    if (edgeFails > 0) {
      showToast(`✓ Object created, but ${edgeFails} relationship(s) failed to save`, 'error');
    } else {
      showToast('✓ Object created!', 'success');
    }

    // Reset form after brief delay
    setTimeout(() => {
      setSaving(false);
      // Clear dynamic form inputs (re-render to reset defaults)
      if (currentShape) {
        $dynamicForm.innerHTML = '';
        const fragment = renderForm(currentShape);
        $dynamicForm.appendChild(fragment);
        initReferencePickers($dynamicForm, client);
      } else {
        $fallbackTitle.value = '';
      }
      $notesInput.value = '';
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
  if (data.title && $fallbackTitle) {
    $fallbackTitle.value = data.title;
  }
  if (data.url && $urlInput) {
    $urlInput.value = data.url;
  }
  if (data.selectedText && $notesInput) {
    $notesInput.value = data.selectedText;
  }
  if (data.author) {
    console.log(`[SemPKM] Page author: ${data.author}`);
  }
}

/* ── Event binding ─────────────────────────────────────────────── */

// Open settings page
$openSettings.addEventListener('click', () => {
  chrome.runtime.openOptionsPage();
});

// Type selector change → fetch shape → render form
$typeSelect.addEventListener('change', handleTypeChange);

// Form submission
$captureForm.addEventListener('submit', handleSave);

// Clear title error on fallback title input
$fallbackTitle.addEventListener('input', () => {
  if ($fallbackTitle.value.trim()) {
    showTitleError(false);
  }
});

// Initialize reference pickers on dynamically added multi-value reference fields
$dynamicForm.addEventListener('sempkm:reference-field-added', (e) => {
  if (e.detail?.element && client) {
    initSinglePicker(e.detail.element, client);
  }
});

/* ── Init ──────────────────────────────────────────────────────── */
init();
console.log('[SemPKM] Popup loaded');
