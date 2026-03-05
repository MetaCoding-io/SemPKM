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
      },
      {
        id: 'urn:sempkm:model:basic-pkm:seed-project-kernel',
        title: 'SemPKM Kernel Project',
        uri: 'urn:sempkm:model:basic-pkm:seed-project-kernel',
        x: 540,
        y: 300,
      }
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

    var html = state.nodes.map(function (node) {
      return [
        '<article class="spatial-node" data-node-id="', escapeHtml(node.id), '" style="left:', node.x, 'px; top:', node.y, 'px;">',
          '<header class="spatial-node-header">', escapeHtml(node.title), '</header>',
          '<div class="spatial-node-uri">', escapeHtml(node.uri), '</div>',
        '</article>'
      ].join('');
    }).join('');

    state.layer.innerHTML = html;
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
