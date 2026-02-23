/**
 * SemPKM Markdown Rendering Module
 *
 * Client-side Markdown rendering using marked.js with syntax-highlighted
 * code blocks via highlight.js and XSS sanitization via DOMPurify.
 * Provides renderMarkdownBody() for the read-only object view.
 */
(function () {
  'use strict';

  var _marked = null;

  /**
   * Lazily initialize the Marked instance with highlight.js integration.
   * Returns null if CDN libraries are not yet loaded.
   */
  function getMarked() {
    if (_marked) return _marked;

    if (typeof globalThis.marked === 'undefined' ||
        typeof globalThis.markedHighlight === 'undefined') {
      return null;
    }

    var Marked = globalThis.marked.Marked;
    var markedHighlight = globalThis.markedHighlight.markedHighlight;

    _marked = new Marked(
      markedHighlight({
        emptyLangClass: 'hljs',
        langPrefix: 'hljs language-',
        highlight: function (code, lang) {
          if (typeof hljs === 'undefined') return code;
          var language = hljs.getLanguage(lang) ? lang : 'plaintext';
          return hljs.highlight(code, { language: language }).value;
        }
      })
    );

    return _marked;
  }

  /**
   * Render Markdown from a source element into a target element.
   *
   * @param {string} sourceId - ID of the element containing raw Markdown text
   *                            (e.g., a <script type="text/plain"> or <template>)
   * @param {string} targetId - ID of the element to receive rendered HTML
   */
  window.renderMarkdownBody = function (sourceId, targetId) {
    var source = document.getElementById(sourceId);
    var target = document.getElementById(targetId);
    if (!source || !target) return;

    var rawText = source.textContent || '';
    if (!rawText.trim()) {
      target.innerHTML = '';
      return;
    }

    var md = getMarked();
    if (!md) {
      // Fallback: show raw text if libraries not loaded
      target.textContent = rawText;
      return;
    }

    var rawHtml = md.parse(rawText);

    // Sanitize to prevent XSS from user-generated Markdown content
    if (typeof DOMPurify !== 'undefined') {
      rawHtml = DOMPurify.sanitize(rawHtml);
    }

    target.innerHTML = rawHtml;
  };
})();
