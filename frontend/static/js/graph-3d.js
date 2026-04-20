/**
 * SemPKM 3D Graph Visualization
 *
 * Wraps the 3d-force-graph (Three.js / WebGL) library. The data endpoint
 * returns the same {nodes, edges, type_colors} shape that the 2D Cytoscape
 * view consumes — this module renames `edges` → `links` before handing off
 * to ForceGraph3D. RDF label precedence, type colors, and inferred/mirrored
 * edge semantics are resolved server-side in _parse_graph_results().
 *
 * The 3d-force-graph UMD bundle (which bundles three.js + three-spritetext
 * + d3-force-3d) is loaded lazily from CDN inside graph_3d_view.html — it
 * is NOT loaded globally from base.html, so users who never open a 3D view
 * pay no cost.
 */

(function () {
  'use strict';

  var currentLayoutName = 'd3-force-3d';
  var _typeColors = {};
  var _allNodes = [];
  var _allLinks = [];

  // --- Deterministic fallback color for types without a declared nodeColor ---

  var _FALLBACK_PALETTE = [
    '#4e79a7', '#f28e2c', '#e15759', '#76b7b2', '#59a14f',
    '#edc949', '#af7aa1', '#ff9da7', '#9c755f', '#bab0ab'
  ];

  function _colorForType(typeIri) {
    if (!typeIri) return _FALLBACK_PALETTE[0];
    var h = 0;
    for (var i = 0; i < typeIri.length; i++) {
      h = ((h << 5) - h) + typeIri.charCodeAt(i);
      h |= 0;
    }
    return _FALLBACK_PALETTE[Math.abs(h) % _FALLBACK_PALETTE.length];
  }

  function _nodeColor(node) {
    var t = node.type || (node.types && node.types[0]) || '';
    return _typeColors[t] || _colorForType(t);
  }

  // --- Graph Initialization ---

  function initGraph3D(containerId, specIri, typeColors, availableLayouts, customDataUrl) {
    var container = document.getElementById(containerId);
    if (!container) {
      console.error('[graph-3d] container not found:', containerId);
      return;
    }

    if (typeof ForceGraph3D === 'undefined') {
      console.error('[graph-3d] ForceGraph3D global missing — CDN script not loaded');
      container.innerHTML = '<div class="graph-loading">3D graph library failed to load.</div>';
      return;
    }

    _typeColors = typeColors || {};

    container.innerHTML = '<div class="graph-loading">Loading 3D graph data...</div>';

    var dataUrl = customDataUrl || ('/browser/views/graph-3d/' + specIri + '/data');
    fetch(dataUrl, { credentials: 'include' })
      .then(function (resp) { return resp.json(); })
      .then(function (data) {
        container.innerHTML = '';
        _renderGraph3D(container, data);
      })
      .catch(function (err) {
        console.error('[graph-3d] failed to load graph data:', err);
        container.innerHTML = '<div class="graph-loading">Failed to load 3D graph data.</div>';
      });
  }

  function _renderGraph3D(container, data) {
    if (!data.nodes || data.nodes.length === 0) {
      container.innerHTML = '<div class="graph-loading">No data to display.</div>';
      return;
    }

    // Merge server-provided type_colors with any caller-provided ones
    _typeColors = Object.assign({}, _typeColors, data.type_colors || {});

    // 3d-force-graph expects {nodes, links} — our server returns {nodes, edges}
    _allNodes = data.nodes.slice();
    _allLinks = (data.edges || []).map(function (e) {
      return {
        source: e.source,
        target: e.target,
        predicate: e.predicate,
        predicate_label: e.predicate_label || '',
        inferred: !!e.inferred,
        mirrored: !!e.mirrored
      };
    });

    var isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var bgColor = isDark ? '#1e2127' : '#f5f5f5';

    // 3d-force-graph factory form is the documented / widest-compatible API.
    var fg;
    try {
      fg = ForceGraph3D()(container);
    } catch (e) {
      try { fg = new ForceGraph3D(container); }
      catch (e2) {
        console.error('[graph-3d] failed to instantiate ForceGraph3D:', e, e2);
        container.innerHTML = '<div class="graph-loading">Could not initialize 3D renderer.</div>';
        return;
      }
    }

    fg
      .graphData({ nodes: _allNodes, links: _allLinks })
      .backgroundColor(bgColor)
      .nodeId('id')
      .nodeLabel(function (n) {
        // Hover tooltip — HTML allowed
        var label = n.label || n.id;
        var typeLabel = n.type_label || n.type || '';
        return '<div style="padding:4px 8px;font-family:sans-serif;font-size:12px;">'
          + '<strong>' + _escape(label) + '</strong>'
          + (typeLabel ? '<br/><span style="opacity:.7">' + _escape(typeLabel) + '</span>' : '')
          + '</div>';
      })
      .nodeColor(_nodeColor)
      .nodeOpacity(0.92)
      .nodeRelSize(5)
      .nodeThreeObjectExtend(true)
      .nodeThreeObject(function (n) {
        // Persistent in-scene text label via three-spritetext (bundled with UMD)
        if (typeof SpriteText === 'undefined') return null;
        var sprite = new SpriteText(n.label || n.id);
        sprite.color = isDark ? '#e6e6e6' : '#222';
        sprite.textHeight = 3;
        sprite.position.y = 7;
        return sprite;
      })
      .linkColor(function (l) {
        if (l.mirrored) return isDark ? '#56b6c2' : '#2a9d8f';
        if (l.inferred) return isDark ? '#7d8799' : '#aaa';
        return isDark ? '#4a4f57' : '#bbb';
      })
      .linkOpacity(0.55)
      .linkWidth(function (l) { return l.mirrored ? 1.5 : 1.0; })
      .linkDirectionalArrowLength(3)
      .linkDirectionalArrowRelPos(1)
      .linkDirectionalParticles(function (l) { return l.mirrored ? 2 : 0; })
      .linkDirectionalParticleSpeed(0.004)
      .onNodeClick(function (n) {
        if (typeof window.loadRightPaneSection === 'function') {
          window.loadRightPaneSection(n.id, 'relations');
          window.loadRightPaneSection(n.id, 'lint');
        }
      })
      .onNodeRightClick(function (n) {
        // Double-click / right-click = expand neighbors (future: wire to /graph/expand)
        _expandNode3D(n.id);
      });

    _applyLayoutPhysics(fg, currentLayoutName);

    window._sempkmGraph3D = fg;
    window._sempkmTypeColors3D = _typeColors;

    // Resize observer so the canvas follows its container
    if (typeof ResizeObserver !== 'undefined') {
      var ro = new ResizeObserver(function () {
        fg.width(container.clientWidth).height(container.clientHeight);
      });
      ro.observe(container);
      fg._sempkmResizeObserver = ro;
    }

    if (typeof window.registerCleanup === 'function' && container.id) {
      window.registerCleanup(container.id, function () {
        if (fg._sempkmResizeObserver) fg._sempkmResizeObserver.disconnect();
        if (window._sempkmGraph3D === fg) window._sempkmGraph3D = null;
        try { fg._destructor && fg._destructor(); } catch (e) { /* noop */ }
      });
    }
  }

  function _expandNode3D(nodeIri) {
    var fg = window._sempkmGraph3D;
    if (!fg) return;
    fetch('/browser/views/graph/expand/' + encodeURIComponent(nodeIri), { credentials: 'include' })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data || !data.nodes) return;
        var known = {};
        _allNodes.forEach(function (n) { known[n.id] = true; });
        data.nodes.forEach(function (n) {
          if (!known[n.id]) {
            _allNodes.push(n);
            known[n.id] = true;
          }
        });
        (data.edges || []).forEach(function (e) {
          _allLinks.push({
            source: e.source,
            target: e.target,
            predicate: e.predicate,
            predicate_label: e.predicate_label || '',
            inferred: !!e.inferred,
            mirrored: !!e.mirrored
          });
        });
        _typeColors = Object.assign({}, _typeColors, data.type_colors || {});
        fg.graphData({ nodes: _allNodes, links: _allLinks });
      })
      .catch(function (err) {
        console.warn('[graph-3d] expand failed:', err);
      });
  }

  // --- Layout / Physics Switching ---

  function _applyLayoutPhysics(fg, layoutName) {
    // 3d-force-graph supports two built-in engines: d3 (default) and ngraph.
    // The library doesn't allow engine swap after instantiation, so "ngraph"
    // tunes d3 forces to produce a tighter, less spread layout instead of a
    // full engine swap. A true engine swap would require rebuilding fg.
    if (layoutName === 'ngraph') {
      if (fg.d3Force) {
        if (fg.d3Force('charge')) fg.d3Force('charge').strength(-40);
        if (fg.d3Force('link')) fg.d3Force('link').distance(30);
      }
    } else {
      if (fg.d3Force) {
        if (fg.d3Force('charge')) fg.d3Force('charge').strength(-90);
        if (fg.d3Force('link')) fg.d3Force('link').distance(60);
      }
    }
    if (fg.d3ReheatSimulation) fg.d3ReheatSimulation();
  }

  function changeLayout3D(layoutName) {
    var fg = window._sempkmGraph3D;
    if (!fg) return;
    currentLayoutName = layoutName;
    _applyLayoutPhysics(fg, layoutName);
  }

  // --- Client-side Filter ---

  function filterGraph3D(text) {
    var fg = window._sempkmGraph3D;
    if (!fg) return;
    var q = (text || '').trim().toLowerCase();

    if (!q) {
      fg.nodeVisibility(function () { return true; });
      fg.linkVisibility(function () { return true; });
      return;
    }

    var matching = {};
    _allNodes.forEach(function (n) {
      var label = (n.label || n.id || '').toLowerCase();
      if (label.indexOf(q) >= 0) matching[n.id] = true;
    });

    fg.nodeVisibility(function (n) { return !!matching[n.id]; });
    fg.linkVisibility(function (l) {
      var src = (typeof l.source === 'object') ? l.source.id : l.source;
      var tgt = (typeof l.target === 'object') ? l.target.id : l.target;
      return !!matching[src] && !!matching[tgt];
    });
  }

  // --- Theme Switching ---

  function switchGraph3DTheme(isDark) {
    var fg = window._sempkmGraph3D;
    if (!fg) return;
    fg.backgroundColor(isDark ? '#1e2127' : '#f5f5f5');
    // Trigger a re-render of link colors (re-binds the accessor lazily on draw)
    fg.linkColor(fg.linkColor());
  }

  document.addEventListener('sempkm:theme-changed', function (e) {
    switchGraph3DTheme(e.detail && e.detail.theme === 'dark');
  });

  // --- Utilities ---

  function _escape(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  // --- Export Globally ---
  window.initGraph3D = initGraph3D;
  window.changeLayout3D = changeLayout3D;
  window.filterGraph3D = filterGraph3D;
  window.switchGraph3DTheme = switchGraph3DTheme;
})();
