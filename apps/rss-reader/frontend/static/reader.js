/**
 * RSS Reader — client-side helpers
 *
 * Handles:
 * - Markdown rendering after htmx swaps content into the reading pane
 * - Lucide icon refresh after any htmx swap within the reader
 * - Keyboard navigation (j/k) for article list traversal
 */
(function () {
    'use strict';

    var READER_ID = 'rss-reader-container';

    // ── htmx afterSwap: render markdown in reading pane ──

    document.body.addEventListener('htmx:afterSwap', function (evt) {
        var target = evt.detail.target;
        if (!target) return;

        // Markdown rendering — only inside the reading pane
        var readingPane = document.getElementById('rss-reading-pane');
        if (readingPane && readingPane.contains(target)) {
            // Find markdown source/target pairs inside the swapped content
            var sources = readingPane.querySelectorAll('script[type="text/plain"][id^="md-source-"]');
            for (var i = 0; i < sources.length; i++) {
                var sourceId = sources[i].id;
                var targetId = sourceId.replace('md-source-', 'md-target-');
                if (document.getElementById(targetId) && typeof window.renderMarkdownBody === 'function') {
                    window.renderMarkdownBody(sourceId, targetId);
                }
            }
        }

        // Lucide icon refresh — for any swap inside the reader container
        var container = document.getElementById(READER_ID);
        if (container && container.contains(target) && typeof lucide !== 'undefined' && lucide.createIcons) {
            lucide.createIcons();
        }
    });

    // ── Keyboard navigation: j/k for next/prev article ──

    document.addEventListener('keydown', function (evt) {
        // Skip if user is typing in an input/textarea
        var tag = (evt.target.tagName || '').toLowerCase();
        if (tag === 'input' || tag === 'textarea' || tag === 'select' || evt.target.isContentEditable) {
            return;
        }

        // Only act when the reader container is visible
        var container = document.getElementById(READER_ID);
        if (!container || container.offsetParent === null) return;

        var articleItems = container.querySelectorAll('.rss-article-item');
        if (articleItems.length === 0) return;

        var activeItem = container.querySelector('.rss-article-item.active');
        var currentIndex = -1;
        if (activeItem) {
            currentIndex = Array.prototype.indexOf.call(articleItems, activeItem);
        }

        var nextIndex = -1;

        if (evt.key === 'j') {
            // Next article
            nextIndex = currentIndex < articleItems.length - 1 ? currentIndex + 1 : currentIndex;
        } else if (evt.key === 'k') {
            // Previous article
            nextIndex = currentIndex > 0 ? currentIndex - 1 : currentIndex;
        } else {
            return;
        }

        if (nextIndex >= 0 && nextIndex !== currentIndex) {
            articleItems[nextIndex].click();
        }
    });

})();
