/**
 * SHACL Form Renderer — converts SHACL shape JSON into HTML form elements.
 *
 * Consumes the JSON response from GET /api/shapes/{type_iri} and produces
 * a DocumentFragment of form fields via imperative DOM manipulation.
 * Chrome MV3 CSP compliant: addEventListener() only, no inline handlers.
 *
 * @module shared/shacl-renderer
 */

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const SKIP_PATHS = new Set([
  'http://purl.org/dc/terms/created',
  'http://purl.org/dc/terms/modified',
]);

const XSD = 'http://www.w3.org/2001/XMLSchema#';

// ---------------------------------------------------------------------------
// Property classification helpers
// ---------------------------------------------------------------------------

/**
 * Returns true if the property represents the body/content field.
 * @param {Object} prop - PropertyShapeInfo object
 * @returns {boolean}
 */
function isBodyProperty(prop) {
  return !!(prop.name && prop.name.toLowerCase() === 'body');
}

/**
 * Returns true if the property represents a tags/keywords field.
 * @param {Object} prop
 * @returns {boolean}
 */
function isTagProperty(prop) {
  return prop.path.includes('tags') || prop.path.includes('keywords');
}

/**
 * Returns true if the property allows multiple values.
 * @param {Object} prop
 * @returns {boolean}
 */
function isMultiValue(prop) {
  return prop.max_count === null || prop.max_count === undefined || prop.max_count > 1;
}

// ---------------------------------------------------------------------------
// DOM helpers
// ---------------------------------------------------------------------------

function el(tag, attrs = {}, children = []) {
  const elem = document.createElement(tag);
  for (const [key, val] of Object.entries(attrs)) {
    if (key === 'className') {
      elem.className = val;
    } else if (key === 'textContent') {
      elem.textContent = val;
    } else if (key === 'required' && val) {
      elem.required = true;
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
// Input creation (matches _render_input macro dispatch order exactly)
// ---------------------------------------------------------------------------

/**
 * Create the raw input element for a property (without label/wrapper).
 * @param {Object} prop - PropertyShapeInfo
 * @returns {HTMLElement} The input/select element
 */
function createInput(prop) {
  const isRequired = prop.min_count > 0;
  const hasDefault = prop.default_value !== null && prop.default_value !== undefined && prop.default_value !== '';
  const defaultClass = hasDefault ? 'default-value' : '';

  // 1. Enum (sh:in constraint)
  if (prop.in_values && prop.in_values.length > 0) {
    const select = el('select', {
      'data-path': prop.path,
      className: `form-select ${defaultClass}`.trim(),
    });
    if (isRequired) select.required = true;

    select.appendChild(el('option', { value: '', textContent: '-- Select --' }));
    for (const opt of prop.in_values) {
      const option = el('option', { value: opt, textContent: opt });
      if (hasDefault && opt === prop.default_value) {
        option.selected = true;
      }
      select.appendChild(option);
    }
    return select;
  }

  // 2. Object reference (sh:class)
  if (prop.target_class) {
    const wrapper = el('div', {
      className: 'reference-field',
      'data-target-class': prop.target_class,
    });
    const searchInput = el('input', {
      type: 'text',
      className: `form-input reference-search ${defaultClass}`.trim(),
      placeholder: `Search ${prop.name}...`,
      autocomplete: 'off',
      'data-target-class': prop.target_class,
    });
    const hiddenInput = el('input', {
      type: 'hidden',
      'data-path': prop.path,
    });
    if (hasDefault) {
      hiddenInput.value = prop.default_value;
    }
    wrapper.appendChild(searchInput);
    wrapper.appendChild(hiddenInput);
    return wrapper;
  }

  // 3. Date
  if (prop.datatype === `${XSD}date`) {
    return el('input', {
      type: 'date',
      'data-path': prop.path,
      className: `form-input ${defaultClass}`.trim(),
      value: hasDefault ? prop.default_value : '',
      required: isRequired,
    });
  }

  // 4. DateTime
  if (prop.datatype === `${XSD}dateTime`) {
    let dtVal = hasDefault ? prop.default_value : '';
    // Strip timezone for datetime-local input
    if (dtVal.includes('+')) dtVal = dtVal.split('+')[0];
    if (dtVal.endsWith('Z')) dtVal = dtVal.slice(0, -1);
    if (dtVal.length > 16) dtVal = dtVal.slice(0, 16);
    return el('input', {
      type: 'datetime-local',
      'data-path': prop.path,
      className: `form-input ${defaultClass}`.trim(),
      value: dtVal,
      required: isRequired,
    });
  }

  // 5. Boolean
  if (prop.datatype === `${XSD}boolean`) {
    const select = el('select', {
      'data-path': prop.path,
      className: `form-select ${defaultClass}`.trim(),
    });
    if (isRequired) select.required = true;

    const opts = [
      { value: '', label: '-- Select --' },
      { value: 'true', label: 'Yes' },
      { value: 'false', label: 'No' },
    ];
    for (const o of opts) {
      const option = el('option', { value: o.value, textContent: o.label });
      if (hasDefault && o.value === prop.default_value) {
        option.selected = true;
      }
      select.appendChild(option);
    }
    return select;
  }

  // 6. Integer
  if (prop.datatype === `${XSD}integer`) {
    return el('input', {
      type: 'number',
      step: '1',
      'data-path': prop.path,
      className: `form-input ${defaultClass}`.trim(),
      value: hasDefault ? prop.default_value : '',
      required: isRequired,
    });
  }

  // 7. Decimal / float / double
  if (
    prop.datatype &&
    (prop.datatype.endsWith('decimal') ||
      prop.datatype.endsWith('float') ||
      prop.datatype.endsWith('double'))
  ) {
    return el('input', {
      type: 'number',
      step: '0.01',
      'data-path': prop.path,
      className: `form-input ${defaultClass}`.trim(),
      value: hasDefault ? prop.default_value : '',
      required: isRequired,
    });
  }

  // 8. anyURI
  if (prop.datatype === `${XSD}anyURI`) {
    return el('input', {
      type: 'url',
      placeholder: 'https://...',
      'data-path': prop.path,
      className: `form-input ${defaultClass}`.trim(),
      value: hasDefault ? prop.default_value : '',
      required: isRequired,
    });
  }

  // 9. Tags / keywords
  if (isTagProperty(prop)) {
    return el('input', {
      type: 'text',
      placeholder: 'Type to add tags...',
      'data-path': prop.path,
      className: `form-input ${defaultClass}`.trim(),
      value: hasDefault ? prop.default_value : '',
      required: isRequired,
    });
  }

  // 10. Default — plain text
  return el('input', {
    type: 'text',
    'data-path': prop.path,
    className: `form-input ${defaultClass}`.trim(),
    value: hasDefault ? prop.default_value : '',
    required: isRequired,
  });
}

// ---------------------------------------------------------------------------
// Multi-value wrapper
// ---------------------------------------------------------------------------

/**
 * Clone the input element for a multi-value "add" action.
 * Clears the value but preserves type/attributes.
 * @param {HTMLElement} sourceInput - The original input or wrapper to clone
 * @param {Object} prop - PropertyShapeInfo for context
 * @returns {HTMLElement}
 */
function cloneEmptyInput(sourceInput, prop) {
  // For reference fields, we need to rebuild the wrapper
  if (prop.target_class) {
    const wrapper = el('div', {
      className: 'reference-field',
      'data-target-class': prop.target_class,
    });
    wrapper.appendChild(el('input', {
      type: 'text',
      className: 'form-input reference-search',
      placeholder: `Search ${prop.name}...`,
      autocomplete: 'off',
      'data-target-class': prop.target_class,
    }));
    wrapper.appendChild(el('input', {
      type: 'hidden',
      'data-path': prop.path,
    }));
    return wrapper;
  }

  // For regular inputs/selects, clone and clear
  const clone = sourceInput.cloneNode(true);
  clone.classList.remove('default-value');
  if (clone.tagName === 'SELECT') {
    clone.selectedIndex = 0;
  } else {
    clone.value = '';
  }
  return clone;
}

/**
 * Wrap an input in a multi-value container with add/remove buttons.
 * @param {HTMLElement} input - The input element
 * @param {Object} prop - PropertyShapeInfo
 * @returns {HTMLElement} The multi-value list container + add button wrapper
 */
function wrapMultiValue(input, prop) {
  const container = el('div', { className: 'multi-value-container' });

  const list = el('div', { className: 'multi-value-list' });

  // Initial item
  const item = el('div', { className: 'multi-value-item' });
  item.appendChild(input);

  const removeBtn = el('button', {
    type: 'button',
    className: 'btn-remove-value',
    textContent: '× Remove',
  });
  removeBtn.addEventListener('click', () => {
    // Keep at least one input
    if (list.querySelectorAll('.multi-value-item').length > 1) {
      item.remove();
    }
  });
  item.appendChild(removeBtn);
  list.appendChild(item);

  container.appendChild(list);

  // Add button
  const addBtn = el('button', {
    type: 'button',
    className: 'btn-add-value',
    textContent: `+ Add ${prop.name}`,
  });
  addBtn.addEventListener('click', () => {
    const newInput = cloneEmptyInput(input, prop);
    const newItem = el('div', { className: 'multi-value-item' });
    newItem.appendChild(newInput);

    const newRemoveBtn = el('button', {
      type: 'button',
      className: 'btn-remove-value',
      textContent: '× Remove',
    });
    newRemoveBtn.addEventListener('click', () => {
      if (list.querySelectorAll('.multi-value-item').length > 1) {
        newItem.remove();
      }
    });
    newItem.appendChild(newRemoveBtn);
    list.appendChild(newItem);

    // Notify parent container so reference pickers can be initialized
    const refField = newItem.querySelector('.reference-field');
    if (refField) {
      newItem.dispatchEvent(new CustomEvent('sempkm:reference-field-added', {
        bubbles: true,
        detail: { element: refField },
      }));
    }
  });
  container.appendChild(addBtn);

  return container;
}

// ---------------------------------------------------------------------------
// renderField
// ---------------------------------------------------------------------------

/**
 * Render a single form field from a PropertyShapeInfo object.
 * @param {Object} prop - PropertyShapeInfo
 * @returns {HTMLElement} A .form-field div
 */
export function renderField(prop) {
  const isRequired = prop.min_count > 0;
  const fieldDiv = el('div', {
    className: `form-field ${isRequired ? 'required' : ''}`.trim(),
  });

  // Label row
  const labelRow = el('div', { className: 'form-label-row' });
  const label = el('label', {}, [prop.name]);
  if (isRequired) {
    label.appendChild(el('span', { className: 'required-marker', textContent: '*' }));
  }
  labelRow.appendChild(label);

  // Helptext toggle button
  if (prop.helptext) {
    const helpBtn = el('button', {
      type: 'button',
      className: 'btn-helptext-toggle',
      title: 'Show help',
      textContent: '?',
    });
    const helptextDiv = el('div', {
      className: 'field-helptext',
      style: 'display:none',
    }, [
      el('div', { className: 'field-helptext-content', textContent: prop.helptext }),
    ]);

    helpBtn.addEventListener('click', () => {
      helptextDiv.style.display = helptextDiv.style.display === 'none' ? 'block' : 'none';
    });

    labelRow.appendChild(helpBtn);
    // Store helptext div to append after label row
    fieldDiv._helptextDiv = helptextDiv;
  }

  fieldDiv.appendChild(labelRow);

  // Description
  if (prop.description) {
    fieldDiv.appendChild(el('small', { className: 'field-help', textContent: prop.description }));
  }

  // Helptext expandable div (after description, before input)
  if (fieldDiv._helptextDiv) {
    fieldDiv.appendChild(fieldDiv._helptextDiv);
    delete fieldDiv._helptextDiv;
  }

  // Input element
  const input = createInput(prop);

  if (isMultiValue(prop)) {
    fieldDiv.appendChild(wrapMultiValue(input, prop));
  } else {
    fieldDiv.appendChild(input);
  }

  return fieldDiv;
}

// ---------------------------------------------------------------------------
// renderGroup
// ---------------------------------------------------------------------------

/**
 * Render a group of properties as a collapsible <details> section.
 * @param {Object} group - PropertyGroupInfo {iri, label, order}
 * @param {Object[]} properties - Filtered PropertyShapeInfo array
 * @param {boolean} [isOpen=false] - Whether the details should start open
 * @returns {HTMLElement|null} A <details> element, or null if no renderable properties
 */
function renderGroup(group, properties, isOpen = false) {
  const filtered = properties.filter(
    (p) => !SKIP_PATHS.has(p.path) && !isBodyProperty(p)
  );
  if (filtered.length === 0) return null;

  // Sort by order
  filtered.sort((a, b) => (a.order || 0) - (b.order || 0));

  const details = el('details', { className: 'form-group-section' });
  if (isOpen) details.setAttribute('open', '');

  details.appendChild(el('summary', {}, [group.label]));

  const content = el('div', { className: 'form-group-content' });
  for (const prop of filtered) {
    content.appendChild(renderField(prop));
  }
  details.appendChild(content);

  return details;
}

// ---------------------------------------------------------------------------
// renderForm
// ---------------------------------------------------------------------------

/**
 * Render a complete form from a ShapeResponse object.
 * @param {Object} shapeResponse - ShapeResponse JSON from /api/shapes/{type_iri}
 * @returns {DocumentFragment}
 */
export function renderForm(shapeResponse) {
  const fragment = document.createDocumentFragment();
  const { groups = [], properties = [] } = shapeResponse;

  // Filter out skip paths and body
  const usable = properties.filter(
    (p) => !SKIP_PATHS.has(p.path) && !isBodyProperty(p)
  );

  // Build group map: group IRI -> group info
  const groupMap = new Map();
  for (const g of groups) {
    groupMap.set(g.iri, g);
  }

  // Partition properties into grouped and ungrouped
  const grouped = new Map(); // group IRI -> property[]
  const ungrouped = [];

  for (const prop of usable) {
    if (prop.group && groupMap.has(prop.group)) {
      if (!grouped.has(prop.group)) {
        grouped.set(prop.group, []);
      }
      grouped.get(prop.group).push(prop);
    } else {
      ungrouped.push(prop);
    }
  }

  // Sort groups by order
  const sortedGroups = [...groupMap.values()]
    .filter((g) => grouped.has(g.iri))
    .sort((a, b) => (a.order || 0) - (b.order || 0));

  // Render groups — first group open, rest collapsed
  let isFirst = true;
  for (const group of sortedGroups) {
    const groupEl = renderGroup(group, grouped.get(group.iri), isFirst);
    if (groupEl) {
      fragment.appendChild(groupEl);
      isFirst = false;
    }
  }

  // Ungrouped: required fields directly, optional in collapsible section
  const ungroupedRequired = ungrouped.filter((p) => p.min_count > 0);
  const ungroupedOptional = ungrouped.filter((p) => !(p.min_count > 0));

  // Sort each set by order
  ungroupedRequired.sort((a, b) => (a.order || 0) - (b.order || 0));
  ungroupedOptional.sort((a, b) => (a.order || 0) - (b.order || 0));

  // Required ungrouped fields — render directly
  for (const prop of ungroupedRequired) {
    fragment.appendChild(renderField(prop));
  }

  // Optional ungrouped fields — in collapsed "Additional Fields" details
  if (ungroupedOptional.length > 0) {
    const details = el('details', { className: 'form-group-section' });
    details.appendChild(el('summary', {}, ['Additional Fields']));
    const content = el('div', { className: 'form-group-content' });
    for (const prop of ungroupedOptional) {
      content.appendChild(renderField(prop));
    }
    details.appendChild(content);
    fragment.appendChild(details);
  }

  return fragment;
}

// ---------------------------------------------------------------------------
// getFormValues
// ---------------------------------------------------------------------------

/**
 * Extract form values from a container as {path: value} or {path: [values]}.
 * Omits entries where all values are empty strings.
 * @param {HTMLElement} container - DOM element containing the rendered form
 * @returns {Object} Map of property path -> value or value array
 */
export function getFormValues(container) {
  const elements = container.querySelectorAll('[data-path]');
  const pathValues = new Map(); // path -> string[]

  for (const elem of elements) {
    const path = elem.getAttribute('data-path');
    if (!path) continue;

    let value = '';
    if (elem.tagName === 'SELECT') {
      value = elem.value;
    } else {
      value = elem.value;
    }

    if (!pathValues.has(path)) {
      pathValues.set(path, []);
    }
    pathValues.get(path).push(value);
  }

  const result = {};
  for (const [path, values] of pathValues) {
    // Filter out empty strings
    const nonEmpty = values.filter((v) => v !== '');
    if (nonEmpty.length === 0) continue;

    // Single value → string, multiple → array
    if (nonEmpty.length === 1) {
      result[path] = nonEmpty[0];
    } else {
      result[path] = nonEmpty;
    }
  }

  return result;
}
