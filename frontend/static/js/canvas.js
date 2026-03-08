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
    nodes: [],
    edges: [],
    expandProvenance: {},
    canvasId: 'default',
    isSaving: false,
    currentSessionId: null
  };

  // Inline SVG icons — avoid Lucide re-scan on every renderNodes() call
  var SVG_CHEVRON = '<svg class="spatial-icon spatial-icon-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"></polyline></svg>';
  var SVG_PLUS = '<svg class="spatial-icon spatial-icon-plus" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>';
  var SVG_X = '<svg class="spatial-icon spatial-icon-x" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>';

  function mountCanvas() {
    var root = document.getElementById('spatial-canvas-root');
    if (!root) return;
    if (state.mounted) return;

    var viewport = root.querySelector('.spatial-canvas-viewport');
    var layer = root.querySelector('.spatial-canvas-layer');
    if (!viewport || !layer) return;

    state.viewport = viewport;
    state.layer = layer;
    state.canvasId = root.dataset.canvasId || 'default';

    renderNodes();
    applyTransform();
    bindEvents();
    state.mounted = true;

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
        fetch('/api/canvas/sessions/' + encodeURIComponent(sessionId) + '/activate', {method: 'PUT'});
        loadCanvas(false);
      });
    }

    loadSessionList();
  }

  function bindEvents() {
    state.viewport.addEventListener('wheel', onWheel, { passive: false });
    state.viewport.addEventListener('pointerdown', onPointerDown);
    state.layer.addEventListener('click', onLayerClick);
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
      if (window.showToast) window.showToast('Already on canvas');
      return;
    }
    var world = screenToWorld(clientX, clientY);
    state.nodes.push({
      id: iri,
      title: label || 'Resource',
      uri: iri,
      x: Math.round(world.x),
      y: Math.round(world.y),
      markdown: '',
      collapsed: false,
    });
    renderNodes();
    setStatus('Added: ' + (label || iri));
    fetchNodeBody(iri);
  }

  function fetchNodeBody(iri) {
    fetch('/api/canvas/body?iri=' + encodeURIComponent(iri))
      .then(function (r) { return r.ok ? r.json() : null; })
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

  function onDragOver(event) {
    if (!event.dataTransfer.types || event.dataTransfer.types.indexOf('text/iri') === -1) return;
    if (!isOverCanvas(event)) {
      state.viewport.classList.remove('canvas-drop-active');
      lastDragOverCanvas = null;
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    event.dataTransfer.dropEffect = 'copy';
    state.viewport.classList.add('canvas-drop-active');
    lastDragOverCanvas = { x: event.clientX, y: event.clientY };
  }

  function onDragLeave(event) {
    if (!isOverCanvas(event)) {
      state.viewport.classList.remove('canvas-drop-active');
      lastDragOverCanvas = null;
    }
  }

  function onDrop(event) {
    if (!isOverCanvas(event)) return;
    event.preventDefault();
    event.stopPropagation();
    state.viewport.classList.remove('canvas-drop-active');
    lastDragOverCanvas = null;
    var iri = event.dataTransfer.getData('text/iri');
    var label = event.dataTransfer.getData('text/label');
    addNodeFromDrag(iri, label, event.clientX, event.clientY);
  }

  function onDragEnd(event) {
    // Always clean up visual state.
    state.viewport.classList.remove('canvas-drop-active');
    // Fallback: if drop never fired but we had a valid position over the
    // canvas, use the side-channel payload set by tree_children.html.
    if (lastDragOverCanvas && window.__canvasDragPayload) {
      var payload = window.__canvasDragPayload;
      addNodeFromDrag(payload.iri, payload.label, lastDragOverCanvas.x, lastDragOverCanvas.y);
    }
    lastDragOverCanvas = null;
    window.__canvasDragPayload = null;
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
    if (event.target && event.target.closest && (event.target.closest('.spatial-node-markdown a') || event.target.closest('.spatial-node-chevron') || event.target.closest('.spatial-node-expand') || event.target.closest('.spatial-node-delete'))) {
      return;
    }

    var node = event.target.closest('.spatial-node');
    if (node) {
      state.nodeDragId = node.dataset.nodeId;
      var model = findNode(state.nodeDragId);
      if (!model) return;

      var world = screenToWorld(event.clientX, event.clientY);
      state.nodeDragOffsetX = world.x - model.x;
      state.nodeDragOffsetY = world.y - model.y;
      node.classList.add('dragging');
      return;
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

    var link = event.target.closest('.spatial-node-markdown a');
    if (link) {
      event.preventDefault();
      var href = link.getAttribute('href') || '';
      var sourceEl = link.closest('.spatial-node');
      var source = sourceEl ? findNode(sourceEl.dataset.nodeId) : null;
      if (!href) return;
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
      var response = await fetch('/api/canvas/subgraph?root_uri=' + encodeURIComponent(model.uri) + '&depth=1');
      if (!response.ok) throw new Error('HTTP ' + response.status);
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
        var radius = 200;
        state.nodes.push({
          id: nid,
          title: String(node.label || node.id || 'Resource'),
          uri: nid,
          x: Math.round(model.x + Math.cos(angle) * radius),
          y: Math.round(model.y + Math.sin(angle) * radius),
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
    if (state.nodeDragId) {
      var node = findNode(state.nodeDragId);
      if (!node) return;
      var world = screenToWorld(event.clientX, event.clientY);
      node.x = Math.round(world.x - state.nodeDragOffsetX);
      node.y = Math.round(world.y - state.nodeDragOffsetY);
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
    if (state.nodeDragId) {
      var nodeEl = state.layer.querySelector('.spatial-node.dragging');
      if (nodeEl) nodeEl.classList.remove('dragging');
    }

    state.nodeDragId = null;
    state.isPanning = false;
    if (state.viewport) state.viewport.classList.remove('is-panning');
  }

  function renderNodes() {
    if (!state.layer) return;

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
      var isExpanded = !!state.expandProvenance[node.id];
      var isOpen = !node.collapsed;
      return [
        '<article class="spatial-node', (node.collapsed ? ' is-collapsed' : ''), (isExpanded ? ' is-expanded' : ''), '" data-node-id="', escapeHtml(node.id), '" style="left:', node.x, 'px; top:', node.y, 'px;">',
          '<header class="spatial-node-header">',
            '<button class="spatial-node-chevron', (isOpen ? ' is-open' : ''), '" type="button" title="Toggle body">', SVG_CHEVRON, '</button>',
            '<span class="spatial-node-title">', escapeHtml(node.title), '</span>',
            '<button class="spatial-node-expand" type="button" title="Expand neighbors">', SVG_PLUS, '</button>',
            '<button class="spatial-node-delete" type="button" title="Remove from canvas">', SVG_X, '</button>',
          '</header>',
          '<div class="spatial-node-uri">', escapeHtml(node.uri), '</div>',
          (node.collapsed ? '' : '<div class="spatial-node-markdown">' + renderMarkdown(node.markdown || '') + '</div>'),
        '</article>'
      ].join('');
    }).join('');

    state.layer.innerHTML = [
      '<svg class="spatial-edges" width="4000" height="4000" viewBox="0 0 4000 4000" aria-hidden="true">',
      '<defs><marker id="spatial-edge-arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto"><path d="M0,0 L0,6 L6,3 z" class="spatial-edge-arrow-path"></path></marker></defs>',
      edgesHtml,
      '</svg>',
      nodesHtml
    ].join('');

    var nodeBoxes = {};
    state.layer.querySelectorAll('.spatial-node').forEach(function (el) {
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
        var targetNode = findNode(href);

        anchorDotsHtml.push('<circle class="spatial-anchor-dot" cx="' + Math.round(anchorX) + '" cy="' + Math.round(anchorY) + '" r="3"></circle>');

        if (targetNode) {
          markdownEdges.push({
            id: 'md|' + sourceId + '|' + href + '|' + idx,
            source: sourceId,
            target: href,
            label: 'link',
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

    var svgHtml = [
      '<svg class="spatial-edges" width="5000" height="5000" viewBox="0 0 5000 5000" aria-hidden="true">',
      '<defs><marker id="spatial-edge-arrow" markerWidth="8" markerHeight="8" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L7,3 z" class="spatial-edge-arrow-path"></path></marker></defs>',
      edgesHtml,
      anchorDotsHtml.join(''),
      '</svg>'
    ].join('');

    state.layer.insertAdjacentHTML('afterbegin', svgHtml);

    // Toggle hint visibility based on whether canvas has nodes
    var hint = document.getElementById('canvas-hint');
    if (hint) hint.style.display = state.nodes.length > 0 ? 'none' : '';
  }

  function applyTransform() {
    if (!state.layer) return;
    state.layer.style.transform = 'translate(' + state.translateX + 'px, ' + state.translateY + 'px) scale(' + state.scale + ')';
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

    if (typeof globalThis.marked !== 'undefined') {
      try {
        var rendered = globalThis.marked.parse(markdownText);
        if (typeof DOMPurify !== 'undefined') {
          rendered = DOMPurify.sanitize(rendered);
        }
        return rendered;
      } catch (e) {
        // fall through to escaped plaintext
      }
    }

    return escapeHtml(markdownText).replace(/\n/g, '<br>');
  }

  function resetView() {
    state.scale = 1;
    state.translateX = 0;
    state.translateY = 0;
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
        return {
          id: n.id,
          title: n.title,
          uri: n.uri,
          x: n.x,
          y: n.y,
          markdown: n.markdown || '',
          collapsed: !!n.collapsed,
        };
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
        return {
          id: String(n.id || ''),
          title: String(n.title || n.id || 'Untitled'),
          uri: String(n.uri || n.id || ''),
          x: Number(n.x || 0),
          y: Number(n.y || 0),
          markdown: String(n.markdown || ''),
          collapsed: !!n.collapsed,
        };
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
  }

  function setStatus(message, isError) {
    var el = document.getElementById('spatial-canvas-status');
    if (!el) return;
    el.textContent = message || '';
    el.classList.toggle('error', !!isError);
  }

  async function loadSessionList() {
    try {
      var response = await fetch('/api/canvas/sessions/list');
      if (!response.ok) throw new Error('HTTP ' + response.status);
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
    var name = window.prompt('Session name:', '');
    if (!name) return;
    state.isSaving = true;
    try {
      var response = await fetch('/api/canvas/sessions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, document: getDocument() }),
      });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      var data = await response.json();
      state.currentSessionId = data.session_id;
      state.canvasId = data.session_id;
      await loadSessionList();
      setStatus('Saved as "' + name + '"');
      if (window.showToast) window.showToast('Saved as "' + name + '"');
    } catch (error) {
      setStatus('Save as failed', true);
      if (window.showToast) window.showToast('Save as failed');
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
      var response = await fetch('/api/canvas/' + encodeURIComponent(state.canvasId || 'default'), {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ document: getDocument() }),
      });
      if (!response.ok) throw new Error('HTTP ' + response.status);
      var data = await response.json();
      setStatus('Saved ' + (data.updated_at || ''));
      if (window.showToast) window.showToast('Canvas saved');
    } catch (error) {
      setStatus('Save failed', true);
      if (window.showToast) window.showToast('Canvas save failed');
    } finally {
      state.isSaving = false;
    }
  }

  async function loadCanvas(silent) {
    try {
      var response = await fetch('/api/canvas/' + encodeURIComponent(state.canvasId || 'default'));
      if (!response.ok) throw new Error('HTTP ' + response.status);
      var data = await response.json();
      if (data && data.document) {
        var hasContent = Array.isArray(data.document.nodes) && data.document.nodes.length > 0;
        if (hasContent) {
          applyDocument(data.document);
          if (!silent) {
            setStatus('Loaded ' + (data.updated_at || ''));
            if (window.showToast) window.showToast('Canvas loaded');
          }
        }
        // Empty canvas: hint text handles the empty state, no toast needed
      }
    } catch (error) {
      if (!silent) {
        setStatus('Load failed', true);
        if (window.showToast) window.showToast('Canvas load failed');
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
  };

  document.body.addEventListener('htmx:afterSwap', function (event) {
    if (event && event.target && event.target.querySelector && event.target.querySelector('#spatial-canvas-root')) {
      state.mounted = false;
      mountCanvas();
    }
  });
})();
