/**
 * SemPKM Auth Pages - Vanilla JS
 *
 * Provides: auth status checks, setup form handling, login form handling,
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
  try {
    const resp = await fetch("/api/auth/status");
    if (!resp.ok) return;

    const data = await resp.json();

    const path = window.location.pathname;

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
  } catch (e) {
    // Network error - silently fail, user can still interact
    console.warn("Auth status check failed:", e.message);
  }
}

/* -- Setup Form -- */

/**
 * Handle the setup wizard form submission.
 * POSTs to /api/auth/setup with the setup token and optional email.
 */
function handleSetupForm() {
  var form = document.getElementById("setupForm");
  if (!form) return;

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    var messageEl = document.getElementById("setup-message");
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
      var resp = await fetch("/api/auth/setup", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token: token, email: email }),
      });

      var data = await resp.json();

      if (!resp.ok) {
        showAuthMessage(messageEl, data.detail || "Setup failed.", "error");
        if (submitBtn) submitBtn.disabled = false;
        return;
      }

      showAuthMessage(
        messageEl,
        "Instance claimed successfully! Redirecting...",
        "success"
      );
      setTimeout(function () {
        window.location.href = "/";
      }, 2000);
    } catch (err) {
      showAuthMessage(messageEl, "Network error: " + err.message, "error");
      if (submitBtn) submitBtn.disabled = false;
    }
  });
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
      var resp = await fetch("/api/auth/magic-link", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email }),
      });

      var data = await resp.json();

      if (!resp.ok) {
        showAuthMessage(
          messageEl,
          data.detail || "Failed to send magic link.",
          "error"
        );
        if (submitBtn) submitBtn.disabled = false;
        return;
      }

      showAuthMessage(
        messageEl,
        "Check your email for a login link. If this is a local instance, check the API logs for the token.",
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
    var resp = await fetch("/api/auth/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: token }),
    });

    var data = await resp.json();

    if (!resp.ok) {
      showAuthMessage(
        messageEl,
        data.detail || "Invalid or expired login link.",
        "error"
      );
      return;
    }

    showAuthMessage(
      messageEl,
      "Welcome, " + (data.display_name || data.email) + "! Redirecting...",
      "success"
    );
    setTimeout(function () {
      window.location.href = "/";
    }, 1500);
  } catch (err) {
    showAuthMessage(messageEl, "Network error: " + err.message, "error");
  }
}

/* -- Logout -- */

/**
 * POST to /api/auth/logout, then redirect to /login.html.
 */
async function handleLogout() {
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
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
    var resp = await fetch("/api/auth/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: token }),
    });

    var data = await resp.json();

    if (!resp.ok) {
      showAuthMessage(
        messageEl,
        (data.detail || "Invalid or expired invitation.") +
          ' <a href="/login.html">Go to login</a>',
        "error"
      );
      return;
    }

    showAuthMessage(
      messageEl,
      "Welcome to SemPKM! Redirecting...",
      "success"
    );
    setTimeout(function () {
      window.location.href = "/";
    }, 2000);
  } catch (err) {
    showAuthMessage(messageEl, "Network error: " + err.message, "error");
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
