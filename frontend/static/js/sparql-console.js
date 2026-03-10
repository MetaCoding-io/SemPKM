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
var cachedModelVersion = null;
var DISPLAY_LIMIT = 200;
var currentSavedQueryId = null;
var currentSavedQueryName = '';

// Known vocabulary prefixes (object IRIs are those NOT matching these)
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
  'urn:sempkm:'
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
    var resp = await fetch('/api/sparql', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ query: queryText, all_graphs: allGraphs })
    });

    var elapsed = Math.round(performance.now() - startTime);

    if (!resp.ok) {
      var errBody = '';
      try { errBody = await resp.text(); } catch (e) {}
      var errMsg = 'Query failed (HTTP ' + resp.status + ')';
      try {
        var errJson = JSON.parse(errBody);
        if (errJson.detail) errMsg = errJson.detail;
      } catch (e) {
        if (errBody) errMsg = errBody;
      }
      if (infoEl) infoEl.textContent = 'Error (' + elapsed + 'ms)';
      if (tableWrap) {
        tableWrap.innerHTML = '<div class="sparql-error">' + escapeHtml(errMsg) + '</div>';
      }
      return;
    }

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
    }

    renderResultTable(tableWrap, vars, bindings, enrichment, 0);

    // Push to session cell history
    addCellHistoryEntry(queryText, totalRows, elapsed, vars, bindings, enrichment);

  } catch (err) {
    if (infoEl) infoEl.textContent = 'Error';
    if (tableWrap) {
      tableWrap.innerHTML = '<div class="sparql-error">Network error: ' + escapeHtml(err.message) + '</div>';
    }
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
    // Vocabulary IRI: show as compact QName
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
    'onclick="if(window.openTab){window.openTab(\'' + escapeJs(uri) + '\',\'' + escapeJs(label) + '\')}">' +
    '<span class="sparql-pill-icon" style="color:' + escapeAttr(iconColor) + '">' +
    '<i data-lucide="' + escapeAttr(iconName) + '"></i></span>' +
    '<span class="sparql-pill-label">' + escapeHtml(label) + '</span></span>';
}

function shortenUri(uri) {
  // Standard prefix shortenings
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
    var resp = await fetch('/api/sparql/history', { credentials: 'include' });
    if (!resp.ok) throw new Error('Failed to load history');
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
    var resp = await fetch('/api/sparql/saved?include_shared=true', { credentials: 'include' });
    if (!resp.ok) throw new Error('Failed to load saved queries');
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
        fetch('/api/sparql/saved/' + qid + '/mark-viewed', {
          method: 'POST',
          credentials: 'include'
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
      fetch('/api/sparql/users', { credentials: 'include' }),
      fetch('/api/sparql/saved/' + queryId + '/shares', { credentials: 'include' })
    ]);
    if (!usersResp.ok || !sharesResp.ok) throw new Error('Failed to load share data');

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
        fetch('/api/sparql/saved/' + queryId + '/shares', {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          credentials: 'include',
          body: JSON.stringify({ user_ids: checkedIds })
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
    var resp = await fetch('/api/sparql/saved/' + queryId + '/fork', {
      method: 'POST',
      credentials: 'include'
    });
    if (resp.ok) {
      showBriefMessage('Forked!');
      loadSaved();
    } else {
      showBriefMessage('Fork failed');
    }
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
    var resp = await fetch('/api/sparql/saved', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ name: name, description: description, query_text: queryText })
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
    await fetch('/api/sparql/saved/' + queryId, {
      method: 'DELETE',
      credentials: 'include'
    });
    loadSaved(); // Refresh the dropdown
  } catch (err) {
    showBriefMessage('Delete failed');
  }
}

async function clearHistory() {
  if (!confirm('Clear all query history?')) return;
  try {
    await fetch('/api/sparql/history', {
      method: 'DELETE',
      credentials: 'include'
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
    var resp = await fetch('/api/sparql/vocabulary', { credentials: 'include' });
    if (!resp.ok) return;
    var data = await resp.json();
    vocabCache = data.items || [];
    prefixCache = data.prefixes || {};
    cachedModelVersion = data.model_version;
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

    fetch('/api/sparql/saved/' + queryId + '/promote', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ display_label: displayLabel, renderer_type: renderer })
    }).then(function(resp) {
      if (resp.ok) {
        showBriefMessage('Promoted!');
        dialog.close();
        // Refresh My Views in nav tree
        refreshMyViews();
      } else if (resp.status === 409) {
        showBriefMessage('Already promoted');
        dialog.close();
      } else {
        resp.json().then(function(data) {
          showBriefMessage(data.detail || 'Promote failed');
        }).catch(function() {
          showBriefMessage('Promote failed');
        });
      }
    }).catch(function() {
      showBriefMessage('Promote failed');
    });
  });
}

function refreshMyViews() {
  var myViewsTree = document.getElementById('my-views-tree');
  if (myViewsTree && typeof htmx !== 'undefined') {
    htmx.ajax('GET', '/browser/my-views', { target: '#my-views-tree', swap: 'innerHTML' });
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
  handlePromoteSubmit();
}
