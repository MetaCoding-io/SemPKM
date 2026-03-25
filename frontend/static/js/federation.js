/**
 * Federation UI interactions: sync, toast, inbox badge, invitation handling,
 * shared graph creation, and notification actions.
 *
 * Loaded in workspace.html via <script src="/js/federation.js" defer>.
 */
(function () {
    'use strict';

    // -----------------------------------------------------------------------
    // Toast notifications
    // -----------------------------------------------------------------------

    function showToast(message, type, duration) {
        type = type || 'info';
        duration = duration || 4000;

        var toast = document.createElement('div');
        toast.className = 'federation-toast federation-toast-' + type;
        toast.textContent = message;
        document.body.appendChild(toast);

        // Trigger reflow then animate in
        void toast.offsetWidth;
        toast.classList.add('show');

        setTimeout(function () {
            toast.classList.remove('show');
            setTimeout(function () {
                toast.remove();
            }, 350);
        }, duration);
    }

    window.showFederationToast = showToast;

    // -----------------------------------------------------------------------
    // Inbox badge polling
    // -----------------------------------------------------------------------

    function updateInboxBadge() {
        apiFetch('/api/inbox?state=unread', { silent: true })
            .then(function (res) {
                return res.json();
            })
            .then(function (data) {
                if (!data) return;
                var badge = document.getElementById('inbox-badge');
                if (!badge) return;
                var count = Array.isArray(data) ? data.length : 0;
                badge.textContent = count;
                badge.style.display = count > 0 ? '' : 'none';
            })
            .catch(function () {
                // Silently ignore badge polling errors
            });
    }

    // Poll badge on load and periodically
    updateInboxBadge();
    var _badgeInterval = setInterval(updateInboxBadge, 60000);

    // Clean up polling on page unload
    window.addEventListener('beforeunload', function () {
        clearInterval(_badgeInterval);
    });

    // -----------------------------------------------------------------------
    // Sync Now handler
    // -----------------------------------------------------------------------

    window.syncSharedGraph = async function (graphId) {
        // Find the sync button for loading state
        var card = document.querySelector('[data-graph-iri*="' + graphId + '"]');
        var btn = card ? card.querySelector('.shared-graph-actions .primary') : null;
        var originalHTML = '';

        if (btn) {
            originalHTML = btn.innerHTML;
            btn.innerHTML = '<i data-lucide="loader-2"></i> Syncing...';
            btn.disabled = true;
            if (window.lucide) lucide.createIcons({ nodes: [btn] });
        }

        try {
            var res = await apiFetch('/api/federation/shared-graphs/' + graphId + '/sync', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
                silent: true
            });

            var result = await res.json();
            showToast('Synced: ' + result.pulled + ' pulled, ' + result.applied + ' applied', 'success');

            // Refresh collaboration panel and shared nav
            refreshCollabPanel();
            refreshSharedNav();
        } catch (err) {
            var detail = 'Sync error';
            try { detail = JSON.parse(err.body || '{}').detail || err.message; } catch (_) { detail = err.message; }
            showToast(detail, 'error');
        } finally {
            if (btn) {
                btn.innerHTML = originalHTML;
                btn.disabled = false;
                if (window.lucide) lucide.createIcons({ nodes: [btn] });
            }
        }
    };

    // Sync triggered from a notification
    window.syncFromNotification = async function (notifId, targetGraphIri) {
        if (targetGraphIri) {
            var graphId = targetGraphIri.replace('urn:sempkm:shared:', '');
            await window.syncSharedGraph(graphId);
        }
        await dismissNotification(notifId, 'acted');
    };

    // -----------------------------------------------------------------------
    // Create shared graph
    // -----------------------------------------------------------------------

    window.showCreateSharedGraph = function () {
        var form = document.getElementById('create-shared-graph-form');
        if (form) form.style.display = '';
    };

    window.hideCreateSharedGraph = function () {
        var form = document.getElementById('create-shared-graph-form');
        if (form) form.style.display = 'none';
    };

    window.submitCreateSharedGraph = async function () {
        var nameEl = document.getElementById('new-graph-name');
        var descEl = document.getElementById('new-graph-desc');
        var name = nameEl ? nameEl.value.trim() : '';
        var desc = descEl ? descEl.value.trim() : '';

        if (!name) {
            showToast('Graph name is required', 'error');
            return;
        }

        try {
            var res = await apiFetch('/api/federation/shared-graphs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name: name, description: desc }),
                silent: true
            });

            showToast('Shared graph "' + name + '" created', 'success');
            hideCreateSharedGraph();
            if (nameEl) nameEl.value = '';
            if (descEl) descEl.value = '';

            // Refresh panels
            refreshCollabPanel();
            refreshSharedNav();
        } catch (err) {
            var detail = 'Failed to create shared graph';
            try { detail = JSON.parse(err.body || '{}').detail || err.message; } catch (_) { detail = err.message; }
            showToast(detail, 'error');
        }
    };

    // -----------------------------------------------------------------------
    // Invitation form
    // -----------------------------------------------------------------------

    window.showInviteForm = function (graphIri) {
        var graphId = graphIri.replace('urn:sempkm:shared:', '');
        var form = document.getElementById('invite-form-' + graphId);
        if (form) form.style.display = '';
    };

    window.submitInvite = async function (graphIri, graphId) {
        var input = document.getElementById('invite-handle-' + graphId);
        var handle = input ? input.value.trim() : '';

        if (!handle) {
            showToast('Recipient handle is required', 'error');
            return;
        }

        try {
            var res = await apiFetch('/api/federation/invitations', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ graph_iri: graphIri, recipient_handle: handle }),
                silent: true
            });

            showToast('Invitation sent to ' + handle, 'success');
            var form = document.getElementById('invite-form-' + graphId);
            if (form) form.style.display = 'none';
            if (input) input.value = '';
        } catch (err) {
            var detail = 'Failed to send invitation';
            try { detail = JSON.parse(err.body || '{}').detail || err.message; } catch (_) { detail = err.message; }
            showToast(detail, 'error');
        }
    };

    // -----------------------------------------------------------------------
    // Notification actions
    // -----------------------------------------------------------------------

    window.acceptInvitation = async function (notifId) {
        try {
            var res = await apiFetch('/api/federation/invitations/' + notifId + '/accept', {
                method: 'POST',
                silent: true
            });

            showToast('Invitation accepted', 'success');
            refreshInbox();
            refreshCollabPanel();
            refreshSharedNav();
        } catch (err) {
            var detail = 'Failed to accept invitation';
            try { detail = JSON.parse(err.body || '{}').detail || err.message; } catch (_) { detail = err.message; }
            showToast(detail, 'error');
        }
    };

    window.declineInvitation = async function (notifId) {
        try {
            await apiFetch('/api/federation/invitations/' + notifId + '/decline', {
                method: 'POST',
                silent: true
            });
            showToast('Invitation declined', 'info');
            refreshInbox();
        } catch (err) {
            showToast('Error: ' + err.message, 'error');
        }
    };

    window.markNotificationRead = async function (notifId) {
        try {
            await apiFetch('/api/inbox/' + notifId, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ state: 'read' }),
                silent: true
            });
            refreshInbox();
            updateInboxBadge();
        } catch (err) {
            showToast('Error: ' + err.message, 'error');
        }
    };

    window.dismissNotification = async function (notifId, newState) {
        newState = newState || 'dismissed';
        try {
            await apiFetch('/api/inbox/' + notifId, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ state: newState }),
                silent: true
            });
            refreshInbox();
            updateInboxBadge();
        } catch (err) {
            showToast('Error: ' + err.message, 'error');
        }
    };

    // -----------------------------------------------------------------------
    // Panel refresh helpers
    // -----------------------------------------------------------------------

    function refreshInbox() {
        var el = document.getElementById('inbox-content');
        if (el && window.htmx) {
            htmx.ajax('GET', '/api/federation/inbox-partial', { target: el, swap: 'innerHTML' });
        }
        updateInboxBadge();
    }

    function refreshCollabPanel() {
        var el = document.getElementById('collab-content');
        if (el && window.htmx) {
            htmx.ajax('GET', '/api/federation/collab-partial', { target: el, swap: 'innerHTML' });
        }
    }

    function refreshSharedNav() {
        var el = document.getElementById('section-shared');
        if (el && window.htmx) {
            htmx.ajax('GET', '/api/federation/shared-nav', { target: el, swap: 'outerHTML' });
        }
    }

    // -----------------------------------------------------------------------
    // Re-initialize Lucide icons after htmx swaps
    // -----------------------------------------------------------------------

    document.addEventListener('htmx:afterSwap', function (e) {
        var target = e.detail.target;
        if (target && (
            target.id === 'inbox-content' ||
            target.id === 'collab-content' ||
            target.id === 'section-shared'
        )) {
            if (window.lucide) {
                lucide.createIcons({ nodes: [target] });
            }
        }
    });

    // -----------------------------------------------------------------------
    // Shared nav object click delegation
    // -----------------------------------------------------------------------

    document.addEventListener('click', function (e) {
        var leaf = e.target.closest('.shared-object[data-iri]');
        if (leaf && typeof window.openTab === 'function') {
            var iri = leaf.getAttribute('data-iri');
            var label = leaf.querySelector('span');
            var labelText = label ? label.textContent.trim() : iri;
            window.openTab(iri, labelText);
        }
    });

})();
