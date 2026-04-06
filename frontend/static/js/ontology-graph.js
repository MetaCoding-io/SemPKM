/**
 * SemPKM Ontology TBox Graph
 *
 * Cytoscape.js initialization for the TBox tab's class hierarchy graph.
 * Fetches graph data from /browser/ontology/tbox/graph-data, renders a
 * dagre TB layout with source-based node coloring, and wires node clicks
 * to the detail panel via loadClassDetail().
 */
(function () {
  'use strict';

  // --- Source-based color palette ---
  // gist gets a neutral slate; each model source gets a distinct hue;
  // user-types get a teal accent. Unknown sources cycle through extras.
  var SOURCE_COLORS_LIGHT = {
    gist:    '#94a3b8',  // slate-400
    user:    '#2dd4bf',  // teal-400
    sempkm:  '#a78bfa', // violet-400
  };
  var SOURCE_COLORS_DARK = {
    gist:    '#64748b',  // slate-500
    user:    '#14b8a6',  // teal-500
    sempkm:  '#7c3aed', // violet-600
  };
  // Palette for model sources (basic-pkm, crm, etc.) — assigned in order
  var MODEL_PALETTE_LIGHT = [
    '#60a5fa', // blue-400
    '#f97316', // orange-500
    '#a3e635', // lime-400
    '#f472b6', // pink-400
    '#fbbf24', // amber-400
    '#34d399', // emerald-400
    '#e879f9', // fuchsia-400
    '#fb923c', // orange-400
  ];
  var MODEL_PALETTE_DARK = [
    '#3b82f6', // blue-500
    '#ea580c', // orange-600
    '#84cc16', // lime-500
    '#ec4899', // pink-500
    '#d97706', // amber-600
    '#10b981', // emerald-500
    '#c026d3', // fuchsia-600
    '#c2410c', // orange-700
  ];

  var _modelColorIndex = 0;
  var _modelColorMap = {}; // source-name → color

  function _isDark() {
    return document.documentElement.getAttribute('data-theme') === 'dark';
  }

  /**
   * Get a color for a node source string.
   * Known sources (gist, user, sempkm) get fixed colors.
   * Model sources (basic-pkm, crm, etc.) get assigned from a rotating palette.
   */
  function _colorForSource(source, isDark) {
    var fixed = isDark ? SOURCE_COLORS_DARK : SOURCE_COLORS_LIGHT;
    if (fixed[source]) return fixed[source];

    // Model source — assign from palette if not yet seen
    if (!_modelColorMap[source]) {
      var palette = isDark ? MODEL_PALETTE_DARK : MODEL_PALETTE_LIGHT;
      _modelColorMap[source] = palette[_modelColorIndex % palette.length];
      _modelColorIndex++;
    }
    return _modelColorMap[source];
  }

  /**
   * Darken a hex color by a fraction.
   */
  function _darken(hex, amount) {
    hex = hex.replace('#', '');
    var r = parseInt(hex.substring(0, 2), 16);
    var g = parseInt(hex.substring(2, 4), 16);
    var b = parseInt(hex.substring(4, 6), 16);
    r = Math.max(0, Math.floor(r * (1 - amount)));
    g = Math.max(0, Math.floor(g * (1 - amount)));
    b = Math.max(0, Math.floor(b * (1 - amount)));
    return '#' + r.toString(16).padStart(2, '0') +
                 g.toString(16).padStart(2, '0') +
                 b.toString(16).padStart(2, '0');
  }

  /**
   * Build Cytoscape stylesheet for the TBox graph.
   */
  function _buildStyle(isDark) {
    var nodeColor    = isDark ? '#c9d1d9' : '#24292f';
    var edgeColor    = isDark ? '#3e4452' : '#ccc';
    var edgeLabelClr = isDark ? '#7d8799' : '#888';
    var edgeTextBg   = isDark ? '#282c34' : '#fff';
    var selectedBdr  = isDark ? '#56b6c2' : '#2d5a9e';

    return [
      {
        selector: 'node',
        style: {
          'label': 'data(label)',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'font-size': '10px',
          'text-max-width': '110px',
          'text-wrap': 'ellipsis',
          'width': 28,
          'height': 28,
          'background-color': isDark ? '#5c6370' : '#bab0ab',
          'border-width': 1,
          'border-color': isDark ? '#3e4452' : '#999',
          'shape': 'ellipse',
          'text-margin-y': 4,
          'color': nodeColor,
        }
      },
      {
        selector: 'edge',
        style: {
          'curve-style': 'bezier',
          'target-arrow-shape': 'triangle',
          'target-arrow-color': edgeColor,
          'line-color': edgeColor,
          'width': 1.5,
          'label': '',  // hide edge labels to reduce visual noise
          'font-size': '8px',
          'color': edgeLabelClr,
          'text-background-color': edgeTextBg,
          'text-background-opacity': 0.8,
          'text-background-padding': '2px',
        }
      },
      {
        selector: 'node:selected',
        style: {
          'border-width': 3,
          'border-color': selectedBdr,
        }
      },
      {
        selector: 'node.hovered',
        style: {
          'width': 34,
          'height': 34,
        }
      },
      // Source-based colors applied dynamically via data(sourceColor)
      {
        selector: 'node[sourceColor]',
        style: {
          'background-color': 'data(sourceColor)',
          'border-color': 'data(borderColor)',
        }
      },
    ];
  }

  /**
   * Initialize the TBox Cytoscape graph.
   * Fetches data from the API, builds elements, and renders with dagre TB.
   *
   * @param {string} containerId - ID of the graph container element
   */
  function initTboxGraph(containerId) {
    var container = document.getElementById(containerId);
    if (!container) {
      console.error('[ontology-graph] Container not found:', containerId);
      return;
    }

    // Avoid double-init
    if (window.SemPKM._tboxGraph) {
      window.SemPKM._tboxGraph.destroy();
      window.SemPKM._tboxGraph = null;
    }

    container.innerHTML = '<div class="ontology-loading">Loading TBox graph…</div>';

    // Reset model color assignments for fresh render
    _modelColorIndex = 0;
    _modelColorMap = {};

    var fetchFn = window.SemPKM.apiFetch || window.apiFetch;
    if (!fetchFn) {
      console.error('[ontology-graph] apiFetch not available');
      container.innerHTML = '<div class="ontology-loading">Error: apiFetch not loaded.</div>';
      return;
    }

    fetchFn('/browser/ontology/tbox/graph-data', { silent: true })
      .then(function (resp) {
        if (!resp) return; // aborted
        return resp.json();
      })
      .then(function (data) {
        if (!data) return;
        container.innerHTML = '';

        if (!data.nodes || data.nodes.length === 0) {
          container.innerHTML = '<div class="ontology-loading">No ontology classes found.</div>';
          return;
        }

        _renderTboxGraph(container, data);
      })
      .catch(function (err) {
        console.error('[ontology-graph] Failed to load TBox graph data:', err);
        container.innerHTML = '<div class="ontology-loading">Failed to load graph data.</div>';
      });
  }

  /**
   * Apply source filter — show/hide nodes and their edges.
   * @param {Object} cy - Cytoscape instance
   * @param {Set|Array} activeSources - source names to show
   */
  function _applySourceFilter(cy, activeSources) {
    var activeSet = activeSources instanceof Set ? activeSources : new Set(activeSources);

    cy.batch(function () {
      cy.nodes().forEach(function (node) {
        if (activeSet.has(node.data('source'))) {
          node.show();
        } else {
          node.hide();
        }
      });
      cy.edges().forEach(function (edge) {
        if (edge.source().hidden() || edge.target().hidden()) {
          edge.hide();
        } else {
          edge.show();
        }
      });
    });
  }

  /**
   * Build the per-model filter checkbox UI.
   * @param {HTMLElement} toolbar - toolbar element to append into
   * @param {Array<string>} sources - distinct source names
   * @param {boolean} isDark - current theme
   * @param {Object} cy - Cytoscape instance
   */
  function _buildFilterUI(toolbar, sources, isDark, cy) {
    var wrap = document.createElement('div');
    wrap.className = 'tbox-model-filter';

    // 'All' checkbox
    var allLabel = document.createElement('label');
    allLabel.className = 'tbox-filter-item';
    var allCb = document.createElement('input');
    allCb.type = 'checkbox';
    allCb.checked = true;
    allCb.className = 'tbox-filter-cb-all';
    allLabel.appendChild(allCb);
    var allText = document.createElement('span');
    allText.className = 'tbox-filter-label';
    allText.textContent = 'All';
    allLabel.appendChild(allText);
    wrap.appendChild(allLabel);

    var checkboxes = [];

    for (var i = 0; i < sources.length; i++) {
      (function (src) {
        var label = document.createElement('label');
        label.className = 'tbox-filter-item';

        var cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.checked = true;
        cb.setAttribute('data-source', src);
        label.appendChild(cb);

        var dot = document.createElement('span');
        dot.className = 'tbox-filter-dot';
        dot.style.backgroundColor = _colorForSource(src, isDark);
        label.appendChild(dot);

        var txt = document.createElement('span');
        txt.className = 'tbox-filter-label';
        txt.textContent = src;
        label.appendChild(txt);

        checkboxes.push(cb);

        cb.addEventListener('change', function () {
          _syncAllCheckbox(allCb, checkboxes);
          _applyFromCheckboxes(cy, checkboxes);
        });

        wrap.appendChild(label);
      })(sources[i]);
    }

    // 'All' toggles all individual checkboxes
    allCb.addEventListener('change', function () {
      var checked = allCb.checked;
      for (var k = 0; k < checkboxes.length; k++) {
        checkboxes[k].checked = checked;
      }
      _applyFromCheckboxes(cy, checkboxes);
    });

    toolbar.appendChild(wrap);
    // Store reference for theme updates
    wrap._checkboxes = checkboxes;
  }

  /** Recalculate 'All' checkbox state from individual checkboxes */
  function _syncAllCheckbox(allCb, checkboxes) {
    var allChecked = true;
    for (var i = 0; i < checkboxes.length; i++) {
      if (!checkboxes[i].checked) { allChecked = false; break; }
    }
    allCb.checked = allChecked;
  }

  /** Collect active sources from checkboxes and apply filter */
  function _applyFromCheckboxes(cy, checkboxes) {
    var active = [];
    for (var i = 0; i < checkboxes.length; i++) {
      if (checkboxes[i].checked) {
        active.push(checkboxes[i].getAttribute('data-source'));
      }
    }
    _applySourceFilter(cy, active);
  }

  /**
   * Programmatic filter: show/hide a specific source.
   * @param {string} sourceName - source to toggle
   * @param {boolean} visible - true to show, false to hide
   */
  function filterTboxBySource(sourceName, visible) {
    var cy = window.SemPKM._tboxGraph;
    if (!cy) return;
    // Find the checkbox and toggle it
    var wrap = document.querySelector('.tbox-model-filter');
    if (!wrap) return;
    var cb = wrap.querySelector('input[data-source="' + sourceName + '"]');
    if (cb) {
      cb.checked = visible;
      var allCb = wrap.querySelector('.tbox-filter-cb-all');
      if (allCb) _syncAllCheckbox(allCb, wrap._checkboxes || []);
      _applyFromCheckboxes(cy, wrap._checkboxes || []);
    }
  }

  /**
   * Render the Cytoscape graph from API data.
   */
  function _renderTboxGraph(container, data) {
    var isDark = _isDark();
    var elements = [];

    // Build nodes with source-based colors
    for (var i = 0; i < data.nodes.length; i++) {
      var node = data.nodes[i];
      var color = _colorForSource(node.source || 'other', isDark);
      elements.push({
        group: 'nodes',
        data: {
          id: node.id,
          label: node.label || node.id.split('/').pop().split('#').pop(),
          source: node.source || 'other',
          sourceColor: color,
          borderColor: _darken(color, 0.2),
        }
      });
    }

    // Build edges
    for (var j = 0; j < data.edges.length; j++) {
      var edge = data.edges[j];
      elements.push({
        group: 'edges',
        data: {
          id: 'e-' + j,
          source: edge.source,
          target: edge.target,
        }
      });
    }

    var cy = cytoscape({
      container: container,
      elements: elements,
      style: _buildStyle(isDark),
      layout: {
        name: 'dagre',
        rankDir: 'TB',
        rankSep: 60,
        nodeSep: 30,
        animate: true,
        animationDuration: 400,
      },
      minZoom: 0.1,
      maxZoom: 5,
      wheelSensitivity: 0.3,
    });

    // Store instance
    window.SemPKM._tboxGraph = cy;
    // Also set legacy reference for toggleTboxView()
    window._tboxCy = cy;

    // --- Body-appended popover (escapes dockview stacking context) ---
    var popover = document.createElement('div');
    popover.className = 'graph-popover';
    document.body.appendChild(popover);

    var _hoverTimer = null;
    var _hideTimer = null;
    var _popoverHovered = false;

    popover.addEventListener('mouseenter', function () {
      _popoverHovered = true;
      if (_hideTimer) { clearTimeout(_hideTimer); _hideTimer = null; }
    });
    popover.addEventListener('mouseleave', function () {
      _popoverHovered = false;
      popover.style.display = 'none';
    });

    function _esc(s) {
      var d = document.createElement('span');
      d.textContent = s;
      return d.innerHTML;
    }

    function _showTboxPopover(nodeEl, evt) {
      var d = nodeEl.data();
      var html = '<div class="graph-popover-header">' +
        '<span class="graph-popover-label">' + _esc(d.label) + '</span>' +
        '<span class="graph-popover-type" style="background-color:' + d.sourceColor + '">' + _esc(d.source) + '</span>' +
      '</div>' +
      '<div style="padding:6px 14px 10px;"><span class="graph-popover-iri">' + _esc(d.id) + '</span></div>';

      popover.innerHTML = html;
      popover.style.display = 'block';
      _popoverHovered = false;

      // Position via fixed coords: container rect + rendered position
      var pos = evt.renderedPosition || nodeEl.renderedPosition();
      var cRect = container.getBoundingClientRect();
      var left = cRect.left + pos.x + 16;
      var top = cRect.top + pos.y - 12;

      popover.style.left = left + 'px';
      popover.style.top = top + 'px';

      // Viewport overflow clamping
      var pRect = popover.getBoundingClientRect();
      if (pRect.right > window.innerWidth - 8) {
        popover.style.left = (cRect.left + pos.x - pRect.width - 12) + 'px';
      }
      if (pRect.bottom > window.innerHeight - 8) {
        popover.style.top = (cRect.top + pos.y - pRect.height + 12) + 'px';
      }
    }

    // --- Event handlers ---

    // Click → load class detail in bottom panel
    cy.on('tap', 'node', function (evt) {
      var nodeId = evt.target.id();
      if (typeof loadClassDetail === 'function') {
        loadClassDetail(nodeId);
      }
    });

    // Hover: size feedback + delayed popover
    cy.on('mouseover', 'node', function (evt) {
      evt.target.addClass('hovered');
      container.style.cursor = 'pointer';
      if (_hideTimer) { clearTimeout(_hideTimer); _hideTimer = null; }
      if (_hoverTimer) { clearTimeout(_hoverTimer); }
      var target = evt.target;
      _hoverTimer = setTimeout(function () {
        _showTboxPopover(target, evt);
        _hoverTimer = null;
      }, 250);
    });
    cy.on('mouseout', 'node', function (evt) {
      evt.target.removeClass('hovered');
      container.style.cursor = 'default';
      if (_hoverTimer) { clearTimeout(_hoverTimer); _hoverTimer = null; }
      _hideTimer = setTimeout(function () {
        if (!_popoverHovered) {
          popover.style.display = 'none';
        }
      }, 100);
    });

    // --- Filter UI ---
    // Extract distinct sources and build filter checkboxes
    var sourceSet = new Set();
    for (var s = 0; s < data.nodes.length; s++) {
      sourceSet.add(data.nodes[s].source || 'other');
    }
    var sortedSources = Array.from(sourceSet).sort(function (a, b) {
      // gist first, then alpha
      if (a === 'gist') return -1;
      if (b === 'gist') return 1;
      return a.localeCompare(b);
    });

    // Build source→color map for external use
    var sourceColors = {};
    for (var sc = 0; sc < sortedSources.length; sc++) {
      sourceColors[sortedSources[sc]] = _colorForSource(sortedSources[sc], isDark);
    }
    window.SemPKM._tboxSourceColors = sourceColors;

    // Find toolbar and append filter UI
    var mainView = container.closest('.tbox-main-view');
    var toolbar = mainView ? mainView.querySelector('.tbox-view-toolbar') : null;
    if (toolbar) {
      // Remove any existing filter UI (re-init case)
      var existing = toolbar.querySelector('.tbox-model-filter');
      if (existing) existing.remove();

      _buildFilterUI(toolbar, sortedSources, isDark, cy);
    }

    // --- Cleanup ---
    if (typeof window.SemPKM.registerCleanup === 'function' && container.id) {
      window.SemPKM.registerCleanup(container.id, function () {
        if (window.SemPKM._tboxGraph === cy) {
          window.SemPKM._tboxGraph = null;
          window._tboxCy = null;
        }
        // Remove body-appended popover
        if (popover.parentNode) popover.parentNode.removeChild(popover);
        // Remove filter UI from toolbar
        var filterEl = document.querySelector('.tbox-model-filter');
        if (filterEl) filterEl.remove();
        // Clear pending timers
        if (_hoverTimer) clearTimeout(_hoverTimer);
        if (_hideTimer) clearTimeout(_hideTimer);
        cy.destroy();
      });
    }
  }

  // --- Theme change handler ---
  document.addEventListener('sempkm:theme-changed', function (e) {
    var cy = window.SemPKM._tboxGraph;
    if (!cy) return;

    var isDark = (e.detail && e.detail.theme === 'dark');

    // Rebuild model color map for new theme
    var oldMap = Object.assign({}, _modelColorMap);
    _modelColorIndex = 0;
    _modelColorMap = {};
    var sources = Object.keys(oldMap);
    for (var i = 0; i < sources.length; i++) {
      _colorForSource(sources[i], isDark);
    }

    // Update node data with new colors
    cy.nodes().forEach(function (node) {
      var src = node.data('source');
      if (src) {
        var color = _colorForSource(src, isDark);
        node.data('sourceColor', color);
        node.data('borderColor', _darken(color, 0.2));
      }
    });

    // Rebuild stylesheet
    cy.style().fromJson(_buildStyle(isDark)).update();
  });

  // --- Export ---
  window.SemPKM.initTboxGraph = initTboxGraph;
  window.SemPKM.filterTboxBySource = filterTboxBySource;

})();
