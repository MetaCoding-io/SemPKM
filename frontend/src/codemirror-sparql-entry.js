/**
 * CodeMirror SPARQL bundle entry point.
 *
 * esbuild bundles this into an IIFE that exposes window.CM_Sparql
 * with all symbols needed by sparql-console.js.
 */
export { EditorView, keymap } from '@codemirror/view';
export { EditorState, Compartment } from '@codemirror/state';
export { basicSetup } from 'codemirror';
export { autocompletion } from '@codemirror/autocomplete';

// Re-export sparql language support
import { sparql } from 'codemirror-lang-sparql';
export { sparql };
