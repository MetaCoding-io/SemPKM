/**
 * dropdown-dismiss.js — Global dismiss handlers for suggestion dropdowns.
 *
 * Covers: reference fields (.reference-field), tag fields (.tag-autocomplete-field),
 * and builder fields (.builder-suggestions) in dashboard/workflow builders.
 *
 * Two behaviors:
 *   1. Click outside any open dropdown → dismiss all
 *   2. Escape key while any dropdown is open → dismiss all
 *
 * Uses mousedown (not click) so the dropdown clears before the click target
 * receives focus — prevents a stale dropdown from lingering during focus shift.
 */
(function () {
    'use strict';

    /** Clear every non-empty .suggestions-dropdown in the document. */
    function _dismissAllDropdowns() {
        var open = document.querySelectorAll('.suggestions-dropdown:not(:empty)');
        for (var i = 0; i < open.length; i++) {
            open[i].innerHTML = '';
        }
    }

    /**
     * Mousedown anywhere outside a dropdown or its associated input field
     * dismisses all open suggestion dropdowns.
     */
    document.addEventListener('mousedown', function (e) {
        // Inside a suggestion dropdown itself — let the click handler on the
        // suggestion-item fire normally.
        if (e.target.closest('.suggestions-dropdown')) return;

        // Inside a reference field wrapper (input + dropdown live together)
        if (e.target.closest('.reference-field')) return;

        // Inside a tag autocomplete wrapper
        if (e.target.closest('.tag-autocomplete-field')) return;

        _dismissAllDropdowns();
    });

    /**
     * Escape key dismisses all open dropdowns. Does NOT call preventDefault —
     * Escape should still bubble for modal close, etc.
     */
    document.addEventListener('keydown', function (e) {
        if (e.key !== 'Escape') return;

        var open = document.querySelectorAll('.suggestions-dropdown:not(:empty)');
        if (!open.length) return;

        _dismissAllDropdowns();

        // Refocus the nearest associated input so the user can keep typing.
        var active = document.activeElement;
        if (active && (active.classList.contains('reference-search') ||
                       active.closest('.tag-autocomplete-field') ||
                       active.closest('.reference-field'))) {
            // Already focused on the right input — nothing to do.
            return;
        }
        // If focus was inside a dropdown (shouldn't normally happen), move it
        // to the first reference/tag input on the page as a fallback.
        var firstInput = document.querySelector('.reference-search, .tag-autocomplete-field input');
        if (firstInput) firstInput.focus();
    });

    // Export for programmatic use (e.g., before opening a new dropdown).
    window.SemPKM = window.SemPKM || {};
    window.SemPKM.dismissAllDropdowns = _dismissAllDropdowns;
})();
