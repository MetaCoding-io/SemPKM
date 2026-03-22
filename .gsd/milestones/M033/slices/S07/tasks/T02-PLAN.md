---
estimated_steps: 3
estimated_files: 3
skills_used: []
---

# T02: Setup wizard two-step UI

**Slice:** S07 — Deployment & Onboarding Overhaul
**Milestone:** M033

## Description

Redesign the setup wizard (`setup.html` + `auth.js`) as a two-step flow: Step 1 selects deployment mode (local/domain/later) and calls `POST /api/setup/configure-instance`; Step 2 is the existing account creation form. Add step indicator, radio card styling, domain input validation, and a one-way-door warning about namespace permanence.

The `checkAuthStatus()` function uses the new `instance_configured` field from `GET /api/auth/status` to determine which step to show. If `instance_configured` is false and `setup_mode` is true, show Step 1. If `instance_configured` is true and `setup_mode` is true, show Step 2 directly.

## Steps

1. **Redesign `frontend/static/setup.html`** — replace the single-form layout with a two-step wizard:
   - **Step indicator**: "Step 1 of 2 — Deployment Mode" / "Step 2 of 2 — Claim Instance"
   - **Step 1 (deployment mode)**: Three radio card options:
     - "Local only (http://localhost:3000)" — UUID namespace, data stays local
     - "Custom domain" — text input for domain (placeholder: `sempkm.example.com`), inline validation (no `http://` prefix, valid hostname)
     - "Configure later (advanced)" — UUID namespace, can set BASE_NAMESPACE in .env later
   - One-way-door warning text: "Your data namespace cannot be changed after you create objects."
   - "Continue" button to submit Step 1
   - **Step 2 (account creation)**: Existing token + email form, unchanged except wrapped in a `step-2` container hidden initially
   - Both steps share the same `.auth-card` container; visibility toggled via CSS classes

2. **Update `frontend/static/js/auth.js`**:
   - Modify `checkAuthStatus()` — read `data.instance_configured`. If `setup_mode` is true and `instance_configured` is false, show step 1 and hide step 2. If `setup_mode` is true and `instance_configured` is true, hide step 1 and show step 2 directly.
   - Add `handleDeploymentStep()` — listens for the Continue button on step 1. Reads selected radio value. If "domain", validates the domain input is non-empty and doesn't start with `http`. Calls `POST /api/setup/configure-instance` with `{mode, domain?}`. On success, hides step 1 and shows step 2. On error (409 = data exists, 403 = not in setup mode), shows error message.
   - `handleSetupForm()` remains mostly unchanged — it handles step 2's token+email submission to `POST /api/auth/setup`.
   - Wire both handlers in the `<script>` block at the bottom of setup.html.
   - When domain mode is selected, show the derived namespace preview: "Your data namespace will be: https://{domain}/data/"

3. **Add CSS in `frontend/static/css/style.css`** — at the end of the auth section:
   - `.step-indicator` — flex row with step dots/numbers, active state highlighting
   - `.setup-step` — container for each step, hidden by default
   - `.setup-step.active` — visible step (display: block)
   - `.radio-card` — styled radio input card with border, padding, hover state, selected state (accent border + subtle background)
   - `.radio-card input[type="radio"]` — visually hidden but accessible
   - `.radio-card-label` — card content with title and description
   - `.domain-input-group` — conditionally shown when "Custom domain" is selected, smooth reveal animation
   - `.namespace-preview` — small text showing the derived namespace
   - `.one-way-warning` — amber/yellow info box for the permanence warning

## Must-Haves

- [ ] Step 1 shows three deployment mode options as radio cards
- [ ] Domain input only visible when "Custom domain" is selected
- [ ] Domain validation: rejects empty, rejects `http://` prefix, accepts valid hostnames
- [ ] Step 1 calls `POST /api/setup/configure-instance` and shows errors
- [ ] Step 2 is the existing account creation form (unchanged behavior)
- [ ] `checkAuthStatus()` uses `instance_configured` to determine which step to show
- [ ] One-way-door warning visible in Step 1
- [ ] Step indicator shows progress (1 of 2 / 2 of 2)

## Verification

- `grep -q "configure-instance" frontend/static/js/auth.js` — endpoint call exists
- `grep -q "step-indicator\|radio-card\|deployment-mode\|setup-step" frontend/static/css/style.css` — styling exists
- `grep -q "instance_configured" frontend/static/js/auth.js` — auth status field is checked
- `grep -q "step-1\|step-2\|deployment" frontend/static/setup.html` — two-step structure exists

## Observability Impact

- **New runtime signal:** `checkAuthStatus()` now reads `instance_configured` from `/api/auth/status` — logs a console.warn if the status fetch fails
- **Inspection surface:** Step 1 POST to `/api/setup/configure-instance` is visible in browser DevTools Network tab. The button disables and shows "Configuring..." during the request.
- **Failure visibility:** 409 (data exists) and 403 (already configured) errors from the endpoint are displayed inline via `showAuthMessage()` with user-friendly text. Domain validation errors appear inline below the domain input.
- **Step state:** The visible step indicator (dots + label) shows which setup step is active. `_showSetupStep()` manages DOM state transitions.

## Inputs

- `frontend/static/setup.html` — existing single-step setup page to redesign
- `frontend/static/js/auth.js` — existing auth JS with `checkAuthStatus()` and `handleSetupForm()`
- `frontend/static/css/style.css` — existing auth section styles (lines 2142-2280)
- `backend/app/api/setup_routes.py` — T01's configure-instance endpoint (API contract: POST with `{mode, domain?}`, returns instance config JSON or 409/403 error)

## Expected Output

- `frontend/static/setup.html` — redesigned with two-step wizard layout
- `frontend/static/js/auth.js` — updated with multi-step flow, `handleDeploymentStep()`, `instance_configured` check
- `frontend/static/css/style.css` — extended with step indicator, radio card, domain input, warning styles
