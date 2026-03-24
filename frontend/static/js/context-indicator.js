/**
 * Context Indicator — real-time user context display in the sidebar.
 *
 * Fetches current context on load, then subscribes to SSE for live
 * updates.  Renders location/activity/time chips with Lucide icons.
 * Falls back to "Context unknown" when stale or disconnected.
 *
 * @module context-indicator
 */
(function () {
    'use strict';

    // ── Icon mapping ────────────────────────────────────────────
    var LOCATION_ICON = 'map-pin';

    var ACTIVITY_ICONS = {
        walking:    'footprints',
        driving:    'car',
        stationary: 'armchair',
        cycling:    'bike',
        running:    'footprints'
    };
    var ACTIVITY_DEFAULT_ICON = 'activity';

    var TIME_ICONS = {
        morning:    'sunrise',
        work_hours: 'briefcase',
        afternoon:  'sun',
        evening:    'sunset',
        night:      'moon'
    };
    var TIME_DEFAULT_ICON = 'clock';

    // ── Human-readable labels ───────────────────────────────────
    var TIME_LABELS = {
        morning:    'Morning',
        work_hours: 'Work',
        afternoon:  'Afternoon',
        evening:    'Evening',
        night:      'Night'
    };

    var ACTIVITY_LABELS = {
        walking:    'Walking',
        driving:    'Driving',
        stationary: 'Stationary',
        cycling:    'Cycling',
        running:    'Running'
    };

    // ── DOM references ──────────────────────────────────────────
    var _el = null;
    var _sse = null;

    // ── Rendering ───────────────────────────────────────────────

    /**
     * Build a single chip element: <span class="context-chip"><i data-lucide="icon"></i><span class="context-chip-label">label</span></span>
     */
    function _chip(icon, label) {
        return '<span class="context-chip">' +
            '<i data-lucide="' + icon + '"></i>' +
            '<span class="context-chip-label">' + _esc(label) + '</span>' +
            '</span>';
    }

    function _sep() {
        return '<span class="context-separator">·</span>';
    }

    /** Minimal HTML escaping */
    function _esc(s) {
        if (!s) return '';
        return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    }

    /**
     * Render the context data into the indicator element.
     * @param {object|null} data — ContextData dict from the API, or null
     */
    function _renderContext(data) {
        if (!_el) return;

        // Stale or no context → show "Context unknown"
        if (!data || data.is_stale) {
            _el.classList.add('context-stale');
            _el.innerHTML =
                '<i data-lucide="radar"></i>' +
                '<span class="context-status">Context unknown</span>';
            _refreshIcons();
            return;
        }

        // Build chip list from non-null fields
        var chips = [];

        if (data.location_zone) {
            chips.push(_chip(LOCATION_ICON, data.location_zone));
        }
        if (data.activity) {
            var actIcon = ACTIVITY_ICONS[data.activity] || ACTIVITY_DEFAULT_ICON;
            var actLabel = ACTIVITY_LABELS[data.activity] || data.activity;
            chips.push(_chip(actIcon, actLabel));
        }
        if (data.time_period) {
            var timeIcon = TIME_ICONS[data.time_period] || TIME_DEFAULT_ICON;
            var timeLabel = TIME_LABELS[data.time_period] || data.time_period;
            chips.push(_chip(timeIcon, timeLabel));
        }
        if (data.calendar_event) {
            chips.push(_chip('calendar', data.calendar_event));
        }

        // If somehow all fields are null but not stale, show unknown
        if (chips.length === 0) {
            _el.classList.add('context-stale');
            _el.innerHTML =
                '<i data-lucide="radar"></i>' +
                '<span class="context-status">Context unknown</span>';
            _refreshIcons();
            return;
        }

        // Render active context
        _el.classList.remove('context-stale');
        _el.innerHTML =
            '<i data-lucide="radar"></i>' +
            '<span class="context-chips">' +
            chips.join(_sep()) +
            '</span>';
        _refreshIcons();
    }

    /** Re-initialize Lucide icons within the indicator */
    function _refreshIcons() {
        if (typeof lucide !== 'undefined' && _el) {
            lucide.createIcons({ root: _el });
        }
    }

    // ── Data fetching ───────────────────────────────────────────

    /** Fetch current context from the REST API */
    function _fetchCurrent() {
        fetch('/api/context/current', { credentials: 'same-origin' })
            .then(function (res) {
                if (!res.ok) {
                    // Auth failure or server error — show stale
                    _renderContext(null);
                    return null;
                }
                return res.json();
            })
            .then(function (json) {
                if (json && json.context) {
                    _renderContext(json.context);
                } else {
                    _renderContext(null);
                }
            })
            .catch(function () {
                _renderContext(null);
            });
    }

    // ── SSE connection ──────────────────────────────────────────

    function _connectSSE() {
        if (_sse) {
            _sse.close();
        }

        _sse = new EventSource('/api/context/stream');

        _sse.addEventListener('context_update', function (e) {
            try {
                var data = JSON.parse(e.data);
                _renderContext(data);
            } catch (err) {
                console.warn('[context-indicator] Failed to parse SSE data:', err);
            }
        });

        _sse.addEventListener('context_stale', function () {
            if (_el) {
                _el.classList.add('context-stale');
                var statusSpan = _el.querySelector('.context-status');
                if (statusSpan) {
                    statusSpan.textContent = 'Context unknown';
                }
            }
        });

        _sse.onerror = function () {
            // SSE disconnected — mark as stale
            if (_el) {
                _el.classList.add('context-stale');
            }
        };
    }

    // ── Init ────────────────────────────────────────────────────

    function _init() {
        _el = document.getElementById('context-indicator');
        if (!_el) return;

        _fetchCurrent();
        _connectSSE();
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _init);
    } else {
        _init();
    }
})();
