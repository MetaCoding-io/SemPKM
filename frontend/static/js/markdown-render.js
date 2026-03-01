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

  /**
   * Fetch Markdown from a URL and render it into a target element.
   *
   * @param {string} url      - URL to fetch raw Markdown from (e.g. '/docs/guide/01-what-is-sempkm.md')
   * @param {string} targetId - ID of the element to receive rendered HTML
   */
  window.renderMarkdownFromUrl = function (url, targetId) {
    var target = document.getElementById(targetId);
    if (!target) return;

    target.innerHTML = '<p class="docs-loading">Loading...</p>';

    fetch(url)
      .then(function (response) { return response.text(); })
      .then(function (rawText) {
        var md = getMarked();
        if (!md) {
          // Fallback: show raw text if CDN not loaded
          target.textContent = rawText;
          return;
        }
        var rawHtml = md.parse(rawText);
        if (typeof DOMPurify !== 'undefined') {
          rawHtml = DOMPurify.sanitize(rawHtml);
        }
        target.innerHTML = rawHtml;

        // Rebase relative image paths against the fetch URL so they resolve
        // correctly when the page URL differs (e.g. /guide/ vs /docs/guide/).
        var baseUrl = url.substring(0, url.lastIndexOf('/') + 1);
        target.querySelectorAll('img').forEach(function (img) {
          var src = img.getAttribute('src');
          if (src && !src.startsWith('/') && !src.startsWith('http')) {
            img.setAttribute('src', baseUrl + src);
          }
        });

        // Rewrite relative .md links to use the /guide/ route with htmx
        // so prev/next chapter navigation works without a full page reload.
        target.querySelectorAll('a').forEach(function (a) {
          var href = a.getAttribute('href');
          if (href && href.endsWith('.md') && !href.startsWith('/') && !href.startsWith('http')) {
            a.setAttribute('href', '/guide/' + href);
            a.setAttribute('hx-get', '/guide/' + href);
            a.setAttribute('hx-target', '#app-content');
            a.setAttribute('hx-swap', 'innerHTML');
            a.setAttribute('hx-push-url', 'true');
            htmx.process(a);
          }
        });
      })
      .catch(function () {
        target.innerHTML = '<p class="docs-error">Failed to load document.</p>';
      });
  };
})();
