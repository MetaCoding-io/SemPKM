/**
 * SemPKM Auth Pages - Vanilla JS
 *
 * Provides: auth status checks, setup wizard (two-step), login form handling,
 * magic link token verification, logout, and invitation acceptance.
 */

/* -- Auth Status Check -- */

/**
 * Check auth status and redirect as needed.
 * - If setup_mode is true and not on setup page, redirect to /setup.html
 * - If setup is complete and not authenticated, redirect to /login.html
 * - If authenticated, allow navigation
 */
async function checkAuthStatus() {
  var path = window.location.pathname;
  var authPages = ["/setup.html", "/login.html", "/invite.html"];
  var isAuthPage = authPages.indexOf(path) !== -1;

  try {
    var resp = await apiFetch("/api/auth/status", { silent: true });
    var data = await resp.json();

    // If setup mode is active and we're not on the setup page, go there
    if (data.setup_mode && path !== "/setup.html") {
      window.location.href = "/setup.html";
      return;
    }

    // If setup is complete and we're on the setup page, redirect away
    if (!data.setup_mode && data.setup_complete && path === "/setup.html") {
      window.location.href = "/login.html";
      return;
    }

    // If setup is complete, check if user is authenticated
    if (data.setup_complete && !isAuthPage) {
      var meResp = await fetch("/api/auth/me"); // raw-fetch: needs custom 401 redirect with ?next=
      if (meResp.status === 401) {
        window.location.href = "/login.html?next=" + encodeURIComponent(window.location.pathname);
        return;
      }
    }

    return data;
  } catch (e) {
    // Network error - silently fail, user can still interact
    console.warn("Auth status check failed:", e.message);
  }
}

/* -- Setup Wizard (Two-Step) -- */

/**
 * Initialise the two-step setup wizard on setup.html.
 *
 * Step 1: Deployment mode selection → POST /api/setup/configure-instance
 * Step 2: Token + email claim → POST /api/auth/setup (unchanged)
 *
 * On page load, reads `instance_configured` from GET /api/auth/status.
 * If already configured, skips straight to Step 2.
 */
function initSetupWizard() {
  var step1 = document.getElementById("setup-step-1");
  var step2 = document.getElementById("setup-step-2");
  var indicator = document.getElementById("step-indicator");
  var messageEl = document.getElementById("setup-message");
  if (!step1 || !step2) return;

  // --- Step transition helpers ---

  function showStep(num) {
    if (messageEl) messageEl.innerHTML = "";
    if (num === 1) {
      step1.classList.add("active");
      step2.classList.remove("active");
      if (indicator) indicator.textContent = "Step 1 of 2";
      // Focus first radio option
      var firstRadio = step1.querySelector('input[type="radio"]');
      if (firstRadio) firstRadio.focus();
    } else {
      step1.classList.remove("active");
      step2.classList.add("active");
      if (indicator) indicator.textContent = "Step 2 of 2";
      // Focus the token input
      var tokenInput = document.getElementById("setup-token");
      if (tokenInput) tokenInput.focus();
    }
  }

  // --- Domain input conditional visibility ---

  var domainWrap = document.getElementById("domain-input-wrap");
  var domainInput = document.getElementById("domain-input");
  var radios = document.querySelectorAll('input[name="deployment-mode"]');

  function updateDomainVisibility() {
    var selected = document.querySelector('input[name="deployment-mode"]:checked');
    var isDomain = selected && selected.value === "domain";
    if (domainWrap) {
      domainWrap.hidden = !isDomain;
      if (isDomain && domainInput) {
        domainInput.setAttribute("required", "");
      } else if (domainInput) {
        domainInput.removeAttribute("required");
      }
    }
  }

  for (var i = 0; i < radios.length; i++) {
    radios[i].addEventListener("change", updateDomainVisibility);
  }
  updateDomainVisibility();

  // --- Step 1: Next handler ---

  var nextBtn = document.getElementById("setup-next-btn");
  if (nextBtn) {
    nextBtn.addEventListener("click", async function () {
      var selected = document.querySelector('input[name="deployment-mode"]:checked');
      if (!selected) {
        showAuthMessage(messageEl, "Please select a deployment mode.", "error");
        return;
      }

      var mode = selected.value;
      var domain = null;

      if (mode === "domain") {
        domain = _cleanDomain(domainInput ? domainInput.value : "");
        if (!domain) {
          showAuthMessage(messageEl, "Please enter a valid domain.", "error");
          if (domainInput) domainInput.focus();
          return;
        }
        // Write cleaned value back for user transparency
        if (domainInput) domainInput.value = domain;
      }

      // Disable button during request
      nextBtn.disabled = true;
      nextBtn.textContent = "Configuring…";

      try {
        var payload = { mode: mode };
        if (domain) payload.domain = domain;

        var resp = await apiFetch("/api/setup/configure-instance", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
          silent: true,
        });

        // Success — transition to Step 2
        showStep(2);
      } catch (err) {
        var detail = "Network error: " + err.message;
        if (err.body) { try { detail = JSON.parse(err.body).detail || detail; } catch (_) {} }
        showAuthMessage(messageEl, detail, "error");
      } finally {
        nextBtn.disabled = false;
        nextBtn.textContent = "Next";
      }
    });
  }

  // --- Step 2: Back handler ---

  var backBtn = document.getElementById("setup-back-btn");
  if (backBtn) {
    backBtn.addEventListener("click", function () {
      showStep(1);
    });
  }

  // --- Step 2: Submit handler (existing setup flow) ---

  var form = document.getElementById("setupForm");
  if (form) {
    form.addEventListener("submit", async function (e) {
      e.preventDefault();

      var submitBtn = form.querySelector('button[type="submit"]');

      // Clear previous messages
      if (messageEl) messageEl.innerHTML = "";

      var token = document.getElementById("setup-token").value.trim();
      if (!token) {
        showAuthMessage(messageEl, "Please enter the setup token.", "error");
        return;
      }

      var email = document.getElementById("setup-email").value.trim() || null;

      // Disable submit during request
      if (submitBtn) submitBtn.disabled = true;

      try {
        var resp = await apiFetch("/api/auth/setup", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ token: token, email: email }),
          silent: true,
        });

        showAuthMessage(
          messageEl,
          "Instance claimed successfully! Redirecting...",
          "success"
        );
        setTimeout(function () {
          window.location.href = "/";
        }, 2000);
      } catch (err) {
        var detail = "Network error: " + err.message;
        if (err.body) { try { detail = JSON.parse(err.body).detail || detail; } catch (_) {} }
        showAuthMessage(messageEl, detail, "error");
        if (submitBtn) submitBtn.disabled = false;
      }
    });
  }

  // --- On page load: check instance_configured ---

  (async function () {
    var data = await checkAuthStatus();
    // checkAuthStatus may have redirected. If we're still here:
    if (data && data.instance_configured === true) {
      // Instance already configured (Step 1 done), skip to Step 2
      showStep(2);
    } else {
      // Show Step 1
      showStep(1);
    }
  })();
}

/* -- Domain input helpers -- */

/**
 * Clean a domain input string: strip protocol prefixes, trailing
 * slashes/paths, and whitespace. Returns empty string if invalid.
 */
function _cleanDomain(raw) {
  if (!raw) return "";
  var d = raw.trim().toLowerCase();

  // Strip protocol prefixes
  d = d.replace(/^https?:\/\//i, "");
  d = d.replace(/^\/\//, "");

  // Strip trailing slash/path
  d = d.split("/")[0];

  // Basic hostname validation: letters, digits, dots, hyphens
  if (!/^[a-z0-9]([a-z0-9-]*[a-z0-9])?(\.[a-z0-9]([a-z0-9-]*[a-z0-9])?)*\.[a-z]{2,}$/.test(d)) {
    return "";
  }

  return d;
}

/* -- Login Form -- */

/**
 * Handle the login form submission.
 * POSTs to /api/auth/magic-link with the user's email.
 */
function handleLoginForm() {
  var form = document.getElementById("loginForm");
  if (!form) return;

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    var messageEl = document.getElementById("login-message");
    var submitBtn = form.querySelector('button[type="submit"]');

    if (messageEl) messageEl.innerHTML = "";

    var email = document.getElementById("login-email").value.trim();
    if (!email) {
      showAuthMessage(messageEl, "Please enter your email address.", "error");
      return;
    }

    if (submitBtn) submitBtn.disabled = true;

    try {
      var resp = await apiFetch("/api/auth/magic-link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email }),
        silent: true,
      });

      var data = await resp.json();

      if (data.token) {
        // No SMTP configured — token returned directly, auto-verify
        showAuthMessage(messageEl, "Logging in...", "info");
        try {
          var verifyResp = await apiFetch("/api/auth/verify", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ token: data.token }),
            silent: true,
          });
          showAuthMessage(messageEl, "Login successful! Redirecting...", "success");
          setTimeout(function () {
            var params = new URLSearchParams(window.location.search);
            var nextUrl = params.get("next");
            window.location.href = nextUrl || "/";
          }, 1000);
        } catch (verifyErr) {
          var vDetail = "Token verification failed.";
          if (verifyErr.body) { try { vDetail = JSON.parse(verifyErr.body).detail || vDetail; } catch (_) {} }
          showAuthMessage(messageEl, vDetail, "error");
          if (submitBtn) submitBtn.disabled = false;
        }
        return;
      }

      showAuthMessage(
        messageEl,
        "Check your email for a login link.",
        "success"
      );
    } catch (err) {
      showAuthMessage(messageEl, "Network error: " + err.message, "error");
      if (submitBtn) submitBtn.disabled = false;
    }
  });
}

/* -- Token Verification (Magic Link callback) -- */

/**
 * Check URL for ?token=... parameter. If present, POST to /api/auth/verify.
 * On success, redirect to main page. On error, show error message.
 */
async function handleVerifyToken() {
  var params = new URLSearchParams(window.location.search);
  var token = params.get("token");
  if (!token) return;

  var messageEl = document.getElementById("login-message");

  showAuthMessage(messageEl, "Verifying your login link...", "info");

  try {
    var resp = await apiFetch("/api/auth/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: token }),
      silent: true,
    });

    var data = await resp.json();

    showAuthMessage(
      messageEl,
      "Welcome, " + (data.display_name || data.email) + "! Redirecting...",
      "success"
    );
    setTimeout(function () {
      var nextParams = new URLSearchParams(window.location.search);
      var nextUrl = nextParams.get("next");
      window.location.href = nextUrl || "/";
    }, 1500);
  } catch (err) {
    var detail = "Network error: " + err.message;
    if (err.body) { try { detail = JSON.parse(err.body).detail || detail; } catch (_) {} }
    showAuthMessage(messageEl, detail, "error");
  }
}

/* -- Logout -- */

/**
 * POST to /api/auth/logout, then redirect to /login.html.
 */
async function handleLogout() {
  try {
    await apiFetch("/api/auth/logout", {
      method: "POST",
      silent: true,
    });
  } catch (e) {
    // Even if logout fails, redirect to login
    console.warn("Logout request failed:", e.message);
  }
  window.location.href = "/login.html";
}

/* -- Invitation Acceptance -- */

/**
 * On invite.html, read ?token=... from URL and verify the invitation.
 * POSTs to /api/auth/verify with the invitation token.
 */
async function handleInviteAccept() {
  var params = new URLSearchParams(window.location.search);
  var token = params.get("token");

  var messageEl = document.getElementById("invite-message");

  if (!token) {
    showAuthMessage(
      messageEl,
      "No invitation token found. Please use the link from your invitation email.",
      "error"
    );
    return;
  }

  showAuthMessage(messageEl, "Verifying your invitation...", "info");

  try {
    var resp = await apiFetch("/api/auth/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: token }),
      silent: true,
    });

    var data = await resp.json();

    showAuthMessage(
      messageEl,
      "Welcome to SemPKM! Redirecting...",
      "success"
    );
    setTimeout(function () {
      var nextParams = new URLSearchParams(window.location.search);
      var nextUrl = nextParams.get("next");
      window.location.href = nextUrl || "/";
    }, 2000);
  } catch (err) {
    var detail = "Network error: " + err.message;
    if (err.body) {
      try { detail = (JSON.parse(err.body).detail || "Invalid or expired invitation.") + ' <a href="/login.html">Go to login</a>'; } catch (_) {}
    }
    showAuthMessage(messageEl, detail, "error");
  }
}

/* -- Utilities -- */

/**
 * Show a message in an auth message container.
 * @param {HTMLElement} el - The message container element
 * @param {string} message - The message text (may contain HTML for links)
 * @param {string} type - "success", "error", or "info"
 */
function showAuthMessage(el, message, type) {
  if (!el) return;
  var className = "auth-message";
  if (type === "success") className += " auth-message-success";
  else if (type === "error") className += " auth-message-error";
  else if (type === "info") className += " auth-message-info";

  el.innerHTML = '<div class="' + className + '">' + message + "</div>";
}
