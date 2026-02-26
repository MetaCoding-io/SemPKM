/**
 * PostHog analytics and error monitoring for SemPKM frontend.
 *
 * Fetches the PostHog configuration from the backend API and
 * conditionally loads the PostHog JS SDK. When enabled, provides:
 * - Autocapture (clicks, form submissions, page views)
 * - Session replay (full DOM recording for debugging)
 * - Global error capture (window.onerror + unhandledrejection)
 *
 * Controlled by the POSTHOG_ENABLED flag on the backend.
 */
(function () {
  "use strict";

  // Fetch PostHog config from backend and initialize if enabled
  fetch("/api/monitoring/config")
    .then(function (res) {
      if (!res.ok) return null;
      return res.json();
    })
    .then(function (config) {
      if (!config || !config.enabled || !config.api_key) return;
      loadPostHog(config.api_key, config.host);
    })
    .catch(function () {
      // Config endpoint unavailable — PostHog stays disabled
    });

  function loadPostHog(apiKey, apiHost) {
    // PostHog JS SDK bootstrap snippet (official loader pattern)
    !(function (t, e) {
      var o, n, p, r;
      e.__SV ||
        ((window.posthog = e),
        (e._i = []),
        (e.init = function (i, s, a) {
          function g(t, e) {
            var o = e.split(".");
            2 == o.length && ((t = t[o[0]]), (e = o[1]));
            t[e] = function () {
              t.push([e].concat(Array.prototype.slice.call(arguments, 0)));
            };
          }
          ((p = t.createElement("script")).type = "text/javascript"),
            (p.crossOrigin = "anonymous"),
            (p.async = !0),
            (p.src =
              s.api_host.replace(".i.posthog.com", "-assets.i.posthog.com") +
              "/static/array.js"),
            (r = t.getElementsByTagName("script")[0]).parentNode.insertBefore(
              p,
              r
            );
          var u = e;
          for (
            void 0 !== a ? (u = e[a] = []) : (a = "posthog"),
              u.people = u.people || [],
              u.toString = function (t) {
                var e = "posthog";
                return (
                  "posthog" !== a && (e += "." + a), t || (e += " (stub)"), e
                );
              },
              u.people.toString = function () {
                return u.toString(1) + ".people (stub)";
              },
              o =
                "init capture register register_once register_for_session unregister unregister_for_session getFeatureFlag getFeatureFlagPayload isFeatureEnabled reloadFeatureFlags updateEarlyAccessFeatureEnrollment getEarlyAccessFeatures on onFeatureFlags onSessionId getSurveys getActiveMatchingSurveys renderSurvey canRenderSurvey getNextSurveyStep identify setPersonProperties group resetGroups setPersonPropertiesForFlags resetPersonPropertiesForFlags setGroupPropertiesForFlags resetGroupPropertiesForFlags reset get_distinct_id getGroups get_session_id get_session_replay_url alias set_config startSessionRecording stopSessionRecording sessionRecordingStarted captureException loadToolbar get_property getSessionProperty createPersonProfile opt_in_capturing opt_out_capturing has_opted_in_capturing has_opted_out_capturing clear_opt_in_out_capturing debug".split(
                  " "
                ),
              n = 0;
            n < o.length;
            n++
          )
            g(u, o[n]);
          e._i.push([i, s, a]);
        }),
        (e.__SV = 1));
    })(document, window.posthog || []);

    // Initialize PostHog with session replay and autocapture
    posthog.init(apiKey, {
      api_host: apiHost,
      // Autocapture: clicks, form submissions, page views
      autocapture: true,
      // Session replay: record DOM for debugging user issues
      session_recording: {
        recordCrossOriginIframes: false,
      },
      // Capture performance data
      capture_performance: true,
      // Capture page views on route changes
      capture_pageview: true,
      capture_pageleave: true,
      // Enable exception autocapture
      autocapture_exceptions: true,
    });

    // Global error handler: capture unhandled JS errors
    window.addEventListener("error", function (event) {
      if (window.posthog && window.posthog.captureException) {
        window.posthog.captureException(event.error || event.message, {
          source: event.filename,
          lineno: event.lineno,
          colno: event.colno,
        });
      }
    });

    // Global promise rejection handler: capture unhandled rejections
    window.addEventListener("unhandledrejection", function (event) {
      if (window.posthog && window.posthog.captureException) {
        var error =
          event.reason instanceof Error
            ? event.reason
            : new Error(String(event.reason));
        window.posthog.captureException(error, {
          type: "unhandledrejection",
        });
      }
    });
  }
})();
