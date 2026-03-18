/**
 * Reference Picker — search-as-you-type for object reference fields.
 *
 * Enhances `.reference-field` elements (produced by shacl-renderer.js)
 * with debounced search, suggestion dropdown, selection management,
 * and clear functionality.
 *
 * Chrome MV3 CSP compliant: zero inline event handlers.
 *
 * @module shared/reference-picker
 */

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const DEBOUNCE_MS = 300;
const MIN_QUERY_LENGTH = 2;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/**
 * Extract a human-readable type name from a target class IRI or placeholder.
 * @param {HTMLElement} wrapper - The .reference-field element
 * @returns {string}
 */
function extractTypeName(wrapper) {
  const searchInput = wrapper.querySelector('.reference-search');
  if (searchInput && searchInput.placeholder) {
    // "Search Company..." → "Company"
    const match = searchInput.placeholder.match(/^Search\s+(.+?)\.{0,3}$/);
    if (match) return match[1];
  }
  const targetClass = wrapper.dataset.targetClass || '';
  // "urn:sempkm:model:crm:Company" → "Company"
  const localName = targetClass.split(/[:#/]/).pop();
  return localName || 'item';
}

/**
 * Create a DOM element with attributes and children.
 * @param {string} tag
 * @param {Object} attrs
 * @param {Array} children
 * @returns {HTMLElement}
 */
function el(tag, attrs = {}, children = []) {
  const elem = document.createElement(tag);
  for (const [key, val] of Object.entries(attrs)) {
    if (key === 'className') {
      elem.className = val;
    } else if (key === 'textContent') {
      elem.textContent = val;
    } else if (val !== null && val !== undefined && val !== false) {
      elem.setAttribute(key, val);
    }
  }
  for (const child of children) {
    if (typeof child === 'string') {
      elem.appendChild(document.createTextNode(child));
    } else if (child) {
      elem.appendChild(child);
    }
  }
  return elem;
}

// ---------------------------------------------------------------------------
// initSinglePicker
// ---------------------------------------------------------------------------

/**
 * Initialize a single .reference-field element with search-as-you-type.
 * @param {HTMLElement} wrapper - A .reference-field DOM element
 * @param {Object} client - SemPKMClient instance with searchObjects(query)
 */
export function initSinglePicker(wrapper, client) {
  const searchInput = wrapper.querySelector('.reference-search');
  const hiddenInput = wrapper.querySelector('input[type="hidden"][data-path]');
  if (!searchInput || !hiddenInput) {
    console.warn('[SemPKM] Reference picker: missing inputs in', wrapper);
    return;
  }

  const targetClass = wrapper.dataset.targetClass || null;
  const typeName = extractTypeName(wrapper);

  // Create dropdown container
  const dropdown = el('div', { className: 'suggestions-dropdown' });
  dropdown.style.display = 'none';
  wrapper.appendChild(dropdown);

  // State
  let debounceTimer = null;
  let latestQuery = '';

  // ── Search & render ──────────────────────────────────────────
  function showDropdown(content) {
    dropdown.innerHTML = '';
    if (typeof content === 'string') {
      dropdown.appendChild(el('div', { className: 'suggestions-empty', textContent: content }));
    } else {
      dropdown.appendChild(content);
    }
    dropdown.style.display = '';
  }

  function hideDropdown() {
    dropdown.style.display = 'none';
    dropdown.innerHTML = '';
  }

  async function performSearch(query) {
    latestQuery = query;

    // Show loading
    dropdown.innerHTML = '';
    dropdown.appendChild(
      el('div', { className: 'suggestions-loading', textContent: 'Searching…' })
    );
    dropdown.style.display = '';

    let results;
    try {
      results = await client.searchObjects(query);
    } catch (err) {
      console.error('[SemPKM] Reference search failed:', err);
      if (latestQuery !== query) return; // stale
      showDropdown('Search failed');
      return;
    }

    // Stale guard — query may have changed while awaiting
    if (latestQuery !== query) return;

    // Client-side type filtering
    let filtered = results;
    if (targetClass) {
      filtered = results.filter((r) => r.type_iri === targetClass);
    }

    console.log(
      `[SemPKM] Search: "${query}" → ${results.length} results (${filtered.length} after type filter)`
    );

    if (filtered.length === 0) {
      showDropdown(`No matching ${typeName} found`);
      return;
    }

    // Render suggestion items
    const list = document.createDocumentFragment();
    for (const item of filtered) {
      const row = el('div', { className: 'suggestion-item' }, [
        el('span', { className: 'suggestion-label', textContent: item.label }),
        el('span', { className: 'suggestion-type', textContent: item.type_label || '' }),
      ]);
      row.addEventListener('click', () => selectItem(item));
      list.appendChild(row);
    }
    dropdown.innerHTML = '';
    dropdown.appendChild(list);
    dropdown.style.display = '';
  }

  // ── Selection ────────────────────────────────────────────────
  function selectItem(item) {
    hiddenInput.value = item.iri;
    searchInput.value = item.label;
    searchInput.readOnly = true;
    wrapper.classList.add('has-selection');
    hideDropdown();

    // Remove any existing clear button before adding a new one
    const existingClear = wrapper.querySelector('.clear-selection');
    if (existingClear) existingClear.remove();

    const clearBtn = el('button', {
      type: 'button',
      className: 'clear-selection',
      textContent: '×',
    });
    clearBtn.addEventListener('click', clearSelection);
    wrapper.appendChild(clearBtn);

    console.log(`[SemPKM] Reference selected: ${item.label} (${item.iri})`);
  }

  function clearSelection() {
    hiddenInput.value = '';
    searchInput.value = '';
    searchInput.readOnly = false;
    wrapper.classList.remove('has-selection');
    const clearBtn = wrapper.querySelector('.clear-selection');
    if (clearBtn) clearBtn.remove();
    searchInput.focus();
  }

  // ── Input listener with debounce ─────────────────────────────
  searchInput.addEventListener('input', () => {
    clearTimeout(debounceTimer);
    const query = searchInput.value.trim();

    if (query.length < MIN_QUERY_LENGTH) {
      hideDropdown();
      latestQuery = '';
      return;
    }

    debounceTimer = setTimeout(() => performSearch(query), DEBOUNCE_MS);
  });

  // Close dropdown when clicking outside
  document.addEventListener('click', (e) => {
    if (!wrapper.contains(e.target)) {
      hideDropdown();
    }
  });
}

// ---------------------------------------------------------------------------
// getSelectedReferences
// ---------------------------------------------------------------------------

/**
 * Collect all selected references from .reference-field elements in a container.
 * @param {HTMLElement} container - Parent element to search within
 * @returns {Array<{path: string, targetIri: string}>}
 */
export function getSelectedReferences(container) {
  const refs = [];
  const fields = container.querySelectorAll('.reference-field');
  for (const field of fields) {
    const hidden = field.querySelector('input[type="hidden"][data-path]');
    if (hidden && hidden.value) {
      refs.push({
        path: hidden.dataset.path,
        targetIri: hidden.value,
      });
    }
  }
  return refs;
}

// ---------------------------------------------------------------------------
// initReferencePickers
// ---------------------------------------------------------------------------

/**
 * Initialize all .reference-field elements within a container.
 * @param {HTMLElement} container - Parent element to search within
 * @param {Object} client - SemPKMClient instance
 */
export function initReferencePickers(container, client) {
  const fields = container.querySelectorAll('.reference-field');
  for (const field of fields) {
    initSinglePicker(field, client);
  }
  console.log(`[SemPKM] Reference picker initialized: ${fields.length} fields`);
}
