---
id: T02
parent: S01
milestone: M033
provides:
  - Two-step setup wizard UI (deployment mode → account creation)
  - Radio card options for local/domain/later deployment modes
  - Domain input with protocol prefix stripping and hostname validation
  - checkAuthStatus reads instance_configured to show correct step
  - Step transition with focus management and aria-live announcements
key_files:
  - frontend/static/setup.html
  - frontend/static/js/auth.js
  - frontend/static/css/style.css
key_decisions:
  - initSetupWizard() replaces separate checkAuthStatus()+handleSetupForm() calls on setup.html — unified entry point that handles both steps, status check, and step routing
  - checkAuthStatus() now returns the data object so initSetupWizard can read instance_configured without a second fetch
  - Domain validation uses client-side _cleanDomain() for UX (strip prefix, validate hostname) plus server-side validation for security
patterns_established:
  - Setup wizard step visibility uses .setup-step/.setup-step.active CSS classes with JS-managed transitions
  - Radio card pattern using native <label> wrapping <input type="radio"> with :has() selector for checked state highlighting
observability_surfaces:
  - Step indicator (#step-indicator) with aria-live="polite" announces step transitions
  - Domain input rewritten after cleaning — user sees what will be submitted
  - API error messages displayed verbatim in #setup-message area
  - instance_configured from GET /api/auth/status determines which step shows on page load
duration: 20min
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T02: Two-step setup wizard frontend

**Transformed the single-step setup page into a two-step wizard with deployment mode radio cards (local/domain/later), domain input with protocol stripping, one-way-door warning, and instance_configured-based step routing — all verification checks passing.**

## What Happened

Redesigned setup.html into a two-step flow following the existing auth page design language:

1. **`frontend/static/setup.html`** — Completely rewritten with two step containers. Step 1 has three radio card options (Local only / Custom domain / Configure later) inside a native `<fieldset>` with visually-hidden `<legend>`. A domain input appears conditionally when "Custom domain" is selected. An amber one-way-door warning alerts users that namespace is permanent. Step 2 is the unchanged token + email claim form with a Back button. Added `aria-live="polite"` step indicator, `role="group"` on each step, `role="alert"` on the warning box.

2. **`frontend/static/js/auth.js`** — Replaced the separate `checkAuthStatus()` + `handleSetupForm()` setup page pattern with a unified `initSetupWizard()` entry point. On page load, calls `GET /api/auth/status`; if `instance_configured` is true, skips directly to Step 2. Step 1 "Next" validates the selection (domain mode requires non-empty valid domain), strips any accidental `https://` prefix via `_cleanDomain()`, calls `POST /api/setup/configure-instance`, and on success transitions to Step 2 with focus management. Step 2 submission is unchanged. `checkAuthStatus()` now returns the status data object for callers that need it (backward-compatible — existing callers on login/index pages ignore the return value).

3. **`frontend/static/css/style.css`** — Added complete wizard styling: `.setup-step`/`.setup-step.active` for step visibility, `.setup-radio-group`/`.setup-radio-card` for the card-style radio options with `:has(input:checked)` highlight border, `.setup-domain-input-wrap`/`.setup-domain-input` for the conditional domain field, `.setup-warning` for the amber warning box, `.setup-back-btn`/`.setup-step2-buttons` for the Step 2 button layout, `.sr-only` for screen-reader-only text. All using existing theme.css `var(--color-*)` tokens.

## Verification

- Browser verification: Step 1 shows three radio cards, domain input appears when "Custom domain" selected, one-way-door warning visible, validation errors display correctly, domain prefix stripping works
- `grep -q "configure-instance" frontend/static/js/auth.js` — **PASS**
- `grep -q "setup-step" frontend/static/setup.html` — **PASS**
- `grep -q "instance_configured" frontend/static/js/auth.js` — **PASS**
- Backend tests still pass: 32/32 in test_instance_config.py

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py -v` | 0 | ✅ pass | 0.27s |
| 2 | `grep -q "instance_configured" backend/app/auth/schemas.py` | 0 | ✅ pass | <0.1s |
| 3 | `grep -q "configure-instance" backend/app/api/setup_routes.py` | 0 | ✅ pass | <0.1s |
| 4 | `grep -q "configure-instance" frontend/static/js/auth.js` | 0 | ✅ pass | <0.1s |
| 5 | `grep -q "setup-step" frontend/static/setup.html` | 0 | ✅ pass | <0.1s |
| 6 | `grep -q "instance_configured" frontend/static/js/auth.js` | 0 | ✅ pass | <0.1s |
| 7 | `test -f docker-compose.cloud.yml && test -f Caddyfile.cloud` | 1 | ⏳ skip (T03) | <0.1s |
| 8 | Browser: Step 1 radio cards, domain input toggle, warning box, validation | — | ✅ pass | visual |

## Diagnostics

- **Step routing:** `GET /api/auth/status` → `instance_configured` field determines which step shows on page load. `true` = skip to Step 2, `false`/absent = show Step 1.
- **Frontend errors:** All API errors from `POST /api/setup/configure-instance` (400 invalid domain, 409 data exists) are displayed verbatim in the `#setup-message` element.
- **Domain cleaning:** Domain input value is rewritten after `_cleanDomain()` strips protocol prefixes — inspect `#domain-input` value to see what was submitted.
- **Console warnings:** `"Auth status check failed: ..."` logged when the status endpoint is unreachable — the wizard falls back to showing Step 1.

## Deviations

- Added `<link rel="stylesheet" href="/css/theme.css">` to setup.html — the original was missing the theme stylesheet, which meant CSS variables like `--color-accent` were undefined. Login.html already had this import, so this is a bug fix.
- `checkAuthStatus()` now returns the response data object. This is backward-compatible — login.html and index.html call it without using the return value.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/setup.html` — **rewritten** — two-step wizard with radio cards, domain input, warning, step containers
- `frontend/static/js/auth.js` — **modified** — added initSetupWizard(), _cleanDomain(), updated checkAuthStatus() to return data
- `frontend/static/css/style.css` — **modified** — added setup wizard styles (.setup-step, .setup-radio-card, .setup-warning, etc.)
- `.gsd/milestones/M033/slices/S01/tasks/T02-PLAN.md` — **modified** — added Observability Impact section
