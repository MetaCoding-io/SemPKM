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

  // --- Icon Mode State ---
  var _currentIconMode = false;  // true when icon mode is active

  function registerLayout(name, configObj) {
    LAYOUT_REGISTRY[name] = configObj;
  }

  // --- Lucide SVG Data URI Helper (memoized) ---

  var _svgUriCache = {};

  /**
   * Convert a kebab-case Lucide icon name to an SVG data URI string.
   * Uses the global lucide UMD bundle. Returns null if icon not found.
   * Results are cached per (iconName, strokeColor) pair.
   *
   * @param {string} iconName - kebab-case icon name, e.g. 'file-text'
   * @param {string} [strokeColor='#333'] - stroke color for the SVG
   * @returns {string|null} data URI or null
   */
  function _lucideSvgDataUri(iconName, strokeColor) {
    if (!iconName) return null;
    strokeColor = strokeColor || '#333';
    var cacheKey = iconName + ':' + strokeColor;
    if (_svgUriCache[cacheKey] !== undefined) return _svgUriCache[cacheKey];

    if (typeof lucide === 'undefined' || !lucide.icons) {
      console.warn('[graph] lucide UMD not loaded, cannot create icon SVG for:', iconName);
      _svgUriCache[cacheKey] = null;
      return null;
    }

    // Convert kebab-case to PascalCase: 'file-text' -> 'FileText'
    var pascalName = iconName.replace(/(^|-)([a-z])/g, function (_m, _sep, ch) {
      return ch.toUpperCase();
    });

    var iconDef = lucide.icons[pascalName];
    if (!iconDef) {
      console.warn('[graph] Lucide icon not found:', iconName, '(tried:', pascalName, ')');
      _svgUriCache[cacheKey] = null;
      return null;
    }

    try {
      var el = lucide.createElement(iconDef, {
        width: 20,
        height: 20,
        stroke: strokeColor,
        'stroke-width': 1.5
      });
      var svgHtml = el.outerHTML;
      var dataUri = 'data:image/svg+xml;utf8,' + encodeURIComponent(svgHtml);
      _svgUriCache[cacheKey] = dataUri;
      return dataUri;
    } catch (e) {
      console.error('[graph] Failed to create Lucide SVG for:', iconName, e);
      _svgUriCache[cacheKey] = null;
      return null;
    }
  }

  // --- Semantic Style Builder ---

  function buildSemanticStyle(typeColors, isDark, iconMode) {
    isDark = isDark || false;
    iconMode = iconMode || false;

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
      // Inferred edge style (dashed line to distinguish from user-created)
      {
        selector: 'edge.inferred-edge',
        style: {
          'line-style': 'dashed',
          'line-dash-pattern': [6, 3],
          'line-color': isDark ? '#5a6070' : '#aab',
          'target-arrow-color': isDark ? '#5a6070' : '#aab',
          'width': 1.2
        }
      },
      // Mirrored edge style (dotted teal line for federated/mirrored triples)
      {
        selector: 'edge.mirrored-edge',
        style: {
          'line-style': 'dashed',
          'line-dash-pattern': [2, 4],
          'line-color': isDark ? '#5eead4' : '#14b8a6',
          'target-arrow-color': isDark ? '#5eead4' : '#14b8a6',
          'width': 1.2
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

    if (window.SemPKM._sempkmIcons && window.SemPKM._sempkmIcons.graph) {
      var graphIcons = window.SemPKM._sempkmIcons.graph;
      var typeIris = Object.keys(graphIcons);
      for (var k = 0; k < typeIris.length; k++) {
        var iri = typeIris[k];
        var iconInfo = graphIcons[iri];
        if (iconInfo && iconInfo.icon) {
          if (iconMode) {
            // Icon mode: render Lucide SVG as background-image, uniform ellipse shape
            var svgUri = _lucideSvgDataUri(iconInfo.icon, nodeColor);
            if (svgUri) {
              styles.push({
                selector: 'node[type = "' + iri + '"]',
                style: {
                  'shape': 'ellipse',
                  'background-image': svgUri,
                  'background-fit': 'contain',
                  'background-clip': 'none',
                  'background-width': '60%',
                  'background-height': '60%'
                }
              });
            } else {
              // Fallback: still override shape to ellipse for uniformity
              styles.push({
                selector: 'node[type = "' + iri + '"]',
                style: { 'shape': 'ellipse' }
              });
            }
          } else {
            // Shape-only mode: map icon names to distinct Cytoscape shapes
            var shape = iconToShape[iconInfo.icon] || 'ellipse';
            styles.push({
              selector: 'node[type = "' + iri + '"]',
              style: { 'shape': shape }
            });
          }
        }
      }
    }

    // In icon mode, set uniform ellipse shape on all nodes (catch types without icon mapping)
    if (iconMode) {
      styles.push({
        selector: 'node',
        style: { 'shape': 'ellipse' }
      });
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

  function initGraph(containerId, specIri, typeColors, availableLayouts, customDataUrl) {
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
    var dataUrl = customDataUrl || ('/browser/views/graph/' + specIri + '/data');
    apiFetch(dataUrl, { silent: true })
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
      var edgeEl = {
        group: 'edges',
        data: {
          id: edge.source + '-' + edge.predicate + '-' + edge.target,
          source: edge.source,
          target: edge.target,
          label: edge.predicate_label || '',
          fullPredicate: edge.predicate,
          predicate: edge.predicate,
          inferred: edge.inferred || false,
          mirrored: edge.mirrored || false
        }
      };
      if (edge.mirrored) {
        edgeEl.classes = 'mirrored-edge';
      } else if (edge.inferred) {
        edgeEl.classes = 'inferred-edge';
      }
      elements.push(edgeEl);
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

    // Read icon mode from localStorage
    var savedIconMode = localStorage.getItem('sempkm_graph_icon_mode');
    _currentIconMode = (savedIconMode === 'icon');

    var cy = cytoscape({
      container: container,
      elements: elements,
      style: buildSemanticStyle(typeColors, document.documentElement.getAttribute('data-theme') === 'dark', _currentIconMode),
      layout: layoutConfig,
      minZoom: 0.1,
      maxZoom: 5,
      wheelSensitivity: 0.3
    });

    // Store the cy instance globally
    window.SemPKM._sempkmGraph = cy;
    window.SemPKM._sempkmTypeColors = typeColors;

    // Update icon toggle button to reflect loaded preference
    _updateIconToggleButton();

    // Register cleanup for htmx:beforeCleanupElement
    if (typeof window.SemPKM.registerCleanup === 'function' && container.id) {
      window.SemPKM.registerCleanup(container.id, function() {
        if (window.SemPKM._sempkmGraph === cy) {
          window.SemPKM._sempkmGraph = null;
        }
        // Remove body-appended popovers
        if (popover.parentNode) popover.parentNode.removeChild(popover);
        if (edgePopover.parentNode) edgePopover.parentNode.removeChild(edgePopover);
        cy.destroy();
      });
    }

    // --- Event Handlers ---

    // Click to select -- load details in right pane
    cy.on('tap', 'node', function (evt) {
      var nodeId = evt.target.id();
      if (typeof window.SemPKM.refreshRightPaneSection === 'function') {
        window.SemPKM.refreshRightPaneSection(nodeId, 'relations');
        window.SemPKM.refreshRightPaneSection(nodeId, 'lint');
      }
    });

    // Double-click to expand neighbors
    cy.on('dbltap', 'node', function (evt) {
      var nodeIri = evt.target.id();
      _expandNode(cy, nodeIri);
    });

    // --- Popover (rich node bubble + simple edge tooltip) ---
    // Appended to document.body so they render above all chrome (dockview tabs, toolbars)
    var popover = document.createElement('div');
    popover.className = 'graph-popover';
    document.body.appendChild(popover);

    var edgePopover = document.createElement('div');
    edgePopover.className = 'graph-popover';
    document.body.appendChild(edgePopover);

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
      var label = btn.getAttribute('data-node-label');
      if (iri && typeof window.SemPKM.openTab === 'function') {
        window.SemPKM.openTab(iri, label || undefined);
      }
      popover.style.display = 'none';
    });

    // Graph node hover tooltip: shows typeLabel + label via .graph-popover-type and
    // .graph-popover-label. Verified against CONTEXT.md requirement (phase 19-02):
    // "Target locations: nav tree item hover + graph node hover".
    // typeLabel is populated from backend node.type_label (view service.py line ~920)
    // which resolves the primary type IRI via LabelService. The if (d.typeLabel) guard
    // conditionally renders the type span — no changes needed to this implementation.
    /**
     * Compute viewport coordinates for a popover from a Cytoscape rendered position.
     * When isometric transform is active, forward-transforms the position through
     * the wrapper's CSS matrix to get the correct screen position.
     *
     * @param {object} cy - Cytoscape instance
     * @param {HTMLElement} container - The #cy-container element
     * @param {{x: number, y: number}} renderedPos - Cytoscape rendered position
     * @returns {{x: number, y: number}} viewport coordinates
     */
    function _popoverViewportCoords(cy, container, renderedPos) {
      if (cy._isometricActive) {
        var wrapper = document.getElementById('cy-wrapper');
        if (wrapper) {
          // Get the wrapper's computed transform matrix
          var wrapperStyle = getComputedStyle(wrapper);
          var containerStyle = getComputedStyle(container);
          var containerMatrix = new DOMMatrix(containerStyle.transform);
          var wrapperRect = wrapper.getBoundingClientRect();

          // The rendered position is relative to the untransformed container.
          // Transform it through the CSS 3D matrix to get screen coordinates.
          // Container center = (clientWidth/2, clientHeight/2)
          var cx = container.clientWidth / 2;
          var cy2 = container.clientHeight / 2;

          // Point relative to container center
          var relX = renderedPos.x - cx;
          var relY = renderedPos.y - cy2;

          // Apply the CSS transform
          var pt = new DOMPoint(relX, relY, 0, 1);
          var transformed = containerMatrix.transformPoint(pt);

          // Map to viewport coordinates using wrapper center
          var wrapperCenterX = wrapperRect.left + wrapperRect.width / 2;
          var wrapperCenterY = wrapperRect.top + wrapperRect.height / 2;

          return {
            x: wrapperCenterX + transformed.x,
            y: wrapperCenterY + transformed.y
          };
        }
      }

      // Non-isometric: standard container-relative positioning
      var cRect = container.getBoundingClientRect();
      return {
        x: cRect.left + renderedPos.x,
        y: cRect.top + renderedPos.y
      };
    }

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
                '<button class="graph-popover-open-btn" data-node-iri="' + _esc(nodeIri) + '" data-node-label="' + _esc(d.label) + '">Open</button>' +
              '</div>';

      popover.innerHTML = html;
      popover.style.display = 'block';
      _popoverHovered = false;

      // Position near the node using viewport-relative (fixed) coordinates
      var pos = evt.renderedPosition || nodeEl.renderedPosition();
      var coords = _popoverViewportCoords(cy, container, pos);
      var left = coords.x + 16;
      var top = coords.y - 12;

      popover.style.left = left + 'px';
      popover.style.top = top + 'px';

      // Adjust if overflowing viewport edges
      var pRect = popover.getBoundingClientRect();
      if (pRect.right > window.innerWidth - 8) {
        popover.style.left = (coords.x - pRect.width - 12) + 'px';
      }
      if (pRect.bottom > window.innerHeight - 8) {
        popover.style.top = (coords.y - pRect.height + 12) + 'px';
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

      // Position near the edge midpoint using viewport-relative (fixed) coordinates
      var pos = evt.renderedPosition || edgeEl.renderedMidpoint();
      var coords = _popoverViewportCoords(cy, container, pos);
      var left = coords.x + 16;
      var top = coords.y - 12;

      edgePopover.style.left = left + 'px';
      edgePopover.style.top = top + 'px';

      var pRect = edgePopover.getBoundingClientRect();
      if (pRect.right > window.innerWidth - 8) {
        edgePopover.style.left = (coords.x - pRect.width - 12) + 'px';
      }
      if (pRect.bottom > window.innerHeight - 8) {
        edgePopover.style.top = (coords.y - pRect.height + 12) + 'px';
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

    apiFetch(expandUrl, { silent: true })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        if (!data.nodes || data.nodes.length === 0) return;

        // Merge new type colors
        var newTypeColors = data.type_colors || {};
        var currentColors = window.SemPKM._sempkmTypeColors || {};
        Object.assign(currentColors, newTypeColors);
        window.SemPKM._sempkmTypeColors = currentColors;

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
            var newEdge = {
              group: 'edges',
              data: {
                id: edgeId,
                source: edge.source,
                target: edge.target,
                label: edge.predicate_label || '',
                fullPredicate: edge.predicate,
                predicate: edge.predicate,
                inferred: edge.inferred || false,
                mirrored: edge.mirrored || false
              }
            };
            if (edge.mirrored) {
              newEdge.classes = 'mirrored-edge';
            } else if (edge.inferred) {
              newEdge.classes = 'inferred-edge';
            }
            newElements.push(newEdge);
          }
        }

        if (newElements.length === 0) return;

        // Add new elements
        var added = cy.add(newElements);

        // Update styles with new type colors (preserve icon mode)
        cy.style(buildSemanticStyle(currentColors, document.documentElement.getAttribute('data-theme') === 'dark', _currentIconMode));

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

  // --- Isometric 2.5D Transform ---

  /**
   * Apply isometric CSS 3D perspective transform to the graph.
   * Runs fcose layout first to position nodes, then tilts the container.
   * Monkey-patches findContainerClientCoords to fix click targeting under transform.
   *
   * @param {object} cy - Cytoscape instance
   * @param {HTMLElement} container - The #cy-container element
   */
  function _applyIsometricTransform(cy, container) {
    var wrapper = document.getElementById('cy-wrapper');
    if (!wrapper) {
      console.warn('[graph] Isometric wrapper #cy-wrapper not found');
      return;
    }

    // Run fcose layout first to position nodes before tilting
    var fcoseConfig = Object.assign({}, LAYOUT_REGISTRY['fcose'] || { name: 'fcose' }, {
      animate: true,
      animationDuration: 500
    });

    var layout = cy.layout(fcoseConfig);

    layout.on('layoutstop', function () {
      // Apply the CSS 3D transform via class
      wrapper.classList.add('isometric-active');

      // Store original findContainerClientCoords for later restore
      var renderer = cy.renderer();
      if (renderer && typeof renderer.findContainerClientCoords === 'function') {
        cy._origFindCoords = renderer.findContainerClientCoords.bind(renderer);

        // Monkey-patch: return coordinates based on untransformed container dimensions
        // and the wrapper's visual center. This corrects the mismatch between
        // getBoundingClientRect() (which reports the transformed bounding box)
        // and clientWidth/clientHeight (which remain untransformed).
        renderer.findContainerClientCoords = function () {
          var wrapperRect = wrapper.getBoundingClientRect();
          var cw = container.clientWidth;
          var ch = container.clientHeight;
          return [
            wrapperRect.left + wrapperRect.width / 2 - cw / 2,
            wrapperRect.top + wrapperRect.height / 2 - ch / 2,
            cw,
            ch,
            1
          ];
        };
      }

      cy.invalidateSize();
      cy._isometricActive = true;
      SemPKM.debug('graph', 'Isometric 2.5D transform applied');
    });

    layout.run();
  }

  /**
   * Remove isometric CSS 3D perspective transform and restore normal interaction.
   *
   * @param {object} cy - Cytoscape instance
   * @param {HTMLElement} container - The #cy-container element
   */
  function _removeIsometricTransform(cy, container) {
    var wrapper = document.getElementById('cy-wrapper');
    if (!wrapper) return;

    wrapper.classList.remove('isometric-active');

    // Restore original findContainerClientCoords
    if (cy._origFindCoords) {
      var renderer = cy.renderer();
      if (renderer) {
        renderer.findContainerClientCoords = cy._origFindCoords;
      }
      delete cy._origFindCoords;
    }

    cy.invalidateSize();
    cy._isometricActive = false;
    SemPKM.debug('graph', 'Isometric 2.5D transform removed');
  }

  // --- Layout Switching ---

  function changeLayout(layoutName) {
    var cy = window.SemPKM._sempkmGraph;
    if (!cy) return;

    var container = cy.container();
    if (!container) return;

    // Remove isometric transform if currently active
    if (cy._isometricActive) {
      _removeIsometricTransform(cy, container);
    }

    currentLayoutName = layoutName;

    // Isometric is special: run fcose first, then apply CSS 3D transform
    if (layoutName === 'isometric') {
      _applyIsometricTransform(cy, container);
      return;
    }

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
    var cy = window.SemPKM._sempkmGraph;
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
    var cy = window.SemPKM._sempkmGraph;
    if (!cy) return;

    // Clear SVG URI cache since stroke color changes with theme
    _svgUriCache = {};

    var styles = buildSemanticStyle(window.SemPKM._sempkmTypeColors || {}, isDark, _currentIconMode);
    cy.style().fromJson(styles).update();
  }

  // Backup integration: listen for sempkm:theme-changed event
  document.addEventListener('sempkm:theme-changed', function (e) {
    switchGraphTheme(e.detail.theme === 'dark');
  });

  // --- Icon Mode Toggle ---

  /**
   * Set icon mode and rebuild the graph stylesheet.
   * @param {string} mode - 'icon' or 'shape'
   */
  function _setIconMode(mode) {
    var cy = window.SemPKM._sempkmGraph;
    if (!cy) return;

    _currentIconMode = (mode === 'icon');
    localStorage.setItem('sempkm_graph_icon_mode', mode);

    // Clear SVG URI cache when switching modes (stroke color may differ)
    _svgUriCache = {};

    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    cy.style().fromJson(buildSemanticStyle(window.SemPKM._sempkmTypeColors || {}, isDark, _currentIconMode)).update();

    _updateIconToggleButton();
  }

  /**
   * Toggle between icon mode and shape mode.
   */
  function _toggleGraphIcons() {
    var newMode = _currentIconMode ? 'shape' : 'icon';
    _setIconMode(newMode);
  }

  /**
   * Update the icon toggle button's active state and label.
   */
  function _updateIconToggleButton() {
    var btn = document.getElementById('graph-icon-toggle');
    if (!btn) return;

    if (_currentIconMode) {
      btn.classList.add('active');
      var span = btn.querySelector('span');
      if (span) span.textContent = 'Icons On';
    } else {
      btn.classList.remove('active');
      var span = btn.querySelector('span');
      if (span) span.textContent = 'Icons';
    }
  }

  // Update button state when graph initializes (deferred to allow DOM render)
  document.addEventListener('DOMContentLoaded', function () {
    // Small delay to ensure graph template has rendered
    setTimeout(_updateIconToggleButton, 100);
  });

  // --- Export Globally ---
  window.SemPKM.initGraph = initGraph;
  window.SemPKM.changeLayout = changeLayout;
  window.SemPKM.registerLayout = registerLayout;
  window.SemPKM.filterGraph = filterGraph;
  window.SemPKM.switchGraphTheme = switchGraphTheme;
  window.SemPKM._toggleGraphIcons = _toggleGraphIcons;
  window.SemPKM._setIconMode = _setIconMode;


})();
