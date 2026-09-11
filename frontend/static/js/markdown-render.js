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

  // ── Callouts: blockquotes that open with a bold label become Bootstrap-style
  //    alerts. Warning/Important/Caution/Danger -> red with "!", Tip/Example ->
  //    green with a lightbulb, any other labelled quote (Note, ...) -> blue info.
  var CALLOUT_ICONS = {
    warning: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="7" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>',
    tip: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M9 18h6"/><path d="M10 22h4"/><path d="M12 2a7 7 0 0 0-4 12.7c.6.5 1 1.3 1 2.3h6c0-1 .4-1.8 1-2.3A7 7 0 0 0 12 2z"/></svg>',
    note: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><line x1="12" y1="11" x2="12" y2="17"/><line x1="12" y1="7" x2="12.01" y2="7"/></svg>'
  };
  function decorateCallouts(root) {
    if (!root || !root.querySelectorAll) return;
    root.querySelectorAll('blockquote').forEach(function (bq) {
      if (bq.classList.contains('callout')) return;
      var first = bq.firstElementChild;
      var strong = first && first.tagName === 'P' ? first.firstElementChild : null;
      if (!strong || strong.tagName !== 'STRONG' || strong !== first.firstChild) return;
      var label = (strong.textContent || '').trim().replace(/[:.!]$/, '');
      var kind = /^(warning|important|caution|danger)/i.test(label) ? 'warning'
               : /^(tip|example)/i.test(label) ? 'tip' : 'note';
      bq.classList.add('callout', 'callout-' + kind);
      var icon = document.createElement('span');
      icon.className = 'callout-icon';
      icon.innerHTML = CALLOUT_ICONS[kind];
      bq.insertBefore(icon, bq.firstChild);
    });
  }

  window.SemPKM.decorateCallouts = decorateCallouts;

  /**
   * Render a Markdown string into a target element.
   *
   * @param {string} rawText  - Raw Markdown text
   * @param {string} targetId - ID of the element to receive rendered HTML
   */
  window.SemPKM.renderMarkdownText = function (rawText, targetId) {
    var target = document.getElementById(targetId);
    if (!target) return;

    rawText = rawText || '';
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
   * Render Markdown from a source element into a target element.
   *
   * @param {string} sourceId - ID of the element containing raw Markdown text
   *                            (e.g., a <script type="text/plain"> or <template>)
   * @param {string} targetId - ID of the element to receive rendered HTML
   */
  window.SemPKM.renderMarkdownBody = function (sourceId, targetId) {
    var source = document.getElementById(sourceId);
    var target = document.getElementById(targetId);
    if (!source || !target) return;

    window.SemPKM.renderMarkdownText(source.textContent || '', targetId);
  };

  /**
   * Render Markdown carried as a JSON string in a
   * <script type="application/json"> element. Unlike text/plain sources,
   * JSON-encoded text survives HTML autoescaping byte-for-byte, so
   * code blocks containing < > & render exactly as authored.
   *
   * @param {string} sourceId - ID of the <script type="application/json"> element
   * @param {string} targetId - ID of the element to receive rendered HTML
   */
  window.SemPKM.renderMarkdownJson = function (sourceId, targetId) {
    var source = document.getElementById(sourceId);
    var target = document.getElementById(targetId);
    if (!source || !target) return;

    var rawText = '';
    try {
      rawText = JSON.parse(source.textContent || '""');
    } catch (e) {
      rawText = source.textContent || '';
    }
    if (typeof rawText !== 'string') rawText = String(rawText);
    window.SemPKM.renderMarkdownText(rawText, targetId);
    decorateCallouts(target);
  };

  /**
   * Fetch Markdown from a URL and render it into a target element.
   *
   * @param {string} url      - URL to fetch raw Markdown from (e.g. '/docs/guide/01-what-is-sempkm.md')
   * @param {string} targetId - ID of the element to receive rendered HTML
   */
  window.SemPKM.renderMarkdownFromUrl = function (url, targetId) {
    var target = document.getElementById(targetId);
    if (!target) return;

    target.innerHTML = '<p class="docs-loading">Loading...</p>';

    apiFetch(url, { silent: true })
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
        decorateCallouts(target);

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
