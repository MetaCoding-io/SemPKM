/**
 * SemPKM SPARQL Console
 *
 * CodeMirror 6 based SPARQL editor with query execution, result rendering
 * with enriched IRI pills, session cell history, server-side history/saved
 * query dropdowns, and ontology-aware autocomplete.
 *
 * Loaded as an ES module via dynamic import() on first SPARQL tab activation.
 */

import { EditorView, keymap } from "https://esm.sh/@codemirror/view@6";
import { EditorState, Compartment } from "https://esm.sh/@codemirror/state@6";
import { basicSetup } from "https://esm.sh/codemirror@6.0.1";
import { autocompletion } from "https://esm.sh/@codemirror/autocomplete@6";

// Try to load SPARQL language support; fall back gracefully
var sparqlLang = null;
try {
  var mod = await import("https://esm.sh/codemirror-lang-sparql@2");
  sparqlLang = mod.sparql;
} catch (e) {
  console.warn("SPARQL language extension failed to load, using plain text:", e);
}

// --- Theme Compartment ---
var themeCompartment = new Compartment();

var darkEditorTheme = EditorView.theme({
  '&': { backgroundColor: '#282c34', color: '#abb2bf' },
  '.cm-cursor, .cm-dropCursor': { borderLeftColor: '#56b6c2' },
  '.cm-gutters': { backgroundColor: '#21252b', color: '#5c6370', borderRight: '1px solid #3e4452' },
  '.cm-activeLineGutter': { backgroundColor: '#2c313a' },
  '.cm-activeLine': { backgroundColor: '#2c313a' },
  '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection': { backgroundColor: '#3E4451' }
}, { dark: true });

var lightEditorTheme = EditorView.theme({
  '&': { backgroundColor: '#ffffff', color: '#1a1a2e' },
  '.cm-gutters': { backgroundColor: '#f8f9fb', color: '#666', borderRight: '1px solid #e0e0e0' }
}, { dark: false });

function getCurrentTheme() {
  return document.documentElement.getAttribute('data-theme') === 'dark'
    ? darkEditorTheme
    : lightEditorTheme;
}

// --- Module State ---
var editorView = null;
var cellHistory = [];
var vocabCache = [];
var prefixCache = {};
var reversePrefixMap = {};   // namespace → prefix, rebuilt when prefixCache changes
var vocabIriIndex = {};      // full_iri → vocabCache item, rebuilt when vocabCache changes
var cachedModelVersion = null;
var DISPLAY_LIMIT = 200;
var currentSavedQueryId = null;
var currentSavedQueryName = '';
var sparqlCyInstance = null;  // Current Cytoscape instance for SPARQL graph tab
var mirrorAllowlistCache = null;  // Cached mirror endpoint allowlist (fetched lazily)
var _serviceInfoDebounce = null;  // Debounce timer for SERVICE info banner updates

// Known vocabulary prefixes (object IRIs are those NOT matching these).
// NOTE: urn:sempkm:model:* is intentionally EXCLUDED so that model ontology
// class/property IRIs get enriched with pills.  Only internal machinery
// namespaces are listed here.
var KNOWN_VOCAB_PREFIXES = [
  'http://www.w3.org/1999/02/22-rdf-syntax-ns#',
  'http://www.w3.org/2000/01/rdf-schema#',
  'http://www.w3.org/2002/07/owl#',
  'http://purl.org/dc/terms/',
  'http://www.w3.org/2004/02/skos/core#',
  'http://xmlns.com/foaf/0.1/',
  'https://schema.org/',
  'http://schema.org/',
  'http://www.w3.org/2001/XMLSchema#',
  'http://www.w3.org/ns/shacl#',
  'http://www.w3.org/ns/prov#',
  // Specific urn:sempkm: internal namespaces (NOT the broad "urn:sempkm:")
  'urn:sempkm:app:',
  'urn:sempkm:canvas:',
  'urn:sempkm:dashboard:',
  'urn:sempkm:data:',
  'urn:sempkm:event:',
  'urn:sempkm:inbox:',
  'urn:sempkm:inference:',
  'urn:sempkm:instance:',
  'urn:sempkm:lint-result:',
  'urn:sempkm:lint-run:',
  'urn:sempkm:mount:',
  'urn:sempkm:obj:',
  'urn:sempkm:object:',
  'urn:sempkm:ontology:',
  'urn:sempkm:ops-log:',
  'urn:sempkm:person:',
  'urn:sempkm:query:',
  'urn:sempkm:query-exec:',
  'urn:sempkm:query-view:',
  'urn:sempkm:shared:',
  'urn:sempkm:state:',
  'urn:sempkm:task:',
  'urn:sempkm:user:',
  'urn:sempkm:user-types:',
  'urn:sempkm:user-view:',
  'urn:sempkm:validation:',
  'urn:sempkm:vfs:',
  'urn:sempkm:view:',
  'urn:sempkm:vocab:',
  'urn:sempkm:webhook:',
  'urn:sempkm:workflow:',
  'urn:sempkm:mirrored:',
  'urn:sempkm:mirror-prov:'
];

// SPARQL keywords for autocomplete
var SPARQL_KEYWORDS = [
  'SELECT', 'WHERE', 'FILTER', 'OPTIONAL', 'UNION', 'BIND',
  'GROUP BY', 'ORDER BY', 'LIMIT', 'OFFSET', 'HAVING',
  'VALUES', 'ASK', 'CONSTRUCT', 'DESCRIBE', 'PREFIX', 'BASE',
  'DISTINCT', 'REDUCED', 'AS', 'FROM', 'NAMED',
  'NOT EXISTS', 'EXISTS', 'MINUS', 'SERVICE', 'IN', 'NOT IN',
  'a', 'GRAPH', 'INSERT', 'DELETE', 'STR', 'LANG', 'LANGMATCHES',
  'DATATYPE', 'BOUND', 'IRI', 'URI', 'BNODE', 'RAND', 'ABS',
  'CEIL', 'FLOOR', 'ROUND', 'CONCAT', 'STRLEN', 'UCASE', 'LCASE',
  'CONTAINS', 'STRSTARTS', 'STRENDS', 'YEAR', 'MONTH', 'DAY',
  'HOURS', 'MINUTES', 'SECONDS', 'NOW', 'IF', 'COALESCE',
  'REGEX', 'REPLACE', 'COUNT', 'SUM', 'MIN', 'MAX', 'AVG',
  'SAMPLE', 'GROUP_CONCAT', 'SEPARATOR', 'true', 'false',
  'isIRI', 'isURI', 'isBlank', 'isLiteral', 'isNumeric'
];

// --- Autocomplete ---

function sparqlCompletions(context) {
  // --- SERVICE URI autocomplete (checked first, returns early) ---
  var line = context.state.doc.lineAt(context.pos);
  var textBeforeCursor = line.text.substring(0, context.pos - line.from);
  var serviceUriMatch = textBeforeCursor.match(/SERVICE\s+(?:SILENT\s+)?<([^>]*)$/i);
  if (serviceUriMatch) {
    var partial = serviceUriMatch[1].toLowerCase();
    var angleBracketPos = line.from + textBeforeCursor.lastIndexOf('<') + 1;
    var uriOptions = [];
    if (mirrorAllowlistCache && mirrorAllowlistCache.length > 0) {
      mirrorAllowlistCache.forEach(function(entry) {
        var url = _allowlistEntryUrl(entry);
        if (url && url.toLowerCase().indexOf(partial) === 0) {
          uriOptions.push({ label: url, type: 'url', detail: '\u26D3' });
        }
      });
    }
    if (uriOptions.length === 0) return null;
    return { from: angleBracketPos, options: uriOptions, validFor: /^[^\s>]*/ };
  }

  var word = context.matchBefore(/[\w:?$]*/);
  if (!word || (word.from === word.to && !context.explicit)) return null;

  var text = word.text;
  var options = [];

  // SPARQL keywords
  var lowerText = text.toLowerCase();
  SPARQL_KEYWORDS.forEach(function(kw) {
    if (kw.toLowerCase().indexOf(lowerText) === 0 || kw.toLowerCase().indexOf(lowerText) !== -1) {
      options.push({ label: kw, type: 'keyword', detail: 'K' });
    }
  });

  // Prefixed names (when text contains a colon)
  var colonIdx = text.indexOf(':');
  if (colonIdx !== -1) {
    var prefix = text.substring(0, colonIdx);
    var localPart = text.substring(colonIdx + 1).toLowerCase();
    vocabCache.forEach(function(item) {
      if (item.qname && item.qname.indexOf(prefix + ':') === 0) {
        var itemLocal = item.qname.substring(prefix.length + 1).toLowerCase();
        if (!localPart || itemLocal.indexOf(localPart) !== -1) {
          options.push({
            label: item.qname,
            detail: item.badge || 'C',
            info: item.label || '',
            type: 'class'
          });
        }
      }
    });
  }

  // PREFIX declarations (when text starts with P/p)
  if (text.length >= 1 && (text[0] === 'P' || text[0] === 'p')) {
    Object.keys(prefixCache).forEach(function(prefix) {
      var declaration = 'PREFIX ' + prefix + ': <' + prefixCache[prefix] + '>';
      if (declaration.toLowerCase().indexOf(text.toLowerCase()) !== -1) {
        options.push({
          label: declaration,
          apply: declaration + '\n',
          detail: 'D',
          type: 'namespace'
        });
      }
    });
  }

  // Variable names (when text starts with ? or $)
  if (text.length >= 1 && (text[0] === '?' || text[0] === '$')) {
    var doc = context.state.doc.toString();
    var varMatch;
    var varRegex = /[?$]\w+/g;
    var seen = {};
    while ((varMatch = varRegex.exec(doc)) !== null) {
      var varName = varMatch[0];
      if (!seen[varName] && varName !== text) {
        seen[varName] = true;
        options.push({ label: varName, type: 'variable', detail: 'V' });
      }
    }
  }

  if (options.length === 0) return null;
  return { from: word.from, options: options, validFor: /^[\w:?$]*$/ };
}

// --- Editor Setup ---

function createEditor(container) {
  var extensions = [
    basicSetup,
    themeCompartment.of(getCurrentTheme()),
    keymap.of([{
      key: 'Ctrl-Enter',
      mac: 'Cmd-Enter',
      run: function() { executeQuery(); return true; }
    }]),
    autocompletion({
      override: [sparqlCompletions],
      activateOnTyping: true
    }),
    EditorView.theme({
      '&': { height: '100%' },
      '.cm-scroller': { overflow: 'auto' }
    }),
    EditorView.updateListener.of(function(update) {
      if (update.docChanged) {
        clearTimeout(_serviceInfoDebounce);
        _serviceInfoDebounce = setTimeout(function() {
          _updateServiceInfoBanner(update.state.doc.toString());
        }, 500);
      }
    })
  ];

  if (sparqlLang) {
    extensions.push(sparqlLang());
  }

  var defaultQuery = 'SELECT ?s ?p ?o WHERE {\n  ?s ?p ?o .\n} LIMIT 10';

  editorView = new EditorView({
    state: EditorState.create({
      doc: defaultQuery,
      extensions: extensions
    }),
    parent: container
  });

  // Theme change listener
  document.addEventListener('sempkm:theme-changed', function() {
    if (editorView) {
      editorView.dispatch({
        effects: themeCompartment.reconfigure(getCurrentTheme())
      });
    }
  });
}

// --- SERVICE Clause Detection & Mirror Support ---

/**
 * Detect SERVICE clause endpoint URLs in a SPARQL query.
 * Handles both SERVICE <url> and SERVICE SILENT <url> patterns.
 * Strips string literals first to avoid false matches inside quoted strings.
 * Returns an array of unique endpoint URL strings.
 */
function detectServiceEndpoints(queryText) {
  if (!queryText) return [];
  // Strip string literals to avoid matching SERVICE inside strings
  var stripped = queryText.replace(/"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'/g, '""');
  var regex = /\bSERVICE\s+(?:SILENT\s+)?<([^>]+)>/gi;
  var endpoints = [];
  var seen = {};
  var match;
  while ((match = regex.exec(stripped)) !== null) {
    var url = match[1];
    if (!seen[url]) {
      seen[url] = true;
      endpoints.push(url);
    }
  }
  return endpoints;
}

/**
 * Fetch and cache the mirror endpoint allowlist.
 * Resolves to an array of allowed endpoint URL strings.
 * Returns cached value on subsequent calls.
 */
async function fetchMirrorAllowlist() {
  if (mirrorAllowlistCache !== null) return mirrorAllowlistCache;
  try {
    var resp = await apiFetch('/api/sparql/mirror/endpoints', { credentials: 'include', silent: true });
    var data = await resp.json();
    mirrorAllowlistCache = (data.endpoints || []);
  } catch (e) {
    console.warn('Failed to fetch mirror allowlist:', e);
    mirrorAllowlistCache = [];
  }
  return mirrorAllowlistCache;
}

/**
 * Extract the URL string from an allowlist entry.
 * Handles both new object format {url, source, removable} and legacy string format.
 */
function _allowlistEntryUrl(entry) {
  if (typeof entry === 'string') return entry;
  if (entry && typeof entry === 'object' && entry.url) return entry.url;
  return '';
}

/**
 * Check if an endpoint URL is in the cached allowlist.
 * Handles both object format {url, source, removable} and legacy string format.
 */
function isEndpointAllowed(endpointUrl) {
  if (!mirrorAllowlistCache || mirrorAllowlistCache.length === 0) return false;
  return mirrorAllowlistCache.some(function(entry) {
    return _allowlistEntryUrl(entry) === endpointUrl;
  });
}

/**
 * Update the SERVICE info banner below the editor.
 * Shows detected SERVICE endpoints with allowlist status indicators.
 * Called on a 500ms debounce from the EditorView.updateListener.
 */
function _updateServiceInfoBanner(queryText) {
  var banner = document.getElementById('sparql-service-info');
  if (!banner) return;

  var endpoints = detectServiceEndpoints(queryText);
  if (endpoints.length === 0) {
    banner.style.display = 'none';
    banner.innerHTML = '';
    return;
  }

  // If cache hasn't been fetched yet, trigger it and re-render when ready
  if (mirrorAllowlistCache === null) {
    fetchMirrorAllowlist().then(function() {
      _updateServiceInfoBanner(queryText);
    });
    return;
  }

  var html = '<span class="service-info-label">SERVICE endpoints:</span>';
  endpoints.forEach(function(url) {
    var allowed = isEndpointAllowed(url);
    var statusClass = allowed ? 'endpoint-allowed' : 'endpoint-blocked';
    var icon = allowed ? '\u2713' : '\u26A0';
    var title = allowed ? 'Endpoint is in the allowlist' : 'Endpoint is NOT in the allowlist — mirroring will be blocked';
    html += '<span class="endpoint-status ' + statusClass + '" title="' + title + '">'
          + '<span class="endpoint-status-icon">' + icon + '</span>'
          + '<span class="endpoint-status-url">' + _escapeHtml(url) + '</span>'
          + '</span>';
  });

  banner.innerHTML = html;
  banner.style.display = 'flex';
}

/**
 * Escape HTML special characters for safe insertion.
 */
function _escapeHtml(str) {
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

// --- Query Execution ---

async function executeQuery() {
  if (!editorView) return;

  var queryText = editorView.state.doc.toString().trim();
  if (!queryText) return;

  var allGraphsEl = document.getElementById('sparql-all-graphs');
  var allGraphs = allGraphsEl ? allGraphsEl.checked : false;

  var infoEl = document.getElementById('sparql-results-info');
  var tableWrap = document.getElementById('sparql-results-table-wrap');

  if (infoEl) infoEl.textContent = 'Running query...';
  if (tableWrap) tableWrap.innerHTML = '<div class="sparql-results-placeholder">Running...</div>';

  var startTime = performance.now();

  try {
    var resp = await apiFetch('/api/sparql', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ query: queryText, all_graphs: allGraphs }),
      silent: true
    });

    var elapsed = Math.round(performance.now() - startTime);

    var data = await resp.json();
    var enrichment = data._enrichment || {};
    var vars = (data.head && data.head.vars) ? data.head.vars : [];
    var bindings = (data.results && data.results.bindings) ? data.results.bindings : [];
    var totalRows = bindings.length;

    if (infoEl) {
      infoEl.innerHTML = '';
      infoEl.appendChild(document.createTextNode(
        totalRows + ' row' + (totalRows !== 1 ? 's' : '') + ' (' + elapsed + 'ms)'
      ));
      if (currentSavedQueryId) {
        var viewBtn = document.createElement('button');
        viewBtn.className = 'sparql-save-view-btn';
        viewBtn.textContent = 'Save as View';
        viewBtn.title = 'Promote this saved query to a browsable view';
        viewBtn.addEventListener('click', function() {
          openPromoteDialog(currentSavedQueryId, currentSavedQueryName, queryText);
        });
        infoEl.appendChild(viewBtn);
      }

      // Mirror Results button — appears when query contains SERVICE clauses
      var serviceEndpoints = detectServiceEndpoints(queryText);
      if (serviceEndpoints.length > 0) {
        var endpointUrl = serviceEndpoints[0];
        var mirrorBtn = document.createElement('button');
        mirrorBtn.className = 'sparql-mirror-btn';
        mirrorBtn.dataset.endpoint = endpointUrl;
        mirrorBtn.innerHTML = '<i data-lucide="database"></i> Mirror Results';
        mirrorBtn.title = 'Mirror federated results into local triplestore';

        // Check allowlist and add warning if endpoint not allowed
        fetchMirrorAllowlist().then(function(allowlist) {
          if (!isEndpointAllowed(endpointUrl)) {
            mirrorBtn.classList.add('mirror-warning');
            mirrorBtn.title = 'This endpoint is not in the allowlist \u2014 mirroring may be blocked';
          }
          // Re-render Lucide icons for the button
          if (window.lucide) window.lucide.createIcons();
        });

        mirrorBtn.addEventListener('click', function() {
          handleMirrorClick(mirrorBtn, queryText, endpointUrl);
        });
        infoEl.appendChild(mirrorBtn);

        // Render Lucide icon immediately (allowlist check may update later)
        if (window.lucide) window.lucide.createIcons();
      }
    }

    renderResultTable(tableWrap, vars, bindings, enrichment, 0);

    // Inject Table/Graph tab switcher for triple-pattern results
    injectGraphTab(tableWrap, vars, bindings);

    // Push to session cell history
    addCellHistoryEntry(queryText, totalRows, elapsed, vars, bindings, enrichment);

  } catch (err) {
    var elapsed = Math.round(performance.now() - startTime);
    var errMsg = err.message;
    if (err.body) { try { var ej = JSON.parse(err.body); if (ej.detail) errMsg = ej.detail; } catch (_) { errMsg = err.body; } }
    if (infoEl) infoEl.textContent = 'Error (' + elapsed + 'ms)';
    if (tableWrap) {
      tableWrap.innerHTML = '<div class="sparql-error">' + escapeHtml(errMsg) + '</div>';
    }
  }
}

// --- Mirror Click Handler ---

/**
 * Handle Mirror Results button click — POST to /api/sparql/mirror,
 * show progress feedback, handle success/error states.
 */
async function handleMirrorClick(btn, queryText, endpointUrl) {
  // Disable button and show progress
  btn.disabled = true;
  var originalHtml = btn.innerHTML;
  btn.innerHTML = '<i data-lucide="loader-2"></i> Mirroring\u2026';
  if (window.lucide) window.lucide.createIcons();

  try {
    var resp = await apiFetch('/api/sparql/mirror', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ query: queryText, endpoint_url: endpointUrl }),
      silent: true
    });

    var data = await resp.json();
    var count = data.mirrored_count || 0;
    btn.innerHTML = '<i data-lucide="check"></i> <span class="sparql-mirror-success">Mirrored ' + count + ' triple' + (count !== 1 ? 's' : '') + '</span>';
    btn.classList.add('mirror-success');
    if (window.lucide) window.lucide.createIcons();
    // Keep disabled — mirroring is done
  } catch (err) {
    if (err.status === 403) {
      var errDetail = '';
      try { errDetail = JSON.parse(err.body || '{}').detail || 'Endpoint not allowed'; } catch (_) { errDetail = 'Endpoint not allowed'; }
      btn.innerHTML = '<i data-lucide="shield-alert"></i> Not allowed';
      btn.title = errDetail + '. Ask an admin to add it to the federation allowlist.';
      btn.classList.add('mirror-error');
      if (window.lucide) window.lucide.createIcons();
      btn.disabled = false;
    } else if (err.status) {
      var errBody = '';
      try { errBody = JSON.parse(err.body || '{}').detail || 'Mirror failed (HTTP ' + err.status + ')'; } catch (_) { errBody = 'Mirror failed (HTTP ' + err.status + ')'; }
      btn.innerHTML = '<i data-lucide="alert-triangle"></i> Error';
      btn.title = errBody;
      btn.classList.add('mirror-error');
      if (window.lucide) window.lucide.createIcons();
      btn.disabled = false;
    } else {
      btn.innerHTML = '<i data-lucide="alert-triangle"></i> Network error';
      btn.title = err.message;
      btn.classList.add('mirror-error');
      if (window.lucide) window.lucide.createIcons();
      btn.disabled = false;
    }
  }
}

// --- Triple-Pattern Detection & Graph Building ---

/**
 * Detect whether a SPARQL result set looks like a triple pattern (s/p/o).
 * Returns true when vars has exactly 3 items AND either:
 *  - var names match common subject/predicate/object naming patterns, OR
 *  - a sample of bindings shows mostly URI values across all 3 vars.
 */
function isTriplePattern(vars, bindings) {
  if (!vars || vars.length !== 3) return false;
  if (!bindings || bindings.length === 0) return false;

  // Check naming patterns
  var names = vars.map(function(v) { return v.toLowerCase(); });
  var spoSets = [
    ['s', 'p', 'o'],
    ['subject', 'predicate', 'object'],
    ['sub', 'pred', 'obj'],
    ['subj', 'pred', 'obj'],
    ['source', 'predicate', 'target'],
    ['src', 'pred', 'tgt']
  ];
  for (var i = 0; i < spoSets.length; i++) {
    var set = spoSets[i];
    if (names[0] === set[0] && names[1] === set[1] && names[2] === set[2]) {
      return true;
    }
  }

  // Heuristic: sample first ~10 bindings and check if most values are URIs
  var sampleSize = Math.min(bindings.length, 10);
  var uriCounts = [0, 0, 0];
  for (var j = 0; j < sampleSize; j++) {
    for (var k = 0; k < 3; k++) {
      var cell = bindings[j][vars[k]];
      if (cell && cell.type === 'uri') {
        uriCounts[k]++;
      }
    }
  }
  // All 3 vars should have >60% URIs in the sample
  var threshold = sampleSize * 0.6;
  return uriCounts[0] >= threshold && uriCounts[1] >= threshold && uriCounts[2] >= threshold;
}

/**
 * Build Cytoscape elements from SPARQL bindings.
 * Maps vars[0] → subject, vars[1] → predicate, vars[2] → object.
 * Returns { nodes: [...], edges: [...] } in Cytoscape element format.
 */
function buildGraphElements(vars, bindings) {
  var subjectVar = vars[0];
  var predicateVar = vars[1];
  var objectVar = vars[2];

  var nodeMap = {};  // id → { id, label, fullIri }
  var edges = [];

  function addNode(cell) {
    if (!cell) return null;
    var id = cell.value;
    if (!nodeMap[id]) {
      var label = cell.type === 'uri' ? shortenUri(cell.value) : cell.value;
      // Truncate long literal labels
      if (label.length > 40) label = label.substring(0, 37) + '...';
      nodeMap[id] = {
        id: id,
        label: label,
        fullIri: cell.type === 'uri' ? cell.value : null,
        isLiteral: cell.type !== 'uri'
      };
    }
    return id;
  }

  for (var i = 0; i < bindings.length; i++) {
    var b = bindings[i];
    var sCell = b[subjectVar];
    var pCell = b[predicateVar];
    var oCell = b[objectVar];

    var sourceId = addNode(sCell);
    var targetId = addNode(oCell);
    var predLabel = pCell ? (pCell.type === 'uri' ? shortenUri(pCell.value) : pCell.value) : '?';

    if (sourceId && targetId) {
      edges.push({
        group: 'edges',
        data: {
          id: 'e' + i,
          source: sourceId,
          target: targetId,
          label: predLabel,
          fullPredicate: pCell ? pCell.value : ''
        }
      });
    }
  }

  var nodes = [];
  var ids = Object.keys(nodeMap);
  for (var j = 0; j < ids.length; j++) {
    var n = nodeMap[ids[j]];
    nodes.push({
      group: 'nodes',
      data: {
        id: n.id,
        label: n.label,
        fullIri: n.fullIri || n.id,
        isLiteral: n.isLiteral
      }
    });
  }

  return { nodes: nodes, edges: edges };
}

/**
 * Initialize (or re-initialize) the Cytoscape graph for SPARQL triple results.
 */
function initSparqlGraph(container, vars, bindings) {
  // Destroy previous instance
  if (sparqlCyInstance) {
    sparqlCyInstance.destroy();
    sparqlCyInstance = null;
  }

  if (!container) return;

  try {
    if (typeof cytoscape === 'undefined') {
      container.innerHTML = '<div class="sparql-graph-error">Cytoscape.js not loaded</div>';
      console.error('Failed to initialize SPARQL graph: cytoscape is undefined');
      return;
    }

    var elements = buildGraphElements(vars, bindings);

    // Determine best layout based on graph size
    var nodeCount = elements.nodes.length;
    var layoutName = 'fcose';
    var layoutOpts = {
      name: 'fcose',
      animate: true,
      animationDuration: 500,
      fit: true,
      padding: 30,
      nodeSeparation: 120,
      idealEdgeLength: 100
    };

    // For small graphs, dagre works better for directed trees
    if (nodeCount < 30 && typeof dagre !== 'undefined') {
      layoutOpts = {
        name: 'dagre',
        rankDir: 'LR',
        nodeSep: 50,
        rankSep: 80,
        animate: true,
        animationDuration: 500,
        fit: true,
        padding: 30
      };
    }

    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var textColor = isDark ? '#ccc' : '#333';
    var edgeColor = isDark ? '#666' : '#ccc';
    var arrowColor = isDark ? '#888' : '#bbb';
    var bgOpacity = isDark ? 0.8 : 0.85;
    var bgColor = isDark ? '#282c34' : '#fff';
    var litBg = isDark ? '#3e4452' : '#f0f0f0';
    var uriBg = isDark ? '#2c5282' : '#dbeafe';

    sparqlCyInstance = cytoscape({
      container: container,
      elements: elements.nodes.concat(elements.edges),
      style: [
        {
          selector: 'node',
          style: {
            'background-color': uriBg,
            'label': 'data(label)',
            'text-valign': 'bottom',
            'text-halign': 'center',
            'font-size': '10px',
            'width': 32,
            'height': 32,
            'border-width': 2,
            'border-color': isDark ? '#4a90d9' : '#3b82f6',
            'text-margin-y': 4,
            'color': textColor,
            'text-wrap': 'ellipsis',
            'text-max-width': '100px'
          }
        },
        {
          selector: 'node[?isLiteral]',
          style: {
            'background-color': litBg,
            'shape': 'round-rectangle',
            'border-color': isDark ? '#666' : '#999',
            'width': 80,
            'height': 24,
            'padding': '6px',
            'text-valign': 'center',
            'text-margin-y': 0
          }
        },
        {
          selector: 'edge',
          style: {
            'curve-style': 'bezier',
            'target-arrow-shape': 'triangle',
            'target-arrow-color': arrowColor,
            'line-color': edgeColor,
            'width': 1.5,
            'label': 'data(label)',
            'font-size': '9px',
            'text-rotation': 'autorotate',
            'color': isDark ? '#aaa' : '#888',
            'text-background-color': bgColor,
            'text-background-opacity': bgOpacity,
            'text-background-padding': '2px'
          }
        },
        {
          selector: 'node.hovered',
          style: {
            'border-width': 3,
            'width': 38,
            'height': 38
          }
        },
        {
          selector: 'node.hovered[?isLiteral]',
          style: {
            'border-width': 3,
            'height': 28
          }
        }
      ],
      layout: layoutOpts,
      minZoom: 0.2,
      maxZoom: 4,
      wheelSensitivity: 0.3
    });

    // Tooltip for node hover
    var tooltip = container.querySelector('.sparql-graph-tooltip');
    if (!tooltip) {
      tooltip = document.createElement('div');
      tooltip.className = 'sparql-graph-tooltip';
      container.appendChild(tooltip);
    }

    sparqlCyInstance.on('mouseover', 'node', function(evt) {
      evt.target.addClass('hovered');
      var data = evt.target.data();
      tooltip.textContent = data.fullIri || data.id;
      tooltip.style.display = 'block';
      var pos = evt.renderedPosition;
      tooltip.style.left = (pos.x + 16) + 'px';
      tooltip.style.top = (pos.y - 12) + 'px';
    });

    sparqlCyInstance.on('mouseout', 'node', function(evt) {
      evt.target.removeClass('hovered');
      tooltip.style.display = 'none';
    });

    sparqlCyInstance.on('mouseover', 'edge', function(evt) {
      var data = evt.target.data();
      tooltip.textContent = data.fullPredicate || data.label;
      tooltip.style.display = 'block';
      var pos = evt.renderedPosition;
      tooltip.style.left = (pos.x + 16) + 'px';
      tooltip.style.top = (pos.y - 12) + 'px';
    });

    sparqlCyInstance.on('mouseout', 'edge', function() {
      tooltip.style.display = 'none';
    });

  } catch (err) {
    console.error('Failed to initialize SPARQL graph:', err);
    container.innerHTML = '<div class="sparql-graph-error">Failed to render graph: ' + escapeHtml(err.message) + '</div>';
  }
}

/**
 * Inject a Table/Graph tab switcher above results when results are triple-pattern.
 * Both views share the same bindings data — no re-fetching needed.
 */
function injectGraphTab(tableWrap, vars, bindings) {
  if (!tableWrap) return;

  // Destroy any previous Cytoscape instance
  if (sparqlCyInstance) {
    sparqlCyInstance.destroy();
    sparqlCyInstance = null;
  }

  // Remove any previous tab bar and graph container
  var resultsWrap = tableWrap.parentElement;
  if (!resultsWrap) return;

  var oldTabBar = resultsWrap.querySelector('.sparql-result-tabs');
  if (oldTabBar) oldTabBar.remove();
  var oldGraph = resultsWrap.querySelector('.sparql-graph-container');
  if (oldGraph) oldGraph.remove();

  if (!isTriplePattern(vars, bindings)) return;

  // Create tab bar
  var tabBar = document.createElement('div');
  tabBar.className = 'sparql-result-tabs';
  tabBar.innerHTML =
    '<button class="sparql-result-tab active" data-tab="table">' +
      '<i data-lucide="table-2"></i> Table' +
    '</button>' +
    '<button class="sparql-result-tab" data-tab="graph">' +
      '<i data-lucide="git-fork"></i> Graph' +
    '</button>' +
    '<span class="sparql-graph-tab-hint">' +
      '<i data-lucide="info"></i> Triple pattern detected' +
    '</span>';

  // Create graph container (hidden initially)
  var graphContainer = document.createElement('div');
  graphContainer.className = 'sparql-graph-container';
  graphContainer.style.display = 'none';

  // Insert tab bar before the table wrap, graph container after
  resultsWrap.insertBefore(tabBar, tableWrap);
  resultsWrap.insertBefore(graphContainer, tableWrap.nextSibling);

  // Track whether graph has been initialized (lazy init on first click)
  var graphInitialized = false;

  // Bind tab click handlers
  var tabs = tabBar.querySelectorAll('.sparql-result-tab');
  tabs.forEach(function(tab) {
    tab.addEventListener('click', function() {
      // Update active tab
      tabs.forEach(function(t) { t.classList.remove('active'); });
      tab.classList.add('active');

      var which = tab.getAttribute('data-tab');
      if (which === 'table') {
        tableWrap.style.display = '';
        graphContainer.style.display = 'none';
      } else {
        tableWrap.style.display = 'none';
        graphContainer.style.display = '';

        // Lazy-initialize graph on first click
        if (!graphInitialized) {
          graphInitialized = true;
          initSparqlGraph(graphContainer, vars, bindings);
        } else if (sparqlCyInstance) {
          // Re-fit on tab switch in case container was resized
          sparqlCyInstance.resize();
          sparqlCyInstance.fit(undefined, 30);
        }
      }
    });
  });

  // Initialize Lucide icons in tab bar
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ root: tabBar });
  }
}

// --- Result Table ---

function renderResultTable(container, vars, bindings, enrichment, startIdx) {
  if (!container) return;

  if (bindings.length === 0) {
    container.innerHTML = '<div class="sparql-results-placeholder">No results</div>';
    return;
  }

  var endIdx = Math.min(startIdx + DISPLAY_LIMIT, bindings.length);
  var html = '<table class="sparql-results-table" id="sparql-results-table">';
  html += '<thead><tr>';
  vars.forEach(function(v) {
    html += '<th>' + escapeHtml(v) + '</th>';
  });
  html += '</tr></thead><tbody>';

  for (var i = startIdx; i < endIdx; i++) {
    var binding = bindings[i];
    html += '<tr>';
    vars.forEach(function(v) {
      var cell = binding[v];
      html += '<td>' + renderCell(cell, enrichment) + '</td>';
    });
    html += '</tr>';
  }

  html += '</tbody></table>';

  if (endIdx < bindings.length) {
    html += '<div class="sparql-load-more">';
    html += '<button class="sparql-load-more-btn" id="sparql-load-more-btn">';
    html += 'Load more (' + (bindings.length - endIdx) + ' remaining)';
    html += '</button></div>';
  }

  container.innerHTML = html;

  // Bind load more handler
  var loadMoreBtn = document.getElementById('sparql-load-more-btn');
  if (loadMoreBtn) {
    loadMoreBtn.addEventListener('click', function() {
      renderResultTable(container, vars, bindings, enrichment, endIdx);
    });
  }

  // Initialize Lucide icons in pills
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ root: container });
  }
}

function renderCell(cell, enrichment) {
  if (!cell) return '<span class="sparql-null">-</span>';

  if (cell.type === 'uri') {
    var uri = cell.value;
    var enr = enrichment[uri];
    if (enr) {
      return renderIriPill(uri, enr);
    }

    // Vocab pill fallback: if the IRI is in vocabCache, render a styled pill
    var vocabItem = vocabIriIndex[uri];
    if (vocabItem) {
      var vocabLabel = vocabItem.qname || shortenUri(uri);
      var vocabBadge = vocabItem.badge || 'C';
      var vocabIcon = vocabBadge === 'C' ? 'box' : (vocabBadge === 'D' ? 'type' : 'arrow-right');
      return '<span class="sparql-iri-pill sparql-vocab-pill" title="' + escapeAttr(uri) + '">' +
        '<span class="sparql-pill-icon"><i data-lucide="' + escapeAttr(vocabIcon) + '"></i></span>' +
        '<span class="sparql-pill-label">' + escapeHtml(vocabLabel) + '</span></span>';
    }

    // Plain vocabulary IRI: show as compact QName
    return '<span class="sparql-uri" title="' + escapeAttr(uri) + '">' + escapeHtml(shortenUri(uri)) + '</span>';
  }

  if (cell.type === 'bnode') {
    return '<span class="sparql-bnode">_:' + escapeHtml(cell.value) + '</span>';
  }

  // Literal
  var text = escapeHtml(cell.value);
  if (cell['xml:lang']) {
    text += '<span class="sparql-lang">@' + escapeHtml(cell['xml:lang']) + '</span>';
  }
  return '<span class="sparql-literal">' + text + '</span>';
}

function renderIriPill(uri, enr) {
  var iconName = (enr.icon && enr.icon.icon) ? enr.icon.icon : 'circle';
  var iconColor = (enr.icon && enr.icon.color) ? enr.icon.color : '#999';
  var label = enr.label || enr.qname || uri;

  return '<span class="sparql-iri-pill" title="' + escapeAttr(uri) + '" ' +
    'data-iri="' + escapeAttr(uri) + '" data-label="' + escapeAttr(label) + '" ' +
    'onclick="if(window.SemPKM.openTab){window.SemPKM.openTab(\'' + escapeJs(uri) + '\',\'' + escapeJs(label) + '\')}">' +
    '<span class="sparql-pill-icon" style="color:' + escapeAttr(iconColor) + '">' +
    '<i data-lucide="' + escapeAttr(iconName) + '"></i></span>' +
    '<span class="sparql-pill-label">' + escapeHtml(label) + '</span></span>';
}

function shortenUri(uri) {
  // Standard prefix shortenings (hardcoded well-known namespaces)
  var prefixes = {
    'http://www.w3.org/1999/02/22-rdf-syntax-ns#': 'rdf:',
    'http://www.w3.org/2000/01/rdf-schema#': 'rdfs:',
    'http://www.w3.org/2002/07/owl#': 'owl:',
    'http://purl.org/dc/terms/': 'dcterms:',
    'http://www.w3.org/2004/02/skos/core#': 'skos:',
    'http://xmlns.com/foaf/0.1/': 'foaf:',
    'http://www.w3.org/2001/XMLSchema#': 'xsd:',
    'http://www.w3.org/ns/shacl#': 'sh:',
    'https://schema.org/': 'schema:',
    'http://schema.org/': 'schema:'
  };
  for (var ns in prefixes) {
    if (uri.indexOf(ns) === 0) {
      return prefixes[ns] + uri.substring(ns.length);
    }
  }

  // Dynamic prefixes from prefixCache (model ontology namespaces, etc.)
  for (var namespace in reversePrefixMap) {
    if (uri.indexOf(namespace) === 0) {
      return reversePrefixMap[namespace] + ':' + uri.substring(namespace.length);
    }
  }

  // Try extracting local name from # or last /
  var hashIdx = uri.lastIndexOf('#');
  if (hashIdx !== -1) return uri.substring(hashIdx + 1);
  var slashIdx = uri.lastIndexOf('/');
  if (slashIdx !== -1 && slashIdx < uri.length - 1) return uri.substring(slashIdx + 1);
  return uri.length > 60 ? uri.substring(0, 57) + '...' : uri;
}

// --- Cell History ---

function addCellHistoryEntry(queryText, rowCount, elapsedMs, vars, bindings, enrichment) {
  var entry = {
    query_text: queryText,
    row_count: rowCount,
    elapsed_ms: elapsedMs,
    vars: vars,
    bindings: bindings.slice(0, 50), // Keep max 50 rows in cell history entries
    enrichment: enrichment,
    timestamp: new Date()
  };
  cellHistory.unshift(entry);

  // Cap at 50 entries
  if (cellHistory.length > 50) cellHistory.length = 50;

  renderCellHistory();
}

function renderCellHistory() {
  var header = document.getElementById('sparql-cell-history-header');
  var container = document.getElementById('sparql-cell-history-items');
  if (!container) return;

  if (cellHistory.length === 0) {
    if (header) header.style.display = 'none';
    container.innerHTML = '';
    return;
  }

  if (header) header.style.display = '';

  var html = '';
  cellHistory.forEach(function(entry, idx) {
    var firstLine = entry.query_text.split('\n')[0];
    if (firstLine.length > 80) firstLine = firstLine.substring(0, 77) + '...';

    html += '<div class="sparql-cell-item" data-cell-idx="' + idx + '">';
    html += '<div class="sparql-cell-summary" onclick="this.parentElement.classList.toggle(\'expanded\')">';
    html += '<span class="sparql-cell-chevron">&#9656;</span>';
    html += '<span class="sparql-cell-query-preview">' + escapeHtml(firstLine) + '</span>';
    html += '<span class="sparql-cell-badge">' + entry.row_count + ' rows</span>';
    html += '<span class="sparql-cell-time">' + entry.elapsed_ms + 'ms</span>';
    html += '</div>';
    html += '<div class="sparql-cell-detail">';
    html += '<pre class="sparql-cell-query-full">' + escapeHtml(entry.query_text) + '</pre>';

    // Mini result table
    if (entry.vars && entry.vars.length > 0 && entry.bindings.length > 0) {
      html += '<div class="sparql-cell-results-wrap">';
      html += '<table class="sparql-results-table sparql-mini-table">';
      html += '<thead><tr>';
      entry.vars.forEach(function(v) { html += '<th>' + escapeHtml(v) + '</th>'; });
      html += '</tr></thead><tbody>';
      var maxRows = Math.min(entry.bindings.length, 10);
      for (var i = 0; i < maxRows; i++) {
        html += '<tr>';
        entry.vars.forEach(function(v) {
          var cell = entry.bindings[i][v];
          html += '<td>' + renderCell(cell, entry.enrichment) + '</td>';
        });
        html += '</tr>';
      }
      html += '</tbody></table>';
      if (entry.bindings.length > 10) {
        html += '<div class="sparql-cell-more">... and ' + (entry.bindings.length - 10) + ' more rows</div>';
      }
      html += '</div>';
    }

    html += '</div></div>';
  });

  container.innerHTML = html;

  // Init Lucide icons in cell history
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ root: container });
  }
}

// --- History Dropdown ---

async function loadHistory() {
  var container = document.getElementById('sparql-history-items');
  if (!container) return;
  container.innerHTML = '<div class="sparql-dropdown-loading">Loading...</div>';

  try {
    var resp = await apiFetch('/api/sparql/history', { credentials: 'include', silent: true });
    var entries = await resp.json();

    if (!entries || entries.length === 0) {
      container.innerHTML = '<div class="sparql-dropdown-empty">No history yet</div>';
      return;
    }

    var html = '';
    entries.forEach(function(entry) {
      var firstLine = entry.query_text.split('\n')[0];
      if (firstLine.length > 60) firstLine = firstLine.substring(0, 57) + '...';
      var timeAgo = formatTimeAgo(new Date(entry.executed_at));

      html += '<div class="sparql-dropdown-item sparql-history-item" data-query-text="' + escapeAttr(entry.query_text) + '">';
      html += '<div class="sparql-dropdown-item-main">';
      html += '<span class="sparql-dropdown-item-label">' + escapeHtml(firstLine) + '</span>';
      html += '<span class="sparql-dropdown-item-time">' + escapeHtml(timeAgo) + '</span>';
      html += '</div>';
      html += '<button class="sparql-star-btn" title="Save this query" data-query-text-ref="true"><i data-lucide="star"></i></button>';
      html += '</div>';
    });

    container.innerHTML = html;

    // Bind click handlers
    container.querySelectorAll('.sparql-history-item').forEach(function(item) {
      item.querySelector('.sparql-dropdown-item-main').addEventListener('click', function() {
        var qt = item.getAttribute('data-query-text');
        setEditorContent(qt);
        closeAllDropdowns();
      });
      var starBtn = item.querySelector('.sparql-star-btn');
      if (starBtn) {
        starBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          var qt = item.getAttribute('data-query-text');
          promptSaveQuery(qt);
        });
      }
    });

    if (typeof lucide !== 'undefined') {
      lucide.createIcons({ root: container });
    }
  } catch (err) {
    container.innerHTML = '<div class="sparql-dropdown-empty">Error loading history</div>';
  }
}

// --- Saved Dropdown ---

async function loadSaved() {
  var container = document.getElementById('sparql-saved-items');
  if (!container) return;
  container.innerHTML = '<div class="sparql-dropdown-loading">Loading...</div>';

  try {
    var resp = await apiFetch('/api/sparql/saved?include_shared=true', { credentials: 'include', silent: true });
    var data = await resp.json();

    var myQueries = data.my_queries || [];
    var sharedQueries = data.shared_with_me || [];

    if (myQueries.length === 0 && sharedQueries.length === 0) {
      container.innerHTML = '<div class="sparql-dropdown-empty">No saved queries</div>';
      return;
    }

    var html = '';

    // My Queries section
    if (myQueries.length > 0) {
      html += '<div class="sparql-dropdown-section-header">My Queries</div>';
      myQueries.forEach(function(entry) {
        var desc = entry.description || '';
        if (desc.length > 50) desc = desc.substring(0, 47) + '...';

        html += '<div class="sparql-dropdown-item sparql-saved-item" data-query-id="' + entry.id + '" data-query-text="' + escapeAttr(entry.query_text) + '">';
        html += '<div class="sparql-dropdown-item-main">';
        html += '<span class="sparql-dropdown-item-name">' + escapeHtml(entry.name) + '</span>';
        if (desc) {
          html += '<span class="sparql-dropdown-item-desc">' + escapeHtml(desc) + '</span>';
        }
        html += '</div>';
        html += '<button class="sparql-share-btn" title="Share query" data-query-id-ref="' + entry.id + '"><i data-lucide="share-2"></i></button>';
        html += '<button class="sparql-promote-btn" title="Promote to view" data-query-id-ref="' + entry.id + '"><i data-lucide="pin"></i></button>';
        html += '<button class="sparql-delete-btn" title="Delete saved query" data-query-id-ref="' + entry.id + '"><i data-lucide="trash-2"></i></button>';
        html += '</div>';
      });
    }

    // Shared with Me section
    if (sharedQueries.length > 0) {
      if (myQueries.length > 0) {
        html += '<div class="sparql-dropdown-divider"></div>';
      }
      html += '<div class="sparql-dropdown-section-header">Shared with Me</div>';
      sharedQueries.forEach(function(entry) {
        html += '<div class="sparql-dropdown-item sparql-shared-item" data-query-id="' + entry.id + '" data-query-text="' + escapeAttr(entry.query_text) + '">';
        html += '<div class="sparql-dropdown-item-main">';
        html += '<span class="sparql-dropdown-item-name">' + escapeHtml(entry.name) + '</span>';
        html += '<span class="sparql-shared-owner">from ' + escapeHtml(entry.owner_name) + '</span>';
        if (entry.is_updated) {
          html += '<span class="sparql-updated-badge" title="Updated since last viewed"></span>';
        }
        html += '</div>';
        html += '<button class="sparql-fork-btn" title="Save as my own" data-query-id-ref="' + entry.id + '"><i data-lucide="copy-plus"></i></button>';
        html += '</div>';
      });
    }

    container.innerHTML = html;

    // Bind click handlers for owned queries
    container.querySelectorAll('.sparql-saved-item').forEach(function(item) {
      item.querySelector('.sparql-dropdown-item-main').addEventListener('click', function() {
        var qt = item.getAttribute('data-query-text');
        var qid = item.getAttribute('data-query-id');
        var name = item.querySelector('.sparql-dropdown-item-name');
        currentSavedQueryId = qid;
        currentSavedQueryName = name ? name.textContent.trim() : '';
        setEditorContent(qt);
        closeAllDropdowns();
      });
      var deleteBtn = item.querySelector('.sparql-delete-btn');
      if (deleteBtn) {
        deleteBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          var qid = item.getAttribute('data-query-id');
          deleteSavedQuery(qid);
        });
      }
      var shareBtn = item.querySelector('.sparql-share-btn');
      if (shareBtn) {
        shareBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          var qid = item.getAttribute('data-query-id');
          toggleSharePicker(item, qid);
        });
      }
      var promoteBtn = item.querySelector('.sparql-promote-btn');
      if (promoteBtn) {
        promoteBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          var qid = item.getAttribute('data-query-id');
          var name = item.querySelector('.sparql-dropdown-item-name');
          var queryName = name ? name.textContent.trim() : '';
          var qt = item.getAttribute('data-query-text') || '';
          openPromoteDialog(qid, queryName, qt);
        });
      }
    });

    // Bind click handlers for shared queries
    container.querySelectorAll('.sparql-shared-item').forEach(function(item) {
      item.querySelector('.sparql-dropdown-item-main').addEventListener('click', function() {
        var qt = item.getAttribute('data-query-text');
        var qid = item.getAttribute('data-query-id');
        setEditorContent(qt);
        // Mark as viewed to clear Updated badge
        apiFetch('/api/sparql/saved/' + qid + '/mark-viewed', {
          method: 'POST',
          credentials: 'include',
          silent: true
        }).catch(function() {});
        closeAllDropdowns();
      });
      var forkBtn = item.querySelector('.sparql-fork-btn');
      if (forkBtn) {
        forkBtn.addEventListener('click', function(e) {
          e.stopPropagation();
          var qid = item.getAttribute('data-query-id');
          forkSharedQuery(qid);
        });
      }
    });

    if (typeof lucide !== 'undefined') {
      lucide.createIcons({ root: container });
    }
  } catch (err) {
    container.innerHTML = '<div class="sparql-dropdown-empty">Error loading saved queries</div>';
  }
}

// --- Share Picker ---

async function toggleSharePicker(itemEl, queryId) {
  // If picker already open, close it
  var existing = itemEl.querySelector('.sparql-share-picker');
  if (existing) {
    existing.remove();
    return;
  }

  // Close any other open pickers
  document.querySelectorAll('.sparql-share-picker').forEach(function(p) { p.remove(); });

  var panel = document.getElementById('sparql-panel');
  var currentUserId = panel ? panel.getAttribute('data-current-user-id') : '';

  try {
    // Fetch users and current shares in parallel
    var [usersResp, sharesResp] = await Promise.all([
      apiFetch('/api/sparql/users', { credentials: 'include', silent: true }),
      apiFetch('/api/sparql/saved/' + queryId + '/shares', { credentials: 'include', silent: true })
    ]);

    var users = await usersResp.json();
    var sharedIds = await sharesResp.json();
    var sharedSet = new Set(sharedIds.map(String));

    // Filter out current user
    var eligibleUsers = users.filter(function(u) {
      return String(u.id) !== currentUserId;
    });

    if (eligibleUsers.length === 0) {
      showBriefMessage('No users to share with');
      return;
    }

    var pickerHtml = '';
    eligibleUsers.forEach(function(u) {
      var checked = sharedSet.has(String(u.id)) ? ' checked' : '';
      var displayName = u.display_name || u.email;
      pickerHtml += '<label><input type="checkbox" value="' + u.id + '"' + checked + '> ' + escapeHtml(displayName) + '</label>';
    });

    var picker = document.createElement('div');
    picker.className = 'sparql-share-picker';
    picker.innerHTML = pickerHtml;
    itemEl.appendChild(picker);

    // Bind checkbox change handlers
    picker.querySelectorAll('input[type="checkbox"]').forEach(function(cb) {
      cb.addEventListener('change', function() {
        var checkedIds = [];
        picker.querySelectorAll('input[type="checkbox"]:checked').forEach(function(c) {
          checkedIds.push(c.value);
        });
        apiFetch('/api/sparql/saved/' + queryId + '/shares', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ user_ids: checkedIds }),
          silent: true
        }).catch(function() {
          showBriefMessage('Share update failed');
        });
      });
    });
  } catch (err) {
    showBriefMessage('Failed to load share picker');
  }
}

// --- Fork Shared Query ---

async function forkSharedQuery(queryId) {
  try {
    var resp = await apiFetch('/api/sparql/saved/' + queryId + '/fork', {
      method: 'POST',
      credentials: 'include',
      silent: true
    });
    showBriefMessage('Forked!');
    loadSaved();
  } catch (err) {
    showBriefMessage('Fork failed');
  }
}

// --- Save / Delete Actions ---

async function promptSaveQuery(queryText) {
  var name = prompt('Save query as:');
  if (!name) return;
  var description = prompt('Description (optional):') || '';

  try {
    var resp = await apiFetch('/api/sparql/saved', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ name: name, description: description, query_text: queryText }),
      silent: true
    });
    if (resp.ok) {
      showBriefMessage('Saved!');
    } else {
      showBriefMessage('Save failed');
    }
  } catch (err) {
    showBriefMessage('Save failed');
  }
}

async function deleteSavedQuery(queryId) {
  if (!confirm('Delete this saved query?')) return;
  try {
    await apiFetch('/api/sparql/saved/' + queryId, {
      method: 'DELETE',
      credentials: 'include',
      silent: true
    });
    loadSaved(); // Refresh the dropdown
  } catch (err) {
    showBriefMessage('Delete failed');
  }
}

async function clearHistory() {
  if (!confirm('Clear all query history?')) return;
  try {
    await apiFetch('/api/sparql/history', {
      method: 'DELETE',
      credentials: 'include',
      silent: true
    });
    var container = document.getElementById('sparql-history-items');
    if (container) container.innerHTML = '<div class="sparql-dropdown-empty">No history yet</div>';
  } catch (err) {
    showBriefMessage('Clear failed');
  }
}

// --- Vocabulary Cache ---

async function fetchVocabulary() {
  try {
    var resp = await apiFetch('/api/sparql/vocabulary', { credentials: 'include', silent: true });
    var data = await resp.json();
    vocabCache = data.items || [];
    prefixCache = data.prefixes || {};
    cachedModelVersion = data.model_version;

    // Rebuild reverse prefix map (namespace → prefix) for shortenUri()
    var rmap = {};
    Object.keys(prefixCache).forEach(function(prefix) {
      rmap[prefixCache[prefix]] = prefix;
    });
    reversePrefixMap = rmap;

    // Rebuild IRI index for vocab pill lookup in renderCell()
    var idx = {};
    vocabCache.forEach(function(item) {
      if (item.full_iri) idx[item.full_iri] = item;
    });
    vocabIriIndex = idx;
  } catch (err) {
    console.warn('Failed to fetch SPARQL vocabulary:', err);
  }
}

// --- UI Helpers ---

function setEditorContent(text) {
  if (!editorView) return;
  editorView.dispatch({
    changes: { from: 0, to: editorView.state.doc.length, insert: text }
  });
}

function closeAllDropdowns() {
  var dropdowns = document.querySelectorAll('.sparql-dropdown');
  dropdowns.forEach(function(d) { d.style.display = 'none'; });
}

function toggleDropdown(dropdownId) {
  var dd = document.getElementById(dropdownId);
  if (!dd) return;
  var isOpen = dd.style.display !== 'none';
  closeAllDropdowns();
  if (!isOpen) {
    dd.style.display = '';
    // Load data when opening
    if (dropdownId === 'sparql-history-dropdown') loadHistory();
    if (dropdownId === 'sparql-saved-dropdown') loadSaved();
  }
}

function showBriefMessage(msg) {
  var el = document.getElementById('sparql-results-info');
  if (el) {
    var prev = el.textContent;
    el.textContent = msg;
    setTimeout(function() {
      if (el.textContent === msg) el.textContent = prev;
    }, 2000);
  }
}

function formatTimeAgo(date) {
  var now = new Date();
  var diffMs = now - date;
  var diffSec = Math.floor(diffMs / 1000);
  if (diffSec < 60) return diffSec + 's ago';
  var diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return diffMin + 'm ago';
  var diffHour = Math.floor(diffMin / 60);
  if (diffHour < 24) return diffHour + 'h ago';
  var diffDay = Math.floor(diffHour / 24);
  if (diffDay < 30) return diffDay + 'd ago';
  return date.toLocaleDateString();
}

function escapeHtml(str) {
  if (!str) return '';
  var div = document.createElement('div');
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}

function escapeAttr(str) {
  if (!str) return '';
  return str.replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function escapeJs(str) {
  if (!str) return '';
  return str.replace(/\\/g, '\\\\').replace(/'/g, "\\'").replace(/\n/g, '\\n');
}

// --- Promote Dialog ---

function openPromoteDialog(queryId, queryName, queryText) {
  var dialog = document.getElementById('promote-dialog');
  if (!dialog) return;

  document.getElementById('promote-query-id').value = queryId;
  document.getElementById('promote-label').value = queryName || '';

  // Show/hide graph warning based on query content and selected renderer
  var graphWarning = document.getElementById('promote-graph-warning');
  var hasGraphVars = queryText && /\?source\b/.test(queryText) && /\?target\b/.test(queryText);

  var rendererRadios = dialog.querySelectorAll('input[name="renderer_type"]');
  rendererRadios.forEach(function(radio) {
    radio.addEventListener('change', function() {
      if (graphWarning) {
        graphWarning.style.display = (this.value === 'graph' && !hasGraphVars) ? '' : 'none';
      }
    });
  });

  // Reset to table
  var tableRadio = dialog.querySelector('input[name="renderer_type"][value="table"]');
  if (tableRadio) tableRadio.checked = true;
  if (graphWarning) graphWarning.style.display = 'none';

  // Init Lucide icons in the dialog
  if (typeof lucide !== 'undefined') {
    lucide.createIcons({ root: dialog });
  }

  dialog.showModal();
}

function handlePromoteSubmit() {
  var dialog = document.getElementById('promote-dialog');
  if (!dialog) return;

  var form = document.getElementById('promote-form');

  form.addEventListener('submit', function(e) {
    e.preventDefault();

    var queryId = document.getElementById('promote-query-id').value;
    var displayLabel = document.getElementById('promote-label').value.trim();
    var rendererType = form.querySelector('input[name="renderer_type"]:checked');
    var renderer = rendererType ? rendererType.value : 'table';

    if (!displayLabel) {
      showBriefMessage('View name is required');
      return;
    }

    apiFetch('/api/sparql/saved/' + queryId + '/promote', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ display_label: displayLabel, renderer_type: renderer }),
      silent: true
    }).then(function(resp) {
      showBriefMessage('Promoted!');
      dialog.close();
      // Refresh My Views in nav tree
      refreshMyViews();
    }).catch(function(err) {
      if (err.status === 409) {
        showBriefMessage('Already promoted');
        dialog.close();
      } else {
        var detail = 'Promote failed';
        try { detail = JSON.parse(err.body || '{}').detail || detail; } catch (_) {}
        showBriefMessage(detail);
      }
    });
  });
}

function refreshMyViews() {
  var savedViewsTree = document.getElementById('saved-views-tree');
  if (savedViewsTree && typeof htmx !== 'undefined') {
    htmx.ajax('GET', '/browser/my-views', { target: '#saved-views-tree', swap: 'innerHTML' });
  }
}

// --- Initialization ---

function bindToolbarEvents() {
  var runBtn = document.getElementById('sparql-run-btn');
  if (runBtn) runBtn.addEventListener('click', executeQuery);

  var saveBtn = document.getElementById('sparql-save-btn');
  if (saveBtn) {
    saveBtn.addEventListener('click', function() {
      if (!editorView) return;
      var qt = editorView.state.doc.toString().trim();
      if (!qt) return;
      promptSaveQuery(qt);
    });
  }

  var historyBtn = document.getElementById('sparql-history-btn');
  if (historyBtn) {
    historyBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      toggleDropdown('sparql-history-dropdown');
    });
  }

  var savedBtn = document.getElementById('sparql-saved-btn');
  if (savedBtn) {
    savedBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      toggleDropdown('sparql-saved-dropdown');
    });
  }

  var clearHistoryBtn = document.getElementById('sparql-clear-history-btn');
  if (clearHistoryBtn) {
    clearHistoryBtn.addEventListener('click', function(e) {
      e.stopPropagation();
      clearHistory();
    });
  }

  var clearCellsBtn = document.getElementById('sparql-clear-cells-btn');
  if (clearCellsBtn) {
    clearCellsBtn.addEventListener('click', function() {
      cellHistory = [];
      renderCellHistory();
    });
  }

  // Close dropdowns on outside click
  document.addEventListener('click', function(e) {
    if (!e.target.closest('.sparql-dropdown-wrap')) {
      closeAllDropdowns();
    }
  });
}

export function initSparqlConsole() {
  var container = document.getElementById('sparql-editor');
  if (!container) {
    console.error('SPARQL editor container #sparql-editor not found');
    return;
  }

  // Avoid double-init
  if (container.querySelector('.cm-editor')) return;

  createEditor(container);
  bindToolbarEvents();
  fetchVocabulary();
  fetchMirrorAllowlist();  // Warm the allowlist cache for SERVICE autocomplete & info banner

  // Create the SERVICE info banner below the editor
  var editorWrap = container.closest('.sparql-editor-wrap');
  if (editorWrap && !document.getElementById('sparql-service-info')) {
    var banner = document.createElement('div');
    banner.id = 'sparql-service-info';
    banner.className = 'sparql-service-info';
    banner.style.display = 'none';
    editorWrap.appendChild(banner);
  }

  handlePromoteSubmit();
}
