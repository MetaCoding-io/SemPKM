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

    // --- Event handlers ---

    // Click → load class detail in bottom panel
    cy.on('tap', 'node', function (evt) {
      var nodeId = evt.target.id();
      if (typeof loadClassDetail === 'function') {
        loadClassDetail(nodeId);
      }
    });

    // Hover feedback
    cy.on('mouseover', 'node', function (evt) {
      evt.target.addClass('hovered');
      container.style.cursor = 'pointer';
    });
    cy.on('mouseout', 'node', function (evt) {
      evt.target.removeClass('hovered');
      container.style.cursor = 'default';
    });

    // --- Cleanup ---
    if (typeof window.SemPKM.registerCleanup === 'function' && container.id) {
      window.SemPKM.registerCleanup(container.id, function () {
        if (window.SemPKM._tboxGraph === cy) {
          window.SemPKM._tboxGraph = null;
          window._tboxCy = null;
        }
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

})();
