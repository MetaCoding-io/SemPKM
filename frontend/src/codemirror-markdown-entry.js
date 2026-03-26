/**
 * CodeMirror Markdown bundle entry point.
 *
 * esbuild bundles this into an IIFE that exposes window.CM_Markdown
 * with all symbols needed by editor.js and vfs-browser.js.
 */
export { EditorView, keymap } from '@codemirror/view';
export { EditorState, Compartment } from '@codemirror/state';
export { basicSetup } from 'codemirror';
export { markdown } from '@codemirror/lang-markdown';
