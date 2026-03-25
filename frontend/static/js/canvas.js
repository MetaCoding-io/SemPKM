/**
 * SemPKM Spatial Canvas (C0 slice)
 *
 * Lightweight canvas prototype with pan/zoom and draggable resource cards.
 * This is intentionally framework-free as a bridge until the React Flow
 * island (Track A) lands.
 */
(function () {
  'use strict';

  var state = {
    mounted: false,
    scale: 1,
    minScale: 0.3,
    maxScale: 2.5,
    translateX: 0,
    translateY: 0,
    isPanning: false,
    panStartX: 0,
    panStartY: 0,
    nodeDragId: null,
    nodeDragOffsetX: 0,
    nodeDragOffsetY: 0,
    resizingNodeId: null,
    resizeStartX: 0,
    resizeStartY: 0,
    resizeStartWidth: 0,
    resizeStartHeight: 0,
    resizeHandleType: null, // 'corner', 'right', 'bottom'
    nodes: [],
    edges: [],
    expandProvenance: {},
    canvasId: 'default',
    isSaving: false,
    currentSessionId: null,
    selectedNodeId: null,
    propertyCache: {}
  };

  // Inline SVG icons — avoid Lucide re-scan on every renderNodes() call
  var SVG_CHEVRON = '<svg class="spatial-icon spatial-icon-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>';
  var SVG_PLUS = '<svg class="spatial-icon spatial-icon-plus" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>';
  var SVG_X = '<svg class="spatial-icon spatial-icon-x" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>';
  var SVG_FLIP = '<svg class="spatial-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="17 1 21 5 17 9"></polyline><path d="M3 11V9a4 4 0 0 1 4-4h14"></path><polyline points="7 23 3 19 7 15"></polyline><path d="M21 13v2a4 4 0 0 1-4 4H3"></path></svg>';

  var GRID = 24;
  function snapToGrid(value) { return Math.round(value / GRID) * GRID; }

  // Wiki-link regex — matches [[target]], [[target|alias]], [[target#heading|alias]]
  // Same pattern as backend/app/obsidian/scanner.py WIKILINK_RE
  var WIKILINK_RE = /(?<!!)\[\[([^\]\|#]+)(?:#[^\]\|]*)?\s*(?:\|([^\]]*))?\]\]/g;

  // Maps lowercase title to IRI for on-canvas nodes (rebuilt each renderNodes call)
  var wikiLinkTitleMap = {};

  /**
   * Return nodes sorted in spatial order: top-to-bottom, left-to-right.
   */
  function nodesSpatialOrder() {
    return state.nodes.slice().sort(function (a, b) {
      if (a.y !== b.y) return a.y - b.y;
      return a.x - b.x;
    });
  }

  /**
   * Cycle the node selection forward (+1) or backward (-1) in spatial order.
   */
  function cycleSelection(direction) {
    if (state.nodes.length === 0) return;
    var sorted = nodesSpatialOrder();
    if (!state.selectedNodeId) {
      state.selectedNodeId = sorted[direction > 0 ? 0 : sorted.length - 1].id;
      renderNodes();
      return;
    }
    var currentIdx = -1;
    for (var i = 0; i < sorted.length; i++) {
      if (sorted[i].id === state.selectedNodeId) { currentIdx = i; break; }
    }
    if (currentIdx === -1) {
      state.selectedNodeId = sorted[0].id;
    } else {
      var next = currentIdx + direction;
      if (next >= sorted.length) next = 0;
      if (next < 0) next = sorted.length - 1;
      state.selectedNodeId = sorted[next].id;
    }
    renderNodes();
  }

  /**
   * Keyboard handler for canvas interactions.
   * Guards against capturing keys while typing in inputs or other panels.
   */
  function onKeyDown(event) {
    // Guard: do not capture keys when an input element has focus
    var tag = document.activeElement ? document.activeElement.tagName : '';
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return;
    // Guard: do not capture keys when focus is inside dockview tabs or CodeMirror
    if (document.activeElement && document.activeElement.closest &&
        (document.activeElement.closest('.dv-tabs-container') || document.activeElement.closest('.cm-editor'))) return;
    // Guard: only process if canvas is mounted
    if (!state.mounted || !state.viewport) return;

    var key = event.key;

    // Ctrl+S / Cmd+S — save canvas (works even without selection)
    if (key === 's' && (event.ctrlKey || event.metaKey)) {
      event.preventDefault();
      saveCanvas();
      return;
    }

    // Tab / Shift+Tab — cycle selection (works even without current selection)
    if (key === 'Tab') {
      event.preventDefault();
      cycleSelection(event.shiftKey ? -1 : 1);
      return;
    }

    // All remaining keys require a selected node
    if (!state.selectedNodeId) return;
    var node = findNode(state.selectedNodeId);
    if (!node) return;

    var step = event.shiftKey ? GRID * 5 : GRID;

    switch (key) {
      case 'ArrowUp':
        event.preventDefault();
        node.y -= step;
        renderNodes();
        break;
      case 'ArrowDown':
        event.preventDefault();
        node.y += step;
        renderNodes();
        break;
      case 'ArrowLeft':
        event.preventDefault();
        node.x -= step;
        renderNodes();
        break;
      case 'ArrowRight':
        event.preventDefault();
        node.x += step;
        renderNodes();
        break;
      case 'Delete':
      case 'Backspace':
        event.preventDefault();
        var sorted = nodesSpatialOrder();
        var removedIdx = -1;
        for (var i = 0; i < sorted.length; i++) {
          if (sorted[i].id === state.selectedNodeId) { removedIdx = i; break; }
        }
        removeNode(state.selectedNodeId);
        // Auto-select next node in spatial order after deletion
        if (state.nodes.length > 0) {
          var remaining = nodesSpatialOrder();
          var nextIdx = Math.min(removedIdx, remaining.length - 1);
          if (nextIdx < 0) nextIdx = 0;
          state.selectedNodeId = remaining[nextIdx].id;
        } else {
          state.selectedNodeId = null;
        }
        renderNodes();
        break;
      case 'Enter':
        event.preventDefault();
        toggleExpand(state.selectedNodeId);
        break;
      case 'Escape':
        state.selectedNodeId = null;
        renderNodes();
        break;
    }
  }

  function mountCanvas() {
    var root = document.getElementById('spatial-canvas-root');
    if (!root) return;
    if (state.mounted) return;

    var viewport = root.querySelector('.spatial-canvas-viewport');
    var layer = root.querySelector('.spatial-canvas-layer');
    if (!viewport || !layer) return;

    state.viewport = viewport;
    state.layer = layer;
    state.embedLayer = viewport.querySelector('.spatial-canvas-embed-layer');
    state.canvasId = root.dataset.canvasId || 'default';

    renderNodes();
    applyTransform();
    bindEvents();
    state.mounted = true;

    // Register cleanup so dockview panel disposal tears down listeners
    if (typeof window.SemPKM.registerCleanup === 'function') {
      window.SemPKM.registerCleanup('spatial-canvas-root', function () {
        unbindEvents();
        state.mounted = false;
        state.viewport = null;
        state.layer = null;
        state.embedLayer = null;
      });
    }

    // Session switch handler
    var select = document.getElementById('canvas-session-select');
    if (select) {
      select.addEventListener('change', function() {
        var sessionId = select.value;
        if (!sessionId) {
          // "New canvas" selected — clear canvas
          state.nodes = [];
          state.edges = [];
          state.expandProvenance = {};
          state.currentSessionId = null;
          state.canvasId = 'new-' + Date.now();
          renderNodes();
          setStatus('New canvas');
          return;
        }
        // Switch to selected session
        state.canvasId = sessionId;
        state.currentSessionId = sessionId;
        // Set active on backend
        apiFetch('/api/canvas/sessions/' + encodeURIComponent(sessionId) + '/activate', {method: 'PUT', silent: true});
        loadCanvas(false);
      });
    }

    loadSessionList();
  }

  function unbindEvents() {
    window.removeEventListener('pointermove', onPointerMove);
    window.removeEventListener('pointerup', onPointerUp);
    document.removeEventListener('dragover', onDragOver, true);
    document.removeEventListener('dragleave', onDragLeave, true);
    document.removeEventListener('drop', onDrop, true);
    document.removeEventListener('dragend', onDragEnd, true);
    document.removeEventListener('keydown', onKeyDown);
  }

  function bindEvents() {
    // Remove any stacked listeners from a previous mount cycle
    unbindEvents();
    state.viewport.addEventListener('wheel', onWheel, { passive: false });
    state.viewport.addEventListener('pointerdown', onPointerDown);
    state.layer.addEventListener('click', onLayerClick);
    if (state.embedLayer) state.embedLayer.addEventListener('click', onEmbedLayerClick);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    // Drag-drop from nav tree: use capture phase on document so we see events
    // before dockview's tab drag-drop system can intercept them.
    document.addEventListener('dragover', onDragOver, true);
    document.addEventListener('dragleave', onDragLeave, true);
    document.addEventListener('drop', onDrop, true);
    // Fallback: dockview often swallows the 'drop' event entirely.
    // dragend always fires on the source element regardless — use it as a
    // backup if we tracked a valid drag position over the canvas.
    document.addEventListener('dragend', onDragEnd, true);
    // Keyboard navigation for canvas nodes
    document.addEventListener('keydown', onKeyDown);
  }

  // Track last known drag position over canvas for the dragend fallback.
  var lastDragOverCanvas = null;

  function isOverCanvas(event) {
    if (!state.viewport) return false;
    var rect = state.viewport.getBoundingClientRect();
    return event.clientX >= rect.left && event.clientX <= rect.right &&
           event.clientY >= rect.top && event.clientY <= rect.bottom;
  }

  function addNodeFromDrag(iri, label, clientX, clientY) {
    if (!iri) return;
    if (findNode(iri)) {
      setStatus('Already on canvas');
      if (window.SemPKM.showToast) window.SemPKM.showToast('Already on canvas');
      return;
    }
    var world = screenToWorld(clientX, clientY);
    state.nodes.push({
      id: iri,
      title: label || 'Resource',
      uri: iri,
      x: snapToGrid(world.x),
      y: snapToGrid(world.y),
      markdown: '',
      collapsed: false,
    });
    renderNodes();
    setStatus('Added: ' + (label || iri));
    fetchNodeBody(iri);
  }

  var MAX_EMBEDS = 8;

  function addEmbedNode(embedConfig, clientX, clientY) {
    if (!embedConfig || !embedConfig.url) return;
    // Enforce embed limit
    var embedCount = 0;
    for (var i = 0; i < state.nodes.length; i++) {
      if (state.nodes[i].nodeType === 'embed') embedCount++;
    }
    if (embedCount >= MAX_EMBEDS) {
      if (window.SemPKM.showToast) window.SemPKM.showToast('Maximum of ' + MAX_EMBEDS + ' embeds reached');
      return;
    }
    var world = screenToWorld(clientX, clientY);
    var nodeId = 'embed-' + Date.now() + '-' + Math.random().toString(36).substr(2, 6);
    state.nodes.push({
      id: nodeId,
      title: embedConfig.label || 'Embed',
      uri: '',
      x: snapToGrid(world.x),
      y: snapToGrid(world.y),
      width: 400,
      height: 300,
      nodeType: 'embed',
      embedConfig: {
        type: embedConfig.type || 'view',
        id: embedConfig.id || '',
        url: embedConfig.url,
        label: embedConfig.label || 'Embed',
      },
    });
    renderNodes();
    setStatus('Embed added: ' + (embedConfig.label || embedConfig.url));
  }

  function onEmbedLayerClick(event) {
    var deleteBtn = event.target.closest('.spatial-node-delete');
    if (deleteBtn) {
      var nodeEl = deleteBtn.closest('.spatial-node');
      if (!nodeEl) return;
      removeNode(nodeEl.dataset.nodeId);
      return;
    }
  }

  function fetchNodeBody(iri) {
    apiFetch('/api/canvas/body?iri=' + encodeURIComponent(iri), { silent: true })
      .then(function (r) { return r.json(); })
      .catch(function () { return null; })
      .then(function (data) {
        if (!data || !data.body) return;
        var node = findNode(iri);
        if (node) {
          node.markdown = data.body;
          renderNodes();
        }
      })
      .catch(function () { /* silent — body is optional */ });
  }

  function fetchNodeProperties(nodeId, iri) {
    apiFetch('/api/canvas/properties?iri=' + encodeURIComponent(iri), { silent: true })
      .then(function (r) { return r.json(); })
      .catch(function () { return null; })
      .then(function (data) {
        if (data) {
          state.propertyCache[nodeId] = data;
        }
        renderNodes();
      })
      .catch(function () { renderNodes(); });
  }

  function buildPropertyTable(data) {
    var html = ['<div class="spatial-node-properties">'];
    if (data.type_label) {
      html.push('<div class="prop-type-header">', escapeHtml(data.type_label), '</div>');
    }
    var props = data.properties || [];
    for (var i = 0; i < props.length; i++) {
      var prop = props[i];
      var rowClass = prop.source === 'inferred' ? ' prop-inferred' : '';
      html.push('<div class="prop-row', rowClass, '">');
      html.push('<span class="prop-label">', escapeHtml(prop.name || ''), '</span>');
      html.push('<span class="prop-value">');
      var vals = prop.values || (prop.value != null ? [prop.value] : []);
      for (var j = 0; j < vals.length; j++) {
        var v = vals[j];
        var display = '';
        if (typeof v === 'object' && v !== null) {
          display = v.ref_label || v.value || String(v);
        } else if (typeof v === 'boolean') {
          display = v ? '✓' : '✗';
        } else {
          display = String(v);
        }
        // Tag-like values get pill treatment
        if (prop.datatype === 'tag' || (display.length > 0 && display.charAt(0) === '#')) {
          html.push('<span class="prop-pill">', escapeHtml(display), '</span>');
        } else if (vals.length > 1) {
          html.push('<span class="prop-pill">', escapeHtml(display), '</span>');
        } else {
          html.push(escapeHtml(display));
        }
      }
      if (vals.length === 0) {
        html.push('<span class="prop-empty">—</span>');
      }
      html.push('</span></div>');
    }
    if (props.length === 0) {
      html.push('<div class="prop-row"><span class="prop-label" style="width:auto">No properties</span></div>');
    }
    html.push('</div>');
    return html.join('');
  }

  /**
   * Place multiple nodes in a 3-column grid layout at the drop point and
   * auto-discover edges between all canvas nodes afterward.
   */
  function addNodesFromBulkDrop(items, clientX, clientY) {
    var world = screenToWorld(clientX, clientY);
    var baseX = snapToGrid(world.x);
    var baseY = snapToGrid(world.y);
    var cols = 3;
    var colWidth = 260 + GRID; // node width (260px) + 1 grid gap
    var rowHeight = 120 + GRID; // estimated node height + gap

    var addedIris = [];
    var placed = 0;
    items.forEach(function(item) {
      if (findNode(item.iri)) return; // skip duplicates silently
      var col = placed % cols;
      var row = Math.floor(placed / cols);
      state.nodes.push({
        id: item.iri,
        title: item.label || 'Resource',
        uri: item.iri,
        x: snapToGrid(baseX + col * colWidth),
        y: snapToGrid(baseY + row * rowHeight),
        markdown: '',
        collapsed: false,
      });
      addedIris.push(item.iri);
      fetchNodeBody(item.iri);
      placed++;
    });

    if (addedIris.length > 0) {
      renderNodes();
      setStatus('Added ' + addedIris.length + ' nodes');
      fetchBulkEdges(addedIris);
    }
  }

  /**
   * Fetch all edges between canvas nodes from the backend batch-edges
   * endpoint, then merge any new edges into state and re-render.
   */
  function fetchBulkEdges(newIris) {
    // Include all existing canvas node IRIs for complete edge discovery
    var allIris = state.nodes.map(function(n) { return n.id; });
    apiFetch('/api/canvas/batch-edges', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ iris: allIris }),
      silent: true,
    })
    .then(function(r) { return r.json(); })
    .catch(function() { return null; })
    .then(function(data) {
      if (!data || !Array.isArray(data.edges)) return;
      var existingEdgeIds = {};
      state.edges.forEach(function(e) { existingEdgeIds[e.id] = true; });
      data.edges.forEach(function(edge) {
        var edgeId = edge.source + '|' + edge.predicate + '|' + edge.target;
        if (existingEdgeIds[edgeId]) return;
        state.edges.push({
          id: edgeId,
          source: edge.source,
          target: edge.target,
          label: edge.predicate_label || edge.predicate,
        });
        existingEdgeIds[edgeId] = true;
      });
      renderNodes();
    })
    .catch(function() { /* silent -- edges are optional enhancement */ });
  }

  function onDragOver(event) {
    if (!window.SemPKM.__canvasDragPayload) return;
    if (!isOverCanvas(event)) {
      state.viewport.classList.remove('canvas-drop-active');
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = 'copy';
    state.viewport.classList.add('canvas-drop-active');
    lastDragOverCanvas = { x: event.clientX, y: event.clientY };
  }

  function onDragLeave(event) {
    // Only remove visual hint; do NOT clear lastDragOverCanvas here.
    // Dockview overlays cause spurious dragleave events while the pointer
    // is still visually over the canvas, which would wipe the position
    // needed by the dragend fallback.
    if (!isOverCanvas(event)) {
      state.viewport.classList.remove('canvas-drop-active');
    }
  }

  function onDrop(event) {
    if (!isOverCanvas(event)) return;
    event.preventDefault();
    event.stopPropagation();
    state.viewport.classList.remove('canvas-drop-active');
    lastDragOverCanvas = null;

    // Check for bulk drop payload (multi-select drag from nav tree)
    var payload = window.SemPKM.__canvasDragPayload;
    if (payload && Array.isArray(payload.items) && payload.items.length > 1) {
      if (payload.items.length > 20) {
        if (!window.confirm('Drop ' + payload.items.length + ' nodes? This may crowd the canvas.')) {
          window.SemPKM.__canvasDragPayload = null;
          return;
        }
      }
      addNodesFromBulkDrop(payload.items, event.clientX, event.clientY);
      window.SemPKM.__canvasDragPayload = null;
      return;
    }

    // Check for embed-type payload (dashboard, view, query, object-embed drag)
    var embedTypes = ['dashboard', 'view', 'query', 'object-embed'];
    if (payload && payload.type && embedTypes.indexOf(payload.type) !== -1) {
      addEmbedNode({
        type: payload.type,
        id: payload.id || '',
        url: payload.url,
        label: payload.label || 'Embed',
      }, event.clientX, event.clientY);
      window.SemPKM.__canvasDragPayload = null;
      return;
    }

    var iri = event.dataTransfer.getData('text/iri');
    var label = event.dataTransfer.getData('text/label');
    addNodeFromDrag(iri, label, event.clientX, event.clientY);
    window.SemPKM.__canvasDragPayload = null;
  }

  function onDragEnd(event) {
    // Always clean up visual state.
    state.viewport.classList.remove('canvas-drop-active');
    // Fallback: if drop never fired but we had a valid position over the
    // canvas, use the side-channel payload set by tree_children.html.
    if (lastDragOverCanvas && window.SemPKM.__canvasDragPayload) {
      var payload = window.SemPKM.__canvasDragPayload;
      // Check for bulk drop payload (multi-select drag)
      if (Array.isArray(payload.items) && payload.items.length > 1) {
        if (payload.items.length > 20) {
          if (!window.confirm('Drop ' + payload.items.length + ' nodes? This may crowd the canvas.')) {
            lastDragOverCanvas = null;
            window.SemPKM.__canvasDragPayload = null;
            return;
          }
        }
        addNodesFromBulkDrop(payload.items, lastDragOverCanvas.x, lastDragOverCanvas.y);
      // Check for embed-type payload (dashboard, view, query, object-embed drag)
      } else if (payload.type && ['dashboard', 'view', 'query', 'object-embed'].indexOf(payload.type) !== -1) {
        addEmbedNode({
          type: payload.type,
          id: payload.id || '',
          url: payload.url,
          label: payload.label || 'Embed',
        }, lastDragOverCanvas.x, lastDragOverCanvas.y);
      } else {
        addNodeFromDrag(payload.iri, payload.label, lastDragOverCanvas.x, lastDragOverCanvas.y);
      }
    }
    lastDragOverCanvas = null;
    window.SemPKM.__canvasDragPayload = null;
  }

  function onWheel(event) {
    event.preventDefault();

    var rect = state.viewport.getBoundingClientRect();
    var cx = event.clientX - rect.left;
    var cy = event.clientY - rect.top;

    var worldX = (cx - state.translateX) / state.scale;
    var worldY = (cy - state.translateY) / state.scale;

    var factor = event.deltaY > 0 ? 0.92 : 1.08;
    var next = Math.max(state.minScale, Math.min(state.maxScale, state.scale * factor));

    state.scale = next;
    state.translateX = cx - (worldX * state.scale);
    state.translateY = cy - (worldY * state.scale);

    applyTransform();
    updateZoomLabel();
  }

  function onPointerDown(event) {
    if (event.target && event.target.closest && (event.target.closest('.spatial-node-markdown a') || event.target.closest('.spatial-node-chevron') || event.target.closest('.spatial-node-expand') || event.target.closest('.spatial-node-flip') || event.target.closest('.spatial-node-delete'))) {
      return;
    }

    // Resize handle detection — must come before node drag
    var resizeHandle = event.target.closest('.spatial-node-resize-handle, .spatial-node-resize-handle-right, .spatial-node-resize-handle-bottom');
    if (resizeHandle) {
      event.stopPropagation();
      event.preventDefault();
      var nodeEl = resizeHandle.closest('.spatial-node');
      if (!nodeEl) return;
      var nodeId = nodeEl.dataset.nodeId;
      var model = findNode(nodeId);
      if (!model) return;

      // Determine handle type
      var handleType = 'corner';
      if (resizeHandle.classList.contains('spatial-node-resize-handle-right')) handleType = 'right';
      else if (resizeHandle.classList.contains('spatial-node-resize-handle-bottom')) handleType = 'bottom';

      state.resizingNodeId = nodeId;
      state.resizeStartX = event.clientX;
      state.resizeStartY = event.clientY;
      state.resizeStartWidth = nodeEl.offsetWidth;
      state.resizeStartHeight = nodeEl.offsetHeight;
      state.resizeHandleType = handleType;

      // Select the node being resized
      if (state.selectedNodeId !== nodeId) {
        state.selectedNodeId = nodeId;
        renderNodes();
      }
      return;
    }

    var node = event.target.closest('.spatial-node');
    if (node) {
      state.nodeDragId = node.dataset.nodeId;
      // Click-to-select: set selected node on pointer down
      if (state.selectedNodeId !== state.nodeDragId) {
        state.selectedNodeId = state.nodeDragId;
        renderNodes();
      }
      var model = findNode(state.nodeDragId);
      if (!model) return;

      var world = screenToWorld(event.clientX, event.clientY);
      state.nodeDragOffsetX = world.x - model.x;
      state.nodeDragOffsetY = world.y - model.y;
      node.classList.add('dragging');
      return;
    }

    // Clicking on canvas background deselects
    if (state.selectedNodeId) {
      state.selectedNodeId = null;
      renderNodes();
    }

    state.isPanning = true;
    state.panStartX = event.clientX;
    state.panStartY = event.clientY;
    state.viewport.classList.add('is-panning');
  }

  function onLayerClick(event) {
    // Chevron click — toggle body collapsed/expanded
    var chevronBtn = event.target.closest('.spatial-node-chevron');
    if (chevronBtn) {
      var chevronNode = chevronBtn.closest('.spatial-node');
      if (!chevronNode) return;
      var model = findNode(chevronNode.dataset.nodeId);
      if (!model) return;
      model.collapsed = !model.collapsed;
      renderNodes();
      return;
    }

    // Delete click — remove node
    var deleteBtn = event.target.closest('.spatial-node-delete');
    if (deleteBtn) {
      var deleteNode = deleteBtn.closest('.spatial-node');
      if (!deleteNode) return;
      removeNode(deleteNode.dataset.nodeId);
      return;
    }

    // Expand click — toggle expand/collapse neighbors
    var expandBtn = event.target.closest('.spatial-node-expand');
    if (expandBtn) {
      var expandNode = expandBtn.closest('.spatial-node');
      if (!expandNode) return;
      toggleExpand(expandNode.dataset.nodeId);
      return;
    }

    // Flip click — toggle property table / markdown body
    var flipBtn = event.target.closest('.spatial-node-flip');
    if (flipBtn) {
      var flipNode = flipBtn.closest('.spatial-node');
      if (!flipNode) return;
      var nodeId = flipNode.dataset.nodeId;
      var model = findNode(nodeId);
      if (!model) return;
      model.showProperties = !model.showProperties;
      if (model.showProperties && !state.propertyCache[nodeId]) {
        fetchNodeProperties(nodeId, model.uri);
      } else {
        renderNodes();
      }
      return;
    }

    // Ghost node click — resolve wiki-link and add full node
    var ghostNode = event.target.closest('.spatial-ghost-node');
    if (ghostNode) {
      var ghostTitle = ghostNode.getAttribute('data-ghost-title');
      if (!ghostTitle) return;
      var ghostX = parseInt(ghostNode.style.left, 10) || 0;
      var ghostY = parseInt(ghostNode.style.top, 10) || 0;
      // Resolve title to IRI via backend
      apiFetch('/api/canvas/resolve-wikilinks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ titles: [ghostTitle] }),
        silent: true,
      })
        .then(function (r) { return r.json(); })
        .catch(function () { return null; })
        .then(function (data) {
          if (!data || !data.resolved) {
            if (window.SemPKM.showToast) window.SemPKM.showToast('Object not found: ' + ghostTitle);
            return;
          }
          var iri = data.resolved[ghostTitle];
          if (!iri) {
            if (window.SemPKM.showToast) window.SemPKM.showToast('Object not found: ' + ghostTitle);
            return;
          }
          if (findNode(iri)) {
            setStatus('Already on canvas');
            renderNodes();
            return;
          }
          state.nodes.push({
            id: iri,
            title: ghostTitle,
            uri: iri,
            x: snapToGrid(ghostX),
            y: snapToGrid(ghostY),
            markdown: '',
            collapsed: false,
          });
          setStatus('Added: ' + ghostTitle);
          renderNodes();
          fetchNodeBody(iri);
        })
        .catch(function () {
          if (window.SemPKM.showToast) window.SemPKM.showToast('Object not found: ' + ghostTitle);
        });
      return;
    }

    var link = event.target.closest('.spatial-node-markdown a');
    if (link) {
      event.preventDefault();
      var href = link.getAttribute('href') || '';
      var sourceEl = link.closest('.spatial-node');
      var source = sourceEl ? findNode(sourceEl.dataset.nodeId) : null;
      if (!href) return;
      // Skip wikilink: scheme — those are handled by ghost node clicks
      if (href.indexOf('wikilink:') === 0) return;
      var target = findNode(href);
      if (target) {
        setStatus('Focused existing node: ' + href);
        return;
      }
      var shouldAdd = window.confirm('Add target node to canvas?\n' + href);
      if (!shouldAdd) return;

      var baseX = source ? source.x + 320 : 260;
      var baseY = source ? source.y + 40 : 220;
      state.nodes.push({
        id: href,
        title: 'Linked Resource',
        uri: href,
        x: baseX,
        y: baseY,
        markdown: '',
        collapsed: false,
      });
      setStatus('Added linked node: ' + href);
      renderNodes();
      fetchNodeBody(href);
    }
  }

  function removeNode(nodeId) {
    // Filter out the node
    state.nodes = state.nodes.filter(function (n) { return n.id !== nodeId; });
    // Filter out edges referencing this node
    state.edges = state.edges.filter(function (e) { return e.source !== nodeId && e.target !== nodeId; });
    // Remove persistent embed DOM element if present
    if (state.embedLayer) {
      var embedEl = state.embedLayer.querySelector('[data-node-id="' + CSS.escape(nodeId) + '"]');
      if (embedEl) embedEl.remove();
    }
    // Clean up provenance: remove nodeId from any expand's child list
    var provenanceKeys = Object.keys(state.expandProvenance);
    for (var i = 0; i < provenanceKeys.length; i++) {
      var key = provenanceKeys[i];
      var children = state.expandProvenance[key];
      var idx = children.indexOf(nodeId);
      if (idx !== -1) {
        children.splice(idx, 1);
      }
    }
    // Delete this node's own provenance if it was expanded
    delete state.expandProvenance[nodeId];
    renderNodes();
  }

  function toggleExpand(nodeId) {
    if (state.expandProvenance[nodeId]) {
      // Collapse: remove nodes exclusively owned by this expand
      var childIds = state.expandProvenance[nodeId];
      // Build set of all provenance-referenced nodes (except this expand)
      var referencedElsewhere = {};
      var provenanceKeys = Object.keys(state.expandProvenance);
      for (var i = 0; i < provenanceKeys.length; i++) {
        if (provenanceKeys[i] === nodeId) continue;
        var otherChildren = state.expandProvenance[provenanceKeys[i]];
        for (var j = 0; j < otherChildren.length; j++) {
          referencedElsewhere[otherChildren[j]] = true;
        }
      }
      // Remove only exclusively owned nodes
      var toRemove = {};
      for (var k = 0; k < childIds.length; k++) {
        if (!referencedElsewhere[childIds[k]]) {
          toRemove[childIds[k]] = true;
        }
      }
      state.nodes = state.nodes.filter(function (n) { return !toRemove[n.id]; });
      state.edges = state.edges.filter(function (e) { return !toRemove[e.source] && !toRemove[e.target]; });
      delete state.expandProvenance[nodeId];
      renderNodes();
      setStatus('Collapsed neighbors');
    } else {
      expandNode(nodeId);
    }
  }

  async function expandNode(nodeId) {
    var model = findNode(nodeId);
    if (!model) return;

    try {
      var response = await apiFetch('/api/canvas/subgraph?root_uri=' + encodeURIComponent(model.uri) + '&depth=1', { silent: true });
      var data = await response.json();

      if (!data || !Array.isArray(data.nodes)) return;

      var existingIds = {};
      state.nodes.forEach(function (n) { existingIds[n.id] = true; });

      var newNodeIds = [];
      var newNodes = data.nodes.filter(function (n) {
        var nid = String(n.id || '');
        return nid && !existingIds[nid];
      });

      newNodes.forEach(function (node, idx) {
        var nid = String(node.id || '');
        var angle = (idx / Math.max(newNodes.length, 1)) * Math.PI * 2;
        var radius = 350;
        state.nodes.push({
          id: nid,
          title: String(node.label || node.id || 'Resource'),
          uri: nid,
          x: snapToGrid(model.x + Math.cos(angle) * radius),
          y: snapToGrid(model.y + Math.sin(angle) * radius),
          markdown: '',
          collapsed: false,
        });
        newNodeIds.push(nid);
        existingIds[nid] = true;
        fetchNodeBody(nid);
      });

      // Merge edges (dedup)
      if (Array.isArray(data.edges)) {
        var existingEdgeIds = {};
        state.edges.forEach(function (e) { existingEdgeIds[e.id] = true; });
        data.edges.forEach(function (edge) {
          var source = String(edge.source || '');
          var target = String(edge.target || '');
          var predicate = String(edge.predicate || 'relatedTo');
          if (!source || !target) return;
          var edgeId = source + '|' + predicate + '|' + target;
          if (existingEdgeIds[edgeId]) return;
          state.edges.push({
            id: edgeId,
            source: source,
            target: target,
            label: String(edge.predicate_label || predicate),
          });
          existingEdgeIds[edgeId] = true;
        });
      }

      state.expandProvenance[nodeId] = newNodeIds;
      renderNodes();
      setStatus('Expanded ' + newNodeIds.length + ' neighbors');
    } catch (error) {
      setStatus('Expand failed', true);
    }
  }

  function onPointerMove(event) {
    // Resize in progress — update dimensions directly on DOM for performance
    if (state.resizingNodeId) {
      var node = findNode(state.resizingNodeId);
      if (!node) return;
      var dx = (event.clientX - state.resizeStartX) / state.scale;
      var dy = (event.clientY - state.resizeStartY) / state.scale;

      if (state.resizeHandleType === 'corner' || state.resizeHandleType === 'right') {
        node.width = snapToGrid(Math.max(160, state.resizeStartWidth + dx));
      }
      if (state.resizeHandleType === 'corner' || state.resizeHandleType === 'bottom') {
        node.height = snapToGrid(Math.max(80, state.resizeStartHeight + dy));
      }

      // Apply directly to DOM to avoid full re-render per frame
      var el = state.layer.querySelector('.spatial-node[data-node-id="' + CSS.escape(state.resizingNodeId) + '"]');
      if (!el && state.embedLayer) el = state.embedLayer.querySelector('.spatial-node[data-node-id="' + CSS.escape(state.resizingNodeId) + '"]');
      if (el) {
        if (node.width !== undefined) el.style.width = node.width + 'px';
        if (node.height !== undefined) el.style.height = node.height + 'px';
      }
      return;
    }

    if (state.nodeDragId) {
      var node = findNode(state.nodeDragId);
      if (!node) return;
      var world = screenToWorld(event.clientX, event.clientY);
      node.x = snapToGrid(world.x - state.nodeDragOffsetX);
      node.y = snapToGrid(world.y - state.nodeDragOffsetY);
      renderNodes();
      return;
    }

    if (!state.isPanning) return;
    state.translateX += event.clientX - state.panStartX;
    state.translateY += event.clientY - state.panStartY;
    state.panStartX = event.clientX;
    state.panStartY = event.clientY;
    applyTransform();
  }

  function onPointerUp() {
    // Finalize resize — re-render to update edges and DOM state
    if (state.resizingNodeId) {
      state.resizingNodeId = null;
      state.resizeHandleType = null;
      renderNodes();
      return;
    }

    if (state.nodeDragId) {
      var nodeEl = state.viewport.querySelector('.spatial-node.dragging');
      if (nodeEl) nodeEl.classList.remove('dragging');
    }

    state.nodeDragId = null;
    state.isPanning = false;
    if (state.viewport) state.viewport.classList.remove('is-panning');
  }

  function renderNodes() {
    if (!state.layer) return;

    // Rebuild wiki-link title map from current on-canvas nodes
    wikiLinkTitleMap = {};
    for (var ti = 0; ti < state.nodes.length; ti++) {
      var n = state.nodes[ti];
      if (n.title) {
        wikiLinkTitleMap[n.title.toLowerCase()] = n.id;
      }
    }

    var edgesHtml = state.edges.map(function (edge) {
      var source = findNode(edge.source);
      var target = findNode(edge.target);
      if (!source || !target) return '';

      var x1 = source.x + 130;
      var y1 = source.y + 44;
      var x2 = target.x + 130;
      var y2 = target.y + 44;
      var mx = Math.round((x1 + x2) / 2);
      var my = Math.round((y1 + y2) / 2) - 10;

      return [
        '<line class="spatial-edge-line" x1="', x1, '" y1="', y1, '" x2="', x2, '" y2="', y2, '"></line>',
        '<text class="spatial-edge-label" x="', mx, '" y="', my, '">', escapeHtml(edge.label || ''), '</text>'
      ].join('');
    }).join('');

    var nodesHtml = state.nodes.map(function (node) {
      // Skip embed nodes — they are rendered persistently in the embed layer
      if (node.nodeType === 'embed') return '';
      var isExpanded = !!state.expandProvenance[node.id];
      var isOpen = !node.collapsed;
      var isSelected = state.selectedNodeId === node.id;
      // Build inline style: always position, plus width/height if resized
      var inlineStyle = 'left:' + node.x + 'px; top:' + node.y + 'px;';
      if (node.width !== undefined) inlineStyle += ' width:' + node.width + 'px;';
      if (node.height !== undefined) inlineStyle += ' height:' + node.height + 'px;';
      return [
        '<article class="spatial-node', (node.collapsed ? ' is-collapsed' : ''), (isExpanded ? ' is-expanded' : ''), (isSelected ? ' spatial-node-selected' : ''), '" data-node-id="', escapeHtml(node.id), '" style="', inlineStyle, '">',
          '<header class="spatial-node-header">',
            '<button class="spatial-node-chevron', (isOpen ? ' is-open' : ''), '" type="button" title="Toggle body">', SVG_CHEVRON, '</button>',
            '<span class="spatial-node-title">', escapeHtml(node.title), '</span>',
            '<button class="spatial-node-expand" type="button" title="Expand neighbors">', SVG_PLUS, '</button>',
            '<button class="spatial-node-flip', (node.showProperties ? ' is-flipped' : ''), '" type="button" title="Toggle properties">', SVG_FLIP, '</button>',
            '<button class="spatial-node-delete" type="button" title="Remove from canvas">', SVG_X, '</button>',
          '</header>',
          '<div class="spatial-node-uri">', escapeHtml(node.uri), '</div>',
          (node.collapsed ? '' :
            (node.showProperties && state.propertyCache[node.id]
              ? buildPropertyTable(state.propertyCache[node.id])
              : '<div class="spatial-node-markdown">' + renderMarkdown(node.markdown || '') + '</div>')),
          '<div class="spatial-node-resize-handle"></div>',
          '<div class="spatial-node-resize-handle-right"></div>',
          '<div class="spatial-node-resize-handle-bottom"></div>',
        '</article>'
      ].join('');
    }).join('');

    // Render node HTML only; edges are drawn in the second pass below
    // using edgePoint() for proper box-edge termination.
    state.layer.innerHTML = nodesHtml;

    // ── Embed layer: persistent DOM — create/update/orphan-clean ──
    if (state.embedLayer) {
      var embedNodeIds = {};
      for (var ei = 0; ei < state.nodes.length; ei++) {
        var eNode = state.nodes[ei];
        if (eNode.nodeType !== 'embed') continue;
        if (!eNode.embedConfig || !eNode.embedConfig.url) continue; // skip malformed embed nodes
        embedNodeIds[eNode.id] = true;
        var existingEl = state.embedLayer.querySelector('[data-node-id="' + CSS.escape(eNode.id) + '"]');
        if (existingEl) {
          // Update position/size only — never rebuild innerHTML
          existingEl.style.left = eNode.x + 'px';
          existingEl.style.top = eNode.y + 'px';
          if (eNode.width !== undefined) existingEl.style.width = eNode.width + 'px';
          if (eNode.height !== undefined) existingEl.style.height = eNode.height + 'px';
          // Update selection state
          if (state.selectedNodeId === eNode.id) {
            existingEl.classList.add('spatial-node-selected');
          } else {
            existingEl.classList.remove('spatial-node-selected');
          }
        } else {
          // Create new embed node DOM element
          var article = document.createElement('article');
          article.className = 'spatial-node spatial-node-embed' + (state.selectedNodeId === eNode.id ? ' spatial-node-selected' : '');
          article.dataset.nodeId = eNode.id;
          article.dataset.embedType = eNode.embedConfig.type || '';
          article.style.left = eNode.x + 'px';
          article.style.top = eNode.y + 'px';
          article.style.width = (eNode.width || 400) + 'px';
          article.style.height = (eNode.height || 300) + 'px';
          article.innerHTML = [
            '<header class="spatial-node-header">',
              '<span class="spatial-node-title">', escapeHtml(eNode.embedConfig.label || 'Embed'), '</span>',
              '<button class="spatial-node-delete" type="button" title="Remove embed">', SVG_X, '</button>',
            '</header>',
            '<div class="spatial-node-embed-body">',
              '<iframe src="', escapeHtml(eNode.embedConfig.url), '" class="spatial-embed-iframe" loading="lazy"></iframe>',
              '<div class="spatial-embed-loading">Loading…</div>',
            '</div>',
            '<div class="spatial-node-resize-handle"></div>',
            '<div class="spatial-node-resize-handle-right"></div>',
            '<div class="spatial-node-resize-handle-bottom"></div>',
          ].join('');
          // Wire iframe load event to hide loading overlay
          var iframe = article.querySelector('.spatial-embed-iframe');
          var loadingOverlay = article.querySelector('.spatial-embed-loading');
          if (iframe && loadingOverlay) {
            iframe.addEventListener('load', function () {
              this.parentNode.querySelector('.spatial-embed-loading').classList.add('loaded');
            });
          }
          state.embedLayer.appendChild(article);
        }
      }
      // Remove orphaned embed DOM elements
      state.embedLayer.querySelectorAll('[data-node-id]').forEach(function (el) {
        if (!embedNodeIds[el.dataset.nodeId]) el.remove();
      });
    }

    // Build nodeBoxes from both layers
    var nodeBoxes = {};
    state.viewport.querySelectorAll('.spatial-node').forEach(function (el) {
      var id = el.dataset.nodeId;
      var model = findNode(id);
      if (!id || !model) return;
      nodeBoxes[id] = {
        x: model.x,
        y: model.y,
        width: el.offsetWidth,
        height: el.offsetHeight,
      };
    });

    var markdownEdges = [];
    var anchorDotsHtml = [];
    var ghostNodes = [];

    state.layer.querySelectorAll('.spatial-node').forEach(function (nodeEl) {
      var sourceId = nodeEl.dataset.nodeId;
      var sourceBox = nodeBoxes[sourceId];
      if (!sourceBox) return;

      nodeEl.querySelectorAll('.spatial-node-markdown a[href]').forEach(function (linkEl, idx) {
        var href = linkEl.getAttribute('href') || '';
        if (!href) return;
        var linkRect = linkEl.getBoundingClientRect();
        var nodeRect = nodeEl.getBoundingClientRect();
        var anchorY = sourceBox.y + (linkRect.top - nodeRect.top) + (linkRect.height / 2);
        var anchorX = sourceBox.x + sourceBox.width;
        var linkLabel = linkEl.textContent || 'link';

        // Handle wikilink: scheme hrefs (unresolved wiki-links)
        if (href.indexOf('wikilink:') === 0) {
          var decodedTarget = decodeURIComponent(href.substring(9));
          // Check if the target can now be resolved on canvas (title map was rebuilt)
          var resolvedIri = wikiLinkTitleMap[decodedTarget.toLowerCase()];
          if (resolvedIri && findNode(resolvedIri)) {
            // Target is on canvas — draw a markdown edge to it
            anchorDotsHtml.push('<circle class="spatial-anchor-dot spatial-anchor-dot-wikilink" cx="' + Math.round(anchorX) + '" cy="' + Math.round(anchorY) + '" r="3"></circle>');
            markdownEdges.push({
              id: 'md|' + sourceId + '|' + resolvedIri + '|' + idx,
              source: sourceId,
              target: resolvedIri,
              label: linkLabel,
              anchorX: anchorX,
              anchorY: anchorY,
            });
          } else {
            // Target not on canvas — create ghost node
            anchorDotsHtml.push('<circle class="spatial-anchor-dot spatial-anchor-dot-wikilink" cx="' + Math.round(anchorX) + '" cy="' + Math.round(anchorY) + '" r="3"></circle>');
            ghostNodes.push({
              id: 'ghost:' + decodedTarget,
              label: decodedTarget,
              sourceId: sourceId,
              sourceBox: sourceBox,
              anchorX: anchorX,
              anchorY: anchorY,
            });
          }
          return;
        }

        // Standard href — check if target is on canvas
        var targetNode = findNode(href);

        anchorDotsHtml.push('<circle class="spatial-anchor-dot" cx="' + Math.round(anchorX) + '" cy="' + Math.round(anchorY) + '" r="3"></circle>');

        if (targetNode) {
          markdownEdges.push({
            id: 'md|' + sourceId + '|' + href + '|' + idx,
            source: sourceId,
            target: href,
            label: linkLabel,
            anchorX: anchorX,
            anchorY: anchorY,
          });
        }
      });
    });

    var combinedEdges = state.edges.concat(markdownEdges);

    var edgesHtml = combinedEdges.map(function (edge) {
      var source = nodeBoxes[edge.source];
      var target = nodeBoxes[edge.target];
      if (!source || !target) return '';

      var start = (typeof edge.anchorX === 'number' && typeof edge.anchorY === 'number')
        ? { x: edge.anchorX, y: edge.anchorY }
        : edgePoint(source, target);
      var end = edgePoint(target, source);
      var mx = Math.round((start.x + end.x) / 2);
      var my = Math.round((start.y + end.y) / 2) - 10;

      return [
        '<line class="spatial-edge-line', (edge.id.indexOf('md|') === 0 ? ' spatial-edge-line-markdown' : ''), '" x1="', Math.round(start.x), '" y1="', Math.round(start.y), '" x2="', Math.round(end.x), '" y2="', Math.round(end.y), '"></line>',
        '<text class="spatial-edge-label" x="', mx, '" y="', my, '">', escapeHtml(edge.label || ''), '</text>'
      ].join('');
    }).join('');

    // Build ghost node HTML and ghost edge SVG lines
    var ghostHtml = '';
    var ghostEdgesHtml = '';
    var ghostDedup = {};
    for (var gi = 0; gi < ghostNodes.length; gi++) {
      var g = ghostNodes[gi];
      if (ghostDedup[g.id]) continue;
      ghostDedup[g.id] = true;
      var gx = snapToGrid(g.sourceBox.x + g.sourceBox.width + 60);
      var gy = snapToGrid(g.anchorY - 16);
      ghostHtml += '<article class="spatial-ghost-node" data-ghost-title="' + escapeHtml(g.label) + '" data-ghost-source="' + escapeHtml(g.sourceId) + '" style="left:' + gx + 'px; top:' + gy + 'px;"><span class="spatial-ghost-label">' + escapeHtml(g.label) + '</span></article>';
      // Dashed green line from anchor dot to ghost node center
      var ghostCenterX = gx + 40;
      var ghostCenterY = gy + 12;
      ghostEdgesHtml += '<line class="spatial-edge-line spatial-edge-line-markdown" x1="' + Math.round(g.anchorX) + '" y1="' + Math.round(g.anchorY) + '" x2="' + ghostCenterX + '" y2="' + ghostCenterY + '"></line>';
    }

    var svgHtml = [
      '<svg class="spatial-edges" width="5000" height="5000" viewBox="0 0 5000 5000" aria-hidden="true">',
      '<defs><marker id="spatial-edge-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" class="spatial-edge-arrow-path"></path></marker></defs>',
      edgesHtml,
      ghostEdgesHtml,
      anchorDotsHtml.join(''),
      '</svg>'
    ].join('');

    state.layer.insertAdjacentHTML('afterbegin', svgHtml);
    // Append ghost nodes after all other elements
    if (ghostHtml) {
      state.layer.insertAdjacentHTML('beforeend', ghostHtml);
    }

    // Toggle hint visibility based on whether canvas has nodes
    var hint = document.getElementById('canvas-hint');
    if (hint) hint.style.display = state.nodes.length > 0 ? 'none' : '';
  }

  function applyTransform() {
    if (!state.layer) return;
    var t = 'translate(' + state.translateX + 'px, ' + state.translateY + 'px) scale(' + state.scale + ')';
    state.layer.style.transform = t;
    if (state.embedLayer) state.embedLayer.style.transform = t;
  }

  function findNode(id) {
    for (var i = 0; i < state.nodes.length; i++) {
      if (state.nodes[i].id === id) return state.nodes[i];
    }
    return null;
  }

  function edgePoint(fromBox, toBox) {
    var cx = fromBox.x + (fromBox.width / 2);
    var cy = fromBox.y + (fromBox.height / 2);
    var tx = toBox.x + (toBox.width / 2);
    var ty = toBox.y + (toBox.height / 2);

    var dx = tx - cx;
    var dy = ty - cy;

    if (dx === 0 && dy === 0) {
      return { x: cx, y: cy };
    }

    var scaleX = (fromBox.width / 2) / Math.max(Math.abs(dx), 0.0001);
    var scaleY = (fromBox.height / 2) / Math.max(Math.abs(dy), 0.0001);
    var scale = Math.min(scaleX, scaleY);

    return {
      x: cx + (dx * scale),
      y: cy + (dy * scale),
    };
  }

  function screenToWorld(clientX, clientY) {
    var rect = state.viewport.getBoundingClientRect();
    var sx = clientX - rect.left;
    var sy = clientY - rect.top;
    return {
      x: (sx - state.translateX) / state.scale,
      y: (sy - state.translateY) / state.scale,
    };
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }


  function renderMarkdown(markdownText) {
    if (!markdownText) return '';

    // Pre-process wiki-links before markdown parsing
    var preprocessed = markdownText.replace(WIKILINK_RE, function (match, target, alias) {
      var displayText = alias || target;
      var lowerTarget = target.trim().toLowerCase();
      var resolvedIri = wikiLinkTitleMap[lowerTarget];
      if (resolvedIri) {
        // Target is on canvas — render as a standard markdown link to the IRI
        return '[' + displayText + '](' + resolvedIri + ')';
      }
      // Target not on canvas — use wikilink: scheme for ghost node detection
      return '[' + displayText + '](wikilink:' + encodeURIComponent(target.trim()) + ')';
    });

    if (typeof globalThis.marked !== 'undefined') {
      try {
        var rendered = globalThis.marked.parse(preprocessed);
        if (typeof DOMPurify !== 'undefined') {
          rendered = DOMPurify.sanitize(rendered, { ADD_URI_SAFE_PROTOCOLS: ['wikilink'] });
        }
        return rendered;
      } catch (e) {
        // fall through to escaped plaintext
      }
    }

    return escapeHtml(preprocessed).replace(/\n/g, '<br>');
  }

  function resetView() {
    state.scale = 1;
    if (state.nodes.length === 0) {
      state.translateX = 0;
      state.translateY = 0;
    } else {
      // Compute bounding box of all nodes in world coordinates
      var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      state.nodes.forEach(function (n) {
        if (n.x < minX) minX = n.x;
        if (n.y < minY) minY = n.y;
        if (n.x > maxX) maxX = n.x;
        if (n.y > maxY) maxY = n.y;
      });
      var cx = (minX + maxX) / 2;
      var cy = (minY + maxY) / 2;
      // Center the content bounding box within the viewport
      var rect = state.viewport.getBoundingClientRect();
      state.translateX = rect.width / 2 - cx * state.scale;
      state.translateY = rect.height / 2 - cy * state.scale;
    }
    applyTransform();
    updateZoomLabel();
  }

  function zoomIn() {
    state.scale = Math.min(state.maxScale, state.scale * 1.15);
    applyTransform();
    updateZoomLabel();
  }

  function zoomOut() {
    state.scale = Math.max(state.minScale, state.scale * 0.87);
    applyTransform();
    updateZoomLabel();
  }

  function updateZoomLabel() {
    var label = document.getElementById('spatial-canvas-zoom');
    if (!label) return;
    label.textContent = Math.round(state.scale * 100) + '%';
  }


  function getDocument() {
    return {
      nodes: state.nodes.map(function (n) {
        var serialized = {
          id: n.id,
          title: n.title,
          uri: n.uri,
          x: n.x,
          y: n.y,
          markdown: n.markdown || '',
          collapsed: !!n.collapsed,
        };
        // Only serialize width/height when explicitly set (resized)
        if (n.width !== undefined) serialized.width = n.width;
        if (n.height !== undefined) serialized.height = n.height;
        if (n.showProperties) serialized.showProperties = true;
        // Embed node fields
        if (n.nodeType) serialized.nodeType = n.nodeType;
        if (n.embedConfig) serialized.embedConfig = n.embedConfig;
        return serialized;
      }),
      edges: state.edges.map(function (e) {
        return { id: e.id, source: e.source, target: e.target, label: e.label || '' };
      }),
      viewport: { x: state.translateX, y: state.translateY, zoom: state.scale },
      expandProvenance: state.expandProvenance,
    };
  }

  function applyDocument(document) {
    if (!document || typeof document !== 'object') return;
    if (Array.isArray(document.nodes)) {
      state.nodes = document.nodes.map(function (n) {
        var node = {
          id: String(n.id || ''),
          title: String(n.title || n.id || 'Untitled'),
          uri: String(n.uri || n.id || ''),
          x: Number(n.x || 0),
          y: Number(n.y || 0),
          markdown: String(n.markdown || ''),
          collapsed: !!n.collapsed,
        };
        // Restore width/height only when present — undefined means CSS default (260px)
        if (n.width !== undefined && n.width !== null) node.width = Number(n.width);
        if (n.height !== undefined && n.height !== null) node.height = Number(n.height);
        if (n.showProperties) node.showProperties = true;
        // Restore embed node fields (absent in old sessions → undefined → treated as regular)
        if (n.nodeType) node.nodeType = n.nodeType;
        if (n.embedConfig) node.embedConfig = n.embedConfig;
        return node;
      });
    }
    if (Array.isArray(document.edges)) {
      state.edges = document.edges.map(function (e) {
        return {
          id: String(e.id || (e.source + '->' + e.target)),
          source: String(e.source || ''),
          target: String(e.target || ''),
          label: String(e.label || ''),
        };
      });
    }
    if (document.viewport && typeof document.viewport === 'object') {
      state.translateX = Number(document.viewport.x || 0);
      state.translateY = Number(document.viewport.y || 0);
      state.scale = Number(document.viewport.zoom || 1);
    }
    state.expandProvenance = document.expandProvenance || {};
    renderNodes();
    applyTransform();
    updateZoomLabel();
    // Re-fetch properties for any nodes that were saved with showProperties
    state.nodes.forEach(function (n) {
      if (n.showProperties && !state.propertyCache[n.id]) {
        fetchNodeProperties(n.id, n.uri);
      }
    });
  }

  function setStatus(message, isError) {
    var el = document.getElementById('spatial-canvas-status');
    if (!el) return;
    el.textContent = message || '';
    el.classList.toggle('error', !!isError);
  }

  async function loadSessionList() {
    try {
      var response = await apiFetch('/api/canvas/sessions/list', { silent: true });
      var data = await response.json();
      var sessions = data.sessions || [];
      var activeId = data.active_session_id || null;

      // Populate dropdown
      var select = document.getElementById('canvas-session-select');
      if (select) {
        select.innerHTML = '';
        var newOpt = document.createElement('option');
        newOpt.value = '';
        newOpt.textContent = 'New canvas';
        select.appendChild(newOpt);

        for (var i = 0; i < sessions.length; i++) {
          var opt = document.createElement('option');
          opt.value = sessions[i].id;
          opt.textContent = sessions[i].name;
          select.appendChild(opt);
        }

        if (activeId) {
          select.value = activeId;
        }
      }

      state.currentSessionId = activeId;
      if (activeId) {
        state.canvasId = activeId;
        loadCanvas(true);
      }
    } catch (error) {
      // Session list load failed — fall back to empty canvas
    }
  }

  async function saveSessionAs() {
    if (state.isSaving) return;
    var name = window.SemPKM.prompt('Session name:', '');
    if (!name) return;
    state.isSaving = true;
    try {
      var response = await apiFetch('/api/canvas/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, document: getDocument() }),
        silent: true,
      });
      var data = await response.json();
      var data = await response.json();
      state.currentSessionId = data.session_id;
      state.canvasId = data.session_id;
      await loadSessionList();
      setStatus('Saved as "' + name + '"');
      if (window.SemPKM.showToast) window.SemPKM.showToast('Saved as "' + name + '"');
    } catch (error) {
      setStatus('Save as failed', true);
      if (window.SemPKM.showToast) window.SemPKM.showToast('Save as failed');
    } finally {
      state.isSaving = false;
    }
  }

  async function saveCanvas() {
    if (state.isSaving) return;
    if (!state.currentSessionId) {
      // No session yet — force save-as
      return saveSessionAs();
    }
    state.isSaving = true;
    try {
      var response = await apiFetch('/api/canvas/' + encodeURIComponent(state.canvasId || 'default'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document: getDocument() }),
        silent: true,
      });
      var data = await response.json();
      setStatus('Saved ' + (data.updated_at || ''));
      if (window.SemPKM.showToast) window.SemPKM.showToast('Canvas saved');
    } catch (error) {
      setStatus('Save failed', true);
      if (window.SemPKM.showToast) window.SemPKM.showToast('Canvas save failed');
    } finally {
      state.isSaving = false;
    }
  }

  async function loadCanvas(silent) {
    try {
      var response = await apiFetch('/api/canvas/' + encodeURIComponent(state.canvasId || 'default'), { silent: true });
      var data = await response.json();
      if (data && data.document) {
        var hasContent = Array.isArray(data.document.nodes) && data.document.nodes.length > 0;
        if (hasContent) {
          applyDocument(data.document);
          if (!silent) {
            setStatus('Loaded ' + (data.updated_at || ''));
            if (window.SemPKM.showToast) window.SemPKM.showToast('Canvas loaded');
          }
        }
        // Empty canvas: hint text handles the empty state, no toast needed
      }
    } catch (error) {
      if (!silent) {
        setStatus('Load failed', true);
        if (window.SemPKM.showToast) window.SemPKM.showToast('Canvas load failed');
      }
    }
  }


  function mergeSubgraph(payload) {
    if (!payload || !Array.isArray(payload.nodes)) return;

    var existingNodeIds = {};
    state.nodes.forEach(function (n) { existingNodeIds[n.id] = true; });

    var centerX = (state.viewport ? state.viewport.clientWidth : 900) / 2;
    var centerY = (state.viewport ? state.viewport.clientHeight : 600) / 2;

    payload.nodes.forEach(function (node, idx) {
      var nodeId = String(node.id || '');
      if (!nodeId || existingNodeIds[nodeId]) return;

      var angle = (idx / Math.max(payload.nodes.length, 1)) * Math.PI * 2;
      var radius = 220 + (idx % 5) * 30;

      state.nodes.push({
        id: nodeId,
        title: String(node.label || node.id || 'Resource'),
        uri: nodeId,
        x: Math.round((centerX - state.translateX) / state.scale + Math.cos(angle) * radius),
        y: Math.round((centerY - state.translateY) / state.scale + Math.sin(angle) * radius),
        markdown: '',
      });
      existingNodeIds[nodeId] = true;
      fetchNodeBody(nodeId);
    });

    if (Array.isArray(payload.edges)) {
      var existingEdgeIds = {};
      state.edges.forEach(function (e) { existingEdgeIds[e.id] = true; });
      payload.edges.forEach(function (edge) {
        var source = String(edge.source || '');
        var target = String(edge.target || '');
        var predicate = String(edge.predicate || 'relatedTo');
        if (!source || !target) return;
        var edgeId = source + '|' + predicate + '|' + target;
        if (existingEdgeIds[edgeId]) return;
        state.edges.push({
          id: edgeId,
          source: source,
          target: target,
          label: String(edge.predicate_label || predicate),
        });
        existingEdgeIds[edgeId] = true;
      });
    }

    renderNodes();
    applyTransform();
  }

  // ── Embed picker ───────────────────────────────────────────────
  var embedPickerEl = null;
  var embedPickerActiveTab = 'views';
  var embedPickerOutsideHandler = null;

  function openEmbedPicker(anchorEl) {
    // Toggle: close if already open
    if (embedPickerEl && embedPickerEl.style.display !== 'none') {
      closeEmbedPicker();
      return;
    }
    // Check embed limit before opening
    var embedCount = 0;
    for (var i = 0; i < state.nodes.length; i++) {
      if (state.nodes[i].nodeType === 'embed') embedCount++;
    }
    if (embedCount >= MAX_EMBEDS) {
      if (window.SemPKM.showToast) window.SemPKM.showToast('Maximum of ' + MAX_EMBEDS + ' embeds reached');
      return;
    }
    // Create picker DOM if first open
    if (!embedPickerEl) {
      embedPickerEl = document.createElement('div');
      embedPickerEl.className = 'canvas-embed-picker';
      embedPickerEl.innerHTML = [
        '<div class="canvas-embed-picker-tabs">',
          '<button class="active" data-tab="views">Views</button>',
          '<button data-tab="dashboards">Dashboards</button>',
          '<button data-tab="queries">Queries</button>',
        '</div>',
        '<div class="canvas-embed-picker-body">',
          '<div class="canvas-embed-picker-loading">Loading…</div>',
        '</div>',
      ].join('');
      // Tab switching
      embedPickerEl.querySelector('.canvas-embed-picker-tabs').addEventListener('click', function (e) {
        var btn = e.target.closest('button[data-tab]');
        if (!btn) return;
        embedPickerActiveTab = btn.dataset.tab;
        embedPickerEl.querySelectorAll('.canvas-embed-picker-tabs button').forEach(function (b) {
          b.classList.toggle('active', b.dataset.tab === embedPickerActiveTab);
        });
        fetchEmbedPickerTab(embedPickerActiveTab);
      });
      // Item click
      embedPickerEl.querySelector('.canvas-embed-picker-body').addEventListener('click', function (e) {
        var item = e.target.closest('.canvas-embed-picker-item');
        if (!item) return;
        var config;
        try { config = JSON.parse(item.dataset.config); } catch (err) { return; }
        // Place at viewport center
        var rect = state.viewport.getBoundingClientRect();
        var centerX = rect.left + rect.width / 2;
        var centerY = rect.top + rect.height / 2;
        addEmbedNode(config, centerX, centerY);
        closeEmbedPicker();
      });
      // Append to the anchor wrapper so positioning is relative
      var anchor = anchorEl.closest('.canvas-embed-picker-anchor') || anchorEl.parentNode;
      anchor.appendChild(embedPickerEl);
    }
    embedPickerEl.style.display = '';
    embedPickerActiveTab = 'views';
    embedPickerEl.querySelectorAll('.canvas-embed-picker-tabs button').forEach(function (b) {
      b.classList.toggle('active', b.dataset.tab === 'views');
    });
    fetchEmbedPickerTab('views');
    // Close on outside click (delay to avoid catching the opening click)
    setTimeout(function () {
      embedPickerOutsideHandler = function (e) {
        if (!embedPickerEl.contains(e.target) && !e.target.closest('.canvas-embed-picker-btn')) {
          closeEmbedPicker();
        }
      };
      document.addEventListener('pointerdown', embedPickerOutsideHandler, true);
    }, 0);
  }

  function closeEmbedPicker() {
    if (embedPickerEl) embedPickerEl.style.display = 'none';
    if (embedPickerOutsideHandler) {
      document.removeEventListener('pointerdown', embedPickerOutsideHandler, true);
      embedPickerOutsideHandler = null;
    }
  }

  function fetchEmbedPickerTab(tab) {
    var body = embedPickerEl.querySelector('.canvas-embed-picker-body');
    body.innerHTML = '<div class="canvas-embed-picker-loading">Loading…</div>';

    var urls = {
      views: '/browser/views/available',
      dashboards: '/api/dashboard',
      queries: '/api/sparql/saved',
    };
    var url = urls[tab];
    if (!url) { body.innerHTML = '<div class="canvas-embed-picker-empty">Unknown tab</div>'; return; }

    apiFetch(url, { silent: true })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        // Ensure data is an array (sparql/saved may return object when include_shared=true)
        if (!Array.isArray(data)) data = [];
        if (data.length === 0) {
          body.innerHTML = '<div class="canvas-embed-picker-empty">No items found</div>';
          return;
        }
        var html = data.map(function (item) {
          var config = buildEmbedConfig(tab, item);
          if (!config) return '';
          return '<div class="canvas-embed-picker-item" data-config=\'' + escapeHtml(JSON.stringify(config)) + '\'>' + escapeHtml(config.label) + '</div>';
        }).join('');
        body.innerHTML = html || '<div class="canvas-embed-picker-empty">No items found</div>';
      })
      .catch(function () {
        body.innerHTML = '<div class="canvas-embed-picker-empty">Failed to load</div>';
      });
  }

  function buildEmbedConfig(tab, item) {
    if (tab === 'views') {
      var renderer = item.renderer_type || 'table';
      var specIri = item.spec_iri || '';
      var label = item.label || specIri;
      // Generic views (built-in): spec_iri starts with "generic:" or has no target_class
      // Model-declared views: have a target_class and spec_iri is a full IRI
      var url;
      if (!item.target_class) {
        // Generic view — renderer is the spec itself
        url = '/browser/views/generic/' + encodeURIComponent(renderer) + '?embed=1';
      } else {
        // Model-declared view — use renderer + spec_iri
        url = '/browser/views/' + encodeURIComponent(renderer) + '/' + encodeURIComponent(specIri) + '?embed=1';
      }
      return { type: 'view', id: specIri, url: url, label: label };
    }
    if (tab === 'dashboards') {
      var id = item.id || '';
      var name = item.name || 'Dashboard';
      return { type: 'dashboard', id: id, url: '/browser/dashboard/' + encodeURIComponent(id) + '?embed=1', label: name };
    }
    if (tab === 'queries') {
      var id = item.id || '';
      var name = item.name || 'Query';
      return { type: 'query', id: id, url: '/browser/sparql-result/' + encodeURIComponent(id) + '?embed=1', label: name };
    }
    return null;
  }

  window.SemPKMCanvas = {
    mount: mountCanvas,
    zoomIn: zoomIn,
    zoomOut: zoomOut,
    resetView: resetView,
    save: saveCanvas,
    saveAs: saveSessionAs,
    load: function () { return loadCanvas(false); },
    exportState: getDocument,
    importState: applyDocument,
    addEmbed: addEmbedNode,
    openEmbedPicker: openEmbedPicker,
  };

  document.body.addEventListener('htmx:afterSwap', function (event) {
    if (event && event.target && event.target.querySelector && event.target.querySelector('#spatial-canvas-root')) {
      unbindEvents();
      state.mounted = false;
      mountCanvas();
    }
  });
})();
