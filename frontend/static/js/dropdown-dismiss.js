/**
 * dropdown-dismiss.js — Global dismiss + repositioning for suggestion dropdowns.
 *
 * Covers: reference fields (.reference-field), tag fields (.tag-autocomplete-field),
 * and builder fields (.builder-suggestions) in dashboard/workflow builders.
 *
 * Behaviors:
 *   1. Click outside any open dropdown → dismiss all
 *   2. Escape key while any dropdown is open → dismiss all
 *   3. Dropdown near panel edge → reposition with position:fixed to escape
 *      overflow:hidden/auto ancestors (dockview panels). Flips above input
 *      when insufficient space below.
 *   4. Scroll or resize while dropdown is open → dismiss all
 *
 * Uses mousedown (not click) so the dropdown clears before the click target
 * receives focus — prevents a stale dropdown from lingering during focus shift.
 */
(function () {
    'use strict';

    /* ── Reposition helpers ─────────────────────────────────────── */

    /** Minimum viewport pixels needed below input to show dropdown downward. */
    var MIN_SPACE_BELOW = 220; // max-height 200px + 20px margin

    /**
     * Find the associated input element for a .suggestions-dropdown.
     * Returns null for builder dropdowns (they have .builder-suggestions
     * and render inside modal-like containers that don't clip).
     */
    function _findInputForDropdown(dropdown) {
        // Builder dropdowns — skip repositioning entirely.
        if (dropdown.classList.contains('builder-suggestions')) return null;

        var refField = dropdown.closest('.reference-field');
        if (refField) return refField.querySelector('.reference-search');

        var tagField = dropdown.closest('.tag-autocomplete-field');
        if (tagField) return tagField.querySelector('input');

        return null;
    }

    /**
     * Find the containing block for position:fixed elements.
     * CSS `contain: layout` (used by dockview) creates a new containing block,
     * making position:fixed relative to that ancestor instead of the viewport.
     * Returns the containing block's rect, or a zero-origin rect if none exists.
     */
    function _getFixedContainingBlockRect(el) {
        var ancestor = el.parentElement;
        while (ancestor && ancestor !== document.documentElement) {
            var cs = getComputedStyle(ancestor);
            // These CSS properties create a new containing block for fixed elements
            if ((cs.contain && cs.contain !== 'none') ||
                (cs.transform && cs.transform !== 'none') ||
                (cs.willChange === 'transform') ||
                (cs.filter && cs.filter !== 'none') ||
                (cs.perspective && cs.perspective !== 'none')) {
                return ancestor.getBoundingClientRect();
            }
            ancestor = ancestor.parentElement;
        }
        // No containing block found — fixed is relative to viewport
        return { left: 0, top: 0, bottom: window.innerHeight, right: window.innerWidth };
    }

    /**
     * Position a dropdown using position:fixed so it escapes overflow ancestors.
     * Measures the input's viewport rect and places the dropdown directly
     * below (or above if near the bottom edge).
     *
     * Accounts for CSS `contain: layout` on dockview which creates a new
     * containing block — fixed coordinates must be relative to that block,
     * not the viewport.
     */
    function _repositionDropdown(dropdown) {
        var input = _findInputForDropdown(dropdown);
        if (!input) return;

        var rect = input.getBoundingClientRect();
        var cbRect = _getFixedContainingBlockRect(dropdown);

        // Convert viewport coordinates to containing-block-relative coordinates
        var relLeft = rect.left - cbRect.left;
        var relTop = rect.top - cbRect.top;
        var relBottom = rect.bottom - cbRect.top;
        var cbHeight = cbRect.bottom - cbRect.top;

        var spaceBelow = window.innerHeight - rect.bottom;

        dropdown.style.position = 'fixed';
        dropdown.style.left = relLeft + 'px';
        dropdown.style.right = 'auto'; // override CSS right:0
        dropdown.style.width = rect.width + 'px';
        dropdown.style.maxHeight = '200px';

        if (spaceBelow < MIN_SPACE_BELOW) {
            // Flip above: bottom edge aligns with input's top
            dropdown.style.top = 'auto';
            dropdown.style.bottom = (cbHeight - relTop) + 'px';
        } else {
            // Normal: top edge aligns with input's bottom
            dropdown.style.top = relBottom + 'px';
            dropdown.style.bottom = 'auto';
        }
    }

    /** Remove inline positioning styles so CSS defaults take over again. */
    function _resetDropdownPosition(dropdown) {
        dropdown.style.cssText = '';
    }

    /* ── Dismiss ────────────────────────────────────────────────── */

    /** Clear every non-empty .suggestions-dropdown in the document. */
    function _dismissAllDropdowns() {
        var open = document.querySelectorAll('.suggestions-dropdown:not(:empty)');
        for (var i = 0; i < open.length; i++) {
            open[i].innerHTML = '';
            _resetDropdownPosition(open[i]);
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

    /* ── Scroll / resize dismiss ───────────────────────────────── */

    /**
     * Dismiss all dropdowns when the user scrolls any ancestor or resizes
     * the window. This prevents an orphaned fixed-position dropdown from
     * hanging in space while the content underneath moves.
     */
    document.addEventListener('scroll', function () {
        var open = document.querySelectorAll('.suggestions-dropdown:not(:empty)');
        if (open.length) _dismissAllDropdowns();
    }, true); // capture phase — catches scroll on any element, not just document

    window.addEventListener('resize', function () {
        var open = document.querySelectorAll('.suggestions-dropdown:not(:empty)');
        if (open.length) _dismissAllDropdowns();
    });

    /* ── MutationObserver for dropdown population ──────────────── */

    /**
     * Watch for childList mutations on .suggestions-dropdown elements.
     * When children are added (htmx swap populates suggestions), reposition.
     * When children are removed (cleared), reset positioning.
     *
     * Uses a subtree observer on document.body because dropdowns are created
     * dynamically via htmx swaps and multi-value field cloning.
     */
    var _observer = new MutationObserver(function (mutations) {
        for (var i = 0; i < mutations.length; i++) {
            var target = mutations[i].target;

            // Only act on .suggestions-dropdown elements
            if (!target.classList || !target.classList.contains('suggestions-dropdown')) continue;

            if (target.children.length > 0) {
                _repositionDropdown(target);
            } else {
                _resetDropdownPosition(target);
            }
        }
    });

    _observer.observe(document.body, { childList: true, subtree: true });

    /* ── Exports ────────────────────────────────────────────────── */

    window.SemPKM = window.SemPKM || {};
    window.SemPKM.dismissAllDropdowns = _dismissAllDropdowns;
})();
