/**
 * SemPKM CodeMirror 6 Markdown Editor
 *
 * ESM module that initializes CodeMirror 6 with Markdown syntax highlighting,
 * Ctrl+S save handling, and dirty state tracking. Uses esm.sh with pinned
 * versions for reliable CDN imports.
 *
 * If esm.sh causes issues, fall back to a local bundle strategy:
 * 1. npm install codemirror @codemirror/lang-markdown @codemirror/view
 * 2. Bundle with esbuild/rollup to /js/codemirror-bundle.js
 * 3. Change imports below to local paths
 */

import { EditorView } from "https://esm.sh/@codemirror/view@6.35.0?pin=v135";
import { keymap } from "https://esm.sh/@codemirror/view@6.35.0?pin=v135";
import { EditorState } from "https://esm.sh/@codemirror/state@6.4.1?pin=v135";
import { basicSetup } from "https://esm.sh/@codemirror/basic-setup@0.19.1?pin=v135";
import { markdown } from "https://esm.sh/@codemirror/lang-markdown@6.2.5?pin=v135";

// Track active editor instances by object IRI
var editors = {};

/**
 * Initialize a CodeMirror 6 editor in the specified container.
 *
 * @param {string} containerId - DOM element ID for the editor container
 * @param {string} initialContent - Initial Markdown text content
 * @param {string} objectIri - Object IRI for save targeting and dirty tracking
 * @returns {EditorView} The created editor view instance
 */
export function initEditor(containerId, initialContent, objectIri) {
  var container = document.getElementById(containerId);
  if (!container) {
    console.warn('Editor container not found:', containerId);
    return null;
  }

  // Destroy existing editor for this object if present
  if (editors[objectIri]) {
    editors[objectIri].destroy();
    delete editors[objectIri];
  }

  // Clear container content
  container.innerHTML = '';

  // Track whether content has changed from the initial state
  var savedContent = initialContent || '';

  var view = new EditorView({
    state: EditorState.create({
      doc: initialContent || '',
      extensions: [
        basicSetup,
        markdown(),
        keymap.of([
          {
            key: 'Mod-s',
            run: function () {
              saveBody(objectIri, view);
              return true;
            }
          }
        ]),
        // Update listener: track dirty state on document changes
        EditorView.updateListener.of(function (update) {
          if (update.docChanged) {
            var currentContent = update.state.doc.toString();
            if (currentContent !== savedContent) {
              if (typeof window.markDirty === 'function') {
                window.markDirty(objectIri);
              }
            }
          }
        })
      ]
    }),
    parent: container
  });

  editors[objectIri] = view;

  // Register cleanup for htmx:beforeCleanupElement
  if (typeof window.registerCleanup === 'function') {
    window.registerCleanup(containerId, function() {
      if (editors[objectIri]) {
        editors[objectIri].destroy();
        delete editors[objectIri];
      }
    });
  }

  // Store savedContent reference on the view for access during save
  view._sempkmSavedContent = savedContent;

  return view;
}

/**
 * Save the editor body content to the server.
 *
 * POSTs to /browser/objects/{objectIri}/body via fetch.
 * On success, marks the tab clean and updates the saved content reference.
 *
 * @param {string} objectIri - The object IRI to save body for
 * @param {EditorView} view - The CodeMirror view instance
 */
async function saveBody(objectIri, view) {
  var content = view.state.doc.toString();
  var statusEl = document.getElementById('editor-status');

  if (statusEl) {
    statusEl.textContent = 'Saving...';
    statusEl.className = 'editor-status saving';
  }

  try {
    var response = await fetch('/browser/objects/' + encodeURIComponent(objectIri) + '/body', {
      method: 'POST',
      headers: { 'Content-Type': 'text/plain' },
      body: content
    });

    if (response.ok) {
      // Update saved content reference
      view._sempkmSavedContent = content;

      if (typeof window.markClean === 'function') {
        window.markClean(objectIri);
      }

      if (statusEl) {
        statusEl.textContent = 'Saved';
        statusEl.className = 'editor-status saved';
        setTimeout(function () {
          statusEl.textContent = '';
          statusEl.className = 'editor-status';
        }, 2000);
      }
    } else {
      throw new Error('Save failed: ' + response.status);
    }
  } catch (err) {
    console.error('Body save error:', err);
    if (statusEl) {
      statusEl.textContent = 'Save failed';
      statusEl.className = 'editor-status error';
    }
  }
}

/**
 * Execute a toolbar formatting action on the active editor.
 *
 * @param {string} action - The action name (bold, italic, heading, link)
 */
export function editorAction(action) {
  // Find the active editor (from the currently visible object tab)
  var tab = document.querySelector('.object-tab');
  if (!tab) return;

  var iri = tab.dataset.objectIri;
  var view = editors[iri];
  if (!view) return;

  var state = view.state;
  var selection = state.selection.main;
  var selectedText = state.sliceDoc(selection.from, selection.to);

  var replacement = '';
  switch (action) {
    case 'bold':
      replacement = '**' + (selectedText || 'bold text') + '**';
      break;
    case 'italic':
      replacement = '_' + (selectedText || 'italic text') + '_';
      break;
    case 'heading':
      replacement = '## ' + (selectedText || 'Heading');
      break;
    case 'link':
      replacement = '[' + (selectedText || 'link text') + '](url)';
      break;
    default:
      return;
  }

  view.dispatch({
    changes: { from: selection.from, to: selection.to, insert: replacement }
  });
  view.focus();
}

/**
 * Get the editor view for a given object IRI.
 *
 * @param {string} objectIri - The object IRI
 * @returns {EditorView|null} The editor view or null
 */
export function getEditor(objectIri) {
  return editors[objectIri] || null;
}

/**
 * Destroy the editor for a given object IRI.
 *
 * @param {string} objectIri - The object IRI
 */
export function destroyEditor(objectIri) {
  if (editors[objectIri]) {
    editors[objectIri].destroy();
    delete editors[objectIri];
  }
}

// Expose functions globally for use from non-module scripts and onclick handlers
window.initEditor = initEditor;
window.editorAction = editorAction;
window.getEditor = getEditor;
window.destroyEditor = destroyEditor;
