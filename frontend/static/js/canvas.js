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
    nodes: [
      {
        id: 'urn:sempkm:model:basic-pkm:seed-note-arch',
        title: 'Architecture Decision',
        uri: 'urn:sempkm:model:basic-pkm:seed-note-arch',
        x: 160,
        y: 120,
        markdown: '## Architecture Decision\n\n- Adopt **Track A** for packaging.\n- Add `React Flow` island in workspace.\n\n[Open project node](urn:sempkm:model:basic-pkm:seed-project-kernel)',
      },
      {
        id: 'urn:sempkm:model:basic-pkm:seed-project-kernel',
        title: 'Project: Spatial Canvas Beta',
        uri: 'urn:sempkm:model:basic-pkm:seed-project-kernel',
        x: 540,
        y: 300,
        markdown: '### Spatial Canvas Beta\n\nThis project tracks:\n1. Canvas persistence\n2. RDF subgraph loading\n3. Markdown anchors\n\nSee [Architecture Decision](urn:sempkm:model:basic-pkm:seed-note-arch).',
      }
    ],
    edges: [
      { id: 'link-1', source: 'urn:sempkm:model:basic-pkm:seed-note-arch', target: 'urn:sempkm:model:basic-pkm:seed-project-kernel', label: 'related to' }
    ]
  };

  function mountCanvas() {
    var root = document.getElementById('spatial-canvas-root');
    if (!root) return;
    if (state.mounted) return;

    var viewport = root.querySelector('.spatial-canvas-viewport');
    var layer = root.querySelector('.spatial-canvas-layer');
    if (!viewport || !layer) return;

    state.viewport = viewport;
    state.layer = layer;

    renderNodes();
    applyTransform();
    bindEvents();
    state.mounted = true;
  }

  function bindEvents() {
    state.viewport.addEventListener('wheel', onWheel, { passive: false });
    state.viewport.addEventListener('pointerdown', onPointerDown);
    window.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
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
    if (event.target && event.target.closest && event.target.closest('.spatial-node-markdown a')) {
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
      return [
        '<article class="spatial-node" data-node-id="', escapeHtml(node.id), '" style="left:', node.x, 'px; top:', node.y, 'px;">',
          '<header class="spatial-node-header">', escapeHtml(node.title), '</header>',
          '<div class="spatial-node-uri">', escapeHtml(node.uri), '</div>',
          '<div class="spatial-node-markdown">', renderMarkdown(node.markdown || ''), '</div>',
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

  window.SemPKMCanvas = {
    mount: mountCanvas,
    zoomIn: zoomIn,
    zoomOut: zoomOut,
    resetView: resetView,
  };

  document.body.addEventListener('htmx:afterSwap', function (event) {
    if (event && event.target && event.target.querySelector && event.target.querySelector('#spatial-canvas-root')) {
      state.mounted = false;
      mountCanvas();
    }
  });
})();
