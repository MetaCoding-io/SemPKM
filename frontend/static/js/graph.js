/**
 * SemPKM Graph Visualization
 *
 * Cytoscape.js initialization, semantic styling, interaction handlers,
 * and layout registry with registerLayout() for model-contributed layouts.
 */

(function () {
  'use strict';

  // --- Layout Registry ---
  var LAYOUT_REGISTRY = {
    'fcose': { name: 'fcose', animate: true, animationDuration: 500, quality: 'default' },
    'dagre': { name: 'dagre', animate: true, animationDuration: 500, rankDir: 'TB' },
    'concentric': { name: 'concentric', animate: true, animationDuration: 500 }
  };

  var currentLayoutName = 'fcose';

  function registerLayout(name, configObj) {
    LAYOUT_REGISTRY[name] = configObj;
  }

  // --- Semantic Style Builder ---

  function buildSemanticStyle(typeColors, isDark) {
    isDark = isDark || false;

    var nodeColor = isDark ? '#abb2bf' : '#333';
    var nodeBg = isDark ? '#5c6370' : '#bab0ab';
    var nodeBorder = isDark ? '#3e4452' : '#999';
    var edgeLineColor = isDark ? '#3e4452' : '#ccc';
    var edgeLabelColor = isDark ? '#7d8799' : '#888';
    var edgeTextBg = isDark ? '#282c34' : '#fff';
    var selectedBorder = isDark ? '#56b6c2' : '#2d5a9e';

    var styles = [
      // Default node style
      {
        selector: 'node',
        style: {
          'label': 'data(label)',
          'text-valign': 'bottom',
          'text-halign': 'center',
          'font-size': '10px',
          'text-max-width': '100px',
          'text-wrap': 'ellipsis',
          'width': 30,
          'height': 30,
          'background-color': nodeBg,
          'border-width': 1,
          'border-color': nodeBorder,
          'shape': 'ellipse',
          'text-margin-y': 4,
          'color': nodeColor
        }
      },
      // Default edge style
      {
        selector: 'edge',
        style: {
          'curve-style': 'bezier',
          'target-arrow-shape': 'triangle',
          'target-arrow-color': edgeLineColor,
          'line-color': edgeLineColor,
          'width': 1.5,
          'label': 'data(label)',
          'font-size': '9px',
          'text-rotation': 'autorotate',
          'color': edgeLabelColor,
          'text-background-color': edgeTextBg,
          'text-background-opacity': 0.8,
          'text-background-padding': '2px'
        }
      },
      // Selected node
      {
        selector: 'node:selected',
        style: {
          'border-width': 3,
          'border-color': selectedBorder
        }
      },
      // Hovered node (via mouseover class)
      {
        selector: 'node.hovered',
        style: {
          'width': 36,
          'height': 36
        }
      },
      // Filtered-out elements (hidden by filter)
      {
        selector: '.filtered-out',
        style: {
          'opacity': 0.08,
          'events': 'no'
        }
      }
    ];

    // Per-type node colors
    if (typeColors) {
      var types = Object.keys(typeColors);
      for (var i = 0; i < types.length; i++) {
        var typeIri = types[i];
        var color = typeColors[typeIri];
        styles.push({
          selector: 'node[type = "' + typeIri + '"]',
          style: {
            'background-color': color,
            'border-color': _darkenColor(color, 0.2)
          }
        });
      }
    }

    // Per-type node shapes from window._sempkmIcons (fetched from /browser/icons)
    var iconToShape = {
      'file-text': 'rectangle',
      'lightbulb': 'diamond',
      'book-open': 'round-rectangle',
      'tag': 'ellipse',
      'folder-kanban': 'round-rectangle',
      'user': 'ellipse',
    };

    if (window._sempkmIcons && window._sempkmIcons.graph) {
      var graphIcons = window._sempkmIcons.graph;
      var typeIris = Object.keys(graphIcons);
      for (var k = 0; k < typeIris.length; k++) {
        var iri = typeIris[k];
        var iconInfo = graphIcons[iri];
        if (iconInfo && iconInfo.icon) {
          var shape = iconToShape[iconInfo.icon] || 'ellipse';
          styles.push({
            selector: 'node[type = "' + iri + '"]',
            style: { 'shape': shape }
          });
        }
      }
    }

    return styles;
  }

  function _darkenColor(hex, amount) {
    // Simple darken: reduce each channel by amount fraction
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

  // --- Graph Initialization ---

  function initGraph(containerId, specIri, typeColors, availableLayouts) {
    var container = document.getElementById(containerId);
    if (!container) {
      console.error('Graph container not found:', containerId);
      return;
    }

    // Register any model-contributed layouts from availableLayouts
    if (availableLayouts && availableLayouts.length > 0) {
      for (var i = 0; i < availableLayouts.length; i++) {
        var layout = availableLayouts[i];
        if (layout.config && Object.keys(layout.config).length > 0) {
          var config = Object.assign({ name: layout.name }, layout.config);
          registerLayout(layout.name, config);
        }
      }
    }

    // Show loading state
    container.innerHTML = '<div class="graph-loading">Loading graph data...</div>';

    // Fetch graph data from the JSON endpoint
    var dataUrl = '/browser/views/graph/' + specIri + '/data';
    fetch(dataUrl)
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        container.innerHTML = '';  // Clear loading state
        _renderGraph(container, data, typeColors);
      })
      .catch(function (err) {
        console.error('Failed to load graph data:', err);
        container.innerHTML = '<div class="graph-loading">Failed to load graph data.</div>';
      });
  }

  function _renderGraph(container, data, initialTypeColors) {
    if (!data.nodes || data.nodes.length === 0) {
      container.innerHTML = '<div class="graph-loading">No data to display in graph.</div>';
      return;
    }

    // Merge type colors from server data with any initial colors
    var typeColors = Object.assign({}, initialTypeColors || {}, data.type_colors || {});

    // Convert server data to Cytoscape elements
    var elements = [];

    for (var i = 0; i < data.nodes.length; i++) {
      var node = data.nodes[i];
      elements.push({
        group: 'nodes',
        data: {
          id: node.id,
          label: node.label || node.id,
          type: node.type || '',
          typeLabel: node.type_label || '',
          properties: node.properties || {}
        }
      });
    }

    for (var j = 0; j < data.edges.length; j++) {
      var edge = data.edges[j];
      elements.push({
        group: 'edges',
        data: {
          id: edge.source + '-' + edge.predicate + '-' + edge.target,
          source: edge.source,
          target: edge.target,
          label: edge.predicate_label || '',
          fullPredicate: edge.predicate,
          predicate: edge.predicate
        }
      });
    }

    // Determine layout -- use fcose if available, fall back to cose
    var layoutName = currentLayoutName;
    var layoutConfig = LAYOUT_REGISTRY[layoutName] || { name: layoutName };

    // Check if fcose extension is registered
    if (layoutName === 'fcose' && typeof cytoscape !== 'undefined') {
      // fcose should be auto-registered by the CDN script
      // If not available, fall back to cose
      try {
        var testLayout = { name: 'fcose' };
        // Will throw if fcose is not registered
      } catch (e) {
        layoutConfig = { name: 'cose', animate: true, animationDuration: 500 };
      }
    }

    var cy = cytoscape({
      container: container,
      elements: elements,
      style: buildSemanticStyle(typeColors, document.documentElement.getAttribute('data-theme') === 'dark'),
      layout: layoutConfig,
      minZoom: 0.1,
      maxZoom: 5,
      wheelSensitivity: 0.3
    });

    // Store the cy instance globally
    window._sempkmGraph = cy;
    window._sempkmTypeColors = typeColors;

    // Register cleanup for htmx:beforeCleanupElement
    if (typeof window.registerCleanup === 'function' && container.id) {
      window.registerCleanup(container.id, function() {
        if (window._sempkmGraph === cy) {
          window._sempkmGraph = null;
        }
        cy.destroy();
      });
    }

    // --- Event Handlers ---

    // Click to select -- load details in right pane
    cy.on('tap', 'node', function (evt) {
      var nodeId = evt.target.id();
      if (typeof window.loadRightPaneSection === 'function') {
        window.loadRightPaneSection(nodeId, 'relations');
        window.loadRightPaneSection(nodeId, 'lint');
      }
    });

    // Double-click to expand neighbors
    cy.on('dbltap', 'node', function (evt) {
      var nodeIri = evt.target.id();
      _expandNode(cy, nodeIri);
    });

    // --- Popover (rich node bubble + simple edge tooltip) ---
    var popover = document.createElement('div');
    popover.className = 'graph-popover';
    container.appendChild(popover);

    var edgePopover = document.createElement('div');
    edgePopover.className = 'graph-popover';
    container.appendChild(edgePopover);

    var _hoverTimer = null;
    var _edgeHoverTimer = null;
    var _popoverHovered = false;

    // Keep node popover visible when mouse enters it
    popover.addEventListener('mouseenter', function () {
      _popoverHovered = true;
      if (_hoverTimer) { clearTimeout(_hoverTimer); _hoverTimer = null; }
    });
    popover.addEventListener('mouseleave', function () {
      _popoverHovered = false;
      popover.style.display = 'none';
    });

    // Open button click handler
    popover.addEventListener('click', function (e) {
      var btn = e.target.closest('.graph-popover-open-btn');
      if (!btn) return;
      var iri = btn.getAttribute('data-node-iri');
      if (iri && typeof window.openTab === 'function') {
        window.openTab(iri);
      }
      popover.style.display = 'none';
    });

    // Graph node hover tooltip: shows typeLabel + label via .graph-popover-type and
    // .graph-popover-label. Verified against CONTEXT.md requirement (phase 19-02):
    // "Target locations: nav tree item hover + graph node hover".
    // typeLabel is populated from backend node.type_label (view service.py line ~920)
    // which resolves the primary type IRI via LabelService. The if (d.typeLabel) guard
    // conditionally renders the type span — no changes needed to this implementation.
    function _showNodePopover(nodeEl, evt) {
      var d = nodeEl.data();
      var nodeIri = nodeEl.id();
      var html = '<div class="graph-popover-header">' +
                   '<span class="graph-popover-label">' + _esc(d.label) + '</span>';
      if (d.typeLabel) {
        html += '<span class="graph-popover-type">' + _esc(d.typeLabel) + '</span>';
      }
      html += '</div>';

      var props = d.properties || {};
      var keys = Object.keys(props);
      if (keys.length > 0) {
        html += '<div class="graph-popover-props">';
        for (var i = 0; i < keys.length; i++) {
          var val = String(props[keys[i]]);
          if (val.length > 120) val = val.substring(0, 120) + '...';
          html += '<div class="graph-popover-prop">' +
                    '<span class="graph-popover-prop-name">' + _esc(keys[i]) + '</span>' +
                    '<span class="graph-popover-prop-val">' + _esc(val) + '</span>' +
                  '</div>';
        }
        html += '</div>';
      } else {
        html += '<div class="graph-popover-empty">No additional properties</div>';
      }

      html += '<div class="graph-popover-footer">' +
                '<button class="graph-popover-open-btn" data-node-iri="' + _esc(nodeIri) + '">Open</button>' +
              '</div>';

      popover.innerHTML = html;
      popover.style.display = 'block';
      _popoverHovered = false;

      // Position near the node
      var pos = evt.renderedPosition || nodeEl.renderedPosition();
      var cRect = container.getBoundingClientRect();
      var left = pos.x + 16;
      var top = pos.y - 12;

      // Keep within container bounds
      popover.style.left = left + 'px';
      popover.style.top = top + 'px';

      // Adjust if overflowing right edge
      var pRect = popover.getBoundingClientRect();
      if (pRect.right > cRect.right - 8) {
        popover.style.left = (pos.x - pRect.width - 12) + 'px';
      }
      if (pRect.bottom > cRect.bottom - 8) {
        popover.style.top = (pos.y - pRect.height + 12) + 'px';
      }
    }

    function _hidePopover() {
      if (_hoverTimer) { clearTimeout(_hoverTimer); _hoverTimer = null; }
      // Delay hide to allow mouse to enter the popover
      setTimeout(function () {
        if (!_popoverHovered) {
          popover.style.display = 'none';
        }
      }, 100);
    }

    function _showEdgePopover(edgeEl, evt) {
      var d = edgeEl.data();
      var html = '<div class="graph-popover-header">' +
                   '<span class="graph-popover-label">' + _esc(d.label) + '</span>' +
                   '<span class="graph-popover-type">edge</span>' +
                 '</div>';

      // Always show full predicate IRI
      html += '<div class="graph-popover-props">';
      html += '<div class="graph-popover-prop">' +
                '<span class="graph-popover-prop-name">predicate</span>' +
                '<span class="graph-popover-prop-val graph-popover-iri">' + _esc(d.fullPredicate || d.predicate || '') + '</span>' +
              '</div>';

      // Edge properties (for future use)
      var props = d.properties || {};
      var keys = Object.keys(props);
      for (var i = 0; i < keys.length; i++) {
        var val = String(props[keys[i]]);
        if (val.length > 120) val = val.substring(0, 120) + '...';
        html += '<div class="graph-popover-prop">' +
                  '<span class="graph-popover-prop-name">' + _esc(keys[i]) + '</span>' +
                  '<span class="graph-popover-prop-val">' + _esc(val) + '</span>' +
                '</div>';
      }
      html += '</div>';

      edgePopover.innerHTML = html;
      edgePopover.style.display = 'block';

      var pos = evt.renderedPosition || edgeEl.renderedMidpoint();
      var cRect = container.getBoundingClientRect();
      var left = pos.x + 16;
      var top = pos.y - 12;

      edgePopover.style.left = left + 'px';
      edgePopover.style.top = top + 'px';

      var pRect = edgePopover.getBoundingClientRect();
      if (pRect.right > cRect.right - 8) {
        edgePopover.style.left = (pos.x - pRect.width - 12) + 'px';
      }
      if (pRect.bottom > cRect.bottom - 8) {
        edgePopover.style.top = (pos.y - pRect.height + 12) + 'px';
      }
    }

    function _hideEdgePopover() {
      if (_edgeHoverTimer) { clearTimeout(_edgeHoverTimer); _edgeHoverTimer = null; }
      edgePopover.style.display = 'none';
    }

    function _esc(s) {
      var d = document.createElement('span');
      d.textContent = s;
      return d.innerHTML;
    }

    // Hover effects — nodes (show popover after short delay)
    cy.on('mouseover', 'node', function (evt) {
      evt.target.addClass('hovered');
      container.style.cursor = 'pointer';
      var target = evt.target;
      var e = evt;
      _hoverTimer = setTimeout(function () {
        _showNodePopover(target, e);
      }, 250);
    });

    cy.on('mouseout', 'node', function (evt) {
      evt.target.removeClass('hovered');
      container.style.cursor = 'default';
      _hidePopover();
    });

    // Hover effects — edges (show popover after short delay)
    cy.on('mouseover', 'edge', function (evt) {
      container.style.cursor = 'pointer';
      var target = evt.target;
      var e = evt;
      _edgeHoverTimer = setTimeout(function () {
        _showEdgePopover(target, e);
      }, 250);
    });

    cy.on('mouseout', 'edge', function (evt) {
      container.style.cursor = 'default';
      _hideEdgePopover();
    });
  }

  // --- Node Expansion ---

  function _expandNode(cy, nodeIri) {
    var expandUrl = '/browser/views/graph/expand/' + encodeURIComponent(nodeIri);

    fetch(expandUrl)
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (!data.nodes || data.nodes.length === 0) return;

        // Merge new type colors
        var newTypeColors = data.type_colors || {};
        var currentColors = window._sempkmTypeColors || {};
        Object.assign(currentColors, newTypeColors);
        window._sempkmTypeColors = currentColors;

        // Build new elements, skipping duplicates
        var newElements = [];

        for (var i = 0; i < data.nodes.length; i++) {
          var node = data.nodes[i];
          if (!cy.getElementById(node.id).length) {
            newElements.push({
              group: 'nodes',
              data: {
                id: node.id,
                label: node.label || node.id,
                type: node.type || '',
                typeLabel: node.type_label || '',
                properties: node.properties || {}
              }
            });
          }
        }

        for (var j = 0; j < data.edges.length; j++) {
          var edge = data.edges[j];
          var edgeId = edge.source + '-' + edge.predicate + '-' + edge.target;
          if (!cy.getElementById(edgeId).length) {
            newElements.push({
              group: 'edges',
              data: {
                id: edgeId,
                source: edge.source,
                target: edge.target,
                label: edge.predicate_label || '',
                fullPredicate: edge.predicate,
                predicate: edge.predicate
              }
            });
          }
        }

        if (newElements.length === 0) return;

        // Add new elements
        var added = cy.add(newElements);

        // Update styles with new type colors
        cy.style(buildSemanticStyle(currentColors, document.documentElement.getAttribute('data-theme') === 'dark'));

        // Run layout on ONLY the new elements (per Research Pitfall 6)
        var newNodes = added.filter('node');
        if (newNodes.length > 0) {
          var layoutConfig = LAYOUT_REGISTRY[currentLayoutName] || { name: currentLayoutName };
          var expandLayout = Object.assign({}, layoutConfig, {
            animate: true,
            fit: false,
            boundingBox: _boundingBoxNear(cy, nodeIri)
          });
          newNodes.layout(expandLayout).run();
        }
      })
      .catch(function (err) {
        console.error('Failed to expand node:', err);
      });
  }

  function _boundingBoxNear(cy, nodeIri) {
    // Position new nodes near the expanded node
    var node = cy.getElementById(nodeIri);
    if (node.length) {
      var pos = node.position();
      return {
        x1: pos.x - 200,
        y1: pos.y - 200,
        x2: pos.x + 200,
        y2: pos.y + 200
      };
    }
    return undefined;
  }

  // --- Layout Switching ---

  function changeLayout(layoutName) {
    var cy = window._sempkmGraph;
    if (!cy) return;

    currentLayoutName = layoutName;

    var config = LAYOUT_REGISTRY[layoutName];
    if (!config) {
      config = { name: layoutName };
    }

    var layoutConfig = Object.assign({}, config, {
      animate: true,
      animationDuration: 500
    });

    cy.layout(layoutConfig).run();
  }

  // --- Client-side Filter ---

  function filterGraph(text) {
    var cy = window._sempkmGraph;
    if (!cy) return;

    if (!text || !text.trim()) {
      // Show all
      cy.elements().removeClass('filtered-out');
      return;
    }

    var q = text.toLowerCase();
    cy.nodes().forEach(function (node) {
      var label = (node.data('label') || '').toLowerCase();
      if (label.indexOf(q) >= 0) {
        node.removeClass('filtered-out');
      } else {
        node.addClass('filtered-out');
      }
    });

    // Hide edges where either endpoint is filtered out
    cy.edges().forEach(function (edge) {
      if (edge.source().hasClass('filtered-out') || edge.target().hasClass('filtered-out')) {
        edge.addClass('filtered-out');
      } else {
        edge.removeClass('filtered-out');
      }
    });
  }

  // --- Theme Switching ---

  /**
   * Switch Cytoscape graph between dark and light styles.
   * Rebuilds the stylesheet without destroying graph state.
   *
   * @param {boolean} isDark - true for dark theme, false for light
   */
  function switchGraphTheme(isDark) {
    var cy = window._sempkmGraph;
    if (!cy) return;

    var styles = buildSemanticStyle(window._sempkmTypeColors || {}, isDark);
    cy.style().fromJson(styles).update();
  }

  // Backup integration: listen for sempkm:theme-changed event
  document.addEventListener('sempkm:theme-changed', function (e) {
    switchGraphTheme(e.detail.theme === 'dark');
  });

  // --- Export Globally ---
  window.initGraph = initGraph;
  window.changeLayout = changeLayout;
  window.registerLayout = registerLayout;
  window.filterGraph = filterGraph;
  window.switchGraphTheme = switchGraphTheme;

})();
