---
estimated_steps: 5
estimated_files: 3
skills_used:
  - frontend-design
  - make-interfaces-feel-better
  - accessibility
---

# T02: Two-step setup wizard frontend

**Slice:** S01 — Deployment & Onboarding Overhaul
**Milestone:** M033

## Description

Transform the existing single-step setup page into a two-step wizard. Step 1 collects deployment mode (local / custom domain / configure later) and calls `POST /api/setup/configure-instance`. Step 2 is the existing token + email claim form calling `POST /api/auth/setup`. The frontend reads `instance_configured` from `GET /api/auth/status` to decide which step to show on page load.

Follow the existing auth page design language (`.auth-container`, `.auth-card`, `.auth-brand` patterns in `frontend/static/css/style.css`). The wizard must be keyboard-navigable and screen-reader friendly.

## Steps

1. **Redesign `frontend/static/setup.html`:**
   - Add a step indicator (Step 1 of 2 / Step 2 of 2) — simple text, not a complex stepper widget
   - Step 1 container: three radio card options with labels and descriptions:
     - "Local only" — `urn:sempkm:{uuid}/` namespace, no domain needed
     - "Custom domain" — shows a domain input field when selected (no `https://` prefix)
     - "Configure later" — UUID namespace, can set `BASE_NAMESPACE` in .env anytime
   - One-way-door warning: "Your data namespace cannot be changed after you create objects."
   - "Next" button for Step 1
   - Step 2 container: existing setup token + email form (unchanged structure)
   - "Back" button on Step 2 to return to Step 1

2. **Update `frontend/static/js/auth.js`:**
   - Rewrite `handleSetupForm()` as a multi-step flow:
     - On page load, call `GET /api/auth/status`. If `instance_configured` is true, show Step 2 directly; if false (or absent), show Step 1
     - Step 1 "Next" handler: validate selection (domain mode requires non-empty domain), call `POST /api/setup/configure-instance` with `{mode, domain?}`, on success transition to Step 2
     - Step 2 submission: unchanged — calls `POST /api/auth/setup`
   - Add domain input validation: strip `http://`/`https://` prefix if user accidentally includes it, validate hostname format (letters, digits, dots, hyphens)
   - Step transitions: hide/show containers, update step indicator
   - Error display: show API error messages (400 invalid domain, 409 data exists) in the message area

3. **Update `frontend/static/css/style.css`:**
   - `.setup-step` — container for each step, `display:none` by default, `.setup-step.active` shows it
   - `.setup-step-indicator` — step counter text styling (muted color, small font)
   - `.setup-radio-group` — vertical stack of radio card options
   - `.setup-radio-card` — bordered card with radio input, label, and description; highlighted border on selection
   - `.setup-radio-card input[type="radio"]` — accessible but visually integrated
   - `.setup-domain-input` — domain text field, shown only when "Custom domain" is selected
   - `.setup-warning` — one-way-door warning box with amber/yellow styling
   - `.setup-back-btn` — secondary/ghost button for going back to Step 1
   - Respect existing theme variables from `theme.css` (use `var(--color-*)` tokens)
   - Lucide icon sizing: follow CLAUDE.md rule — CSS sizing with `flex-shrink: 0`, no inline styles

4. **Update `checkAuthStatus()` in auth.js:**
   - When on setup.html: read `instance_configured` from status response
   - If `instance_configured === true`, show Step 2 container (instance already configured, just need account claim)
   - If `instance_configured === false` or field is absent (backward compat), show Step 1

5. **Keyboard and accessibility:**
   - Radio cards should be native `<input type="radio">` with `<label>` wrapping for click area
   - Domain input should have `aria-label` and be programmatically associated with its radio option
   - Step transitions should manage focus — move focus to first interactive element in new step
   - "Back" and "Next" buttons have clear accessible names

## Must-Haves

- [ ] Two-step flow: deployment mode → account creation
- [ ] Three radio card options: local / domain / later
- [ ] Domain input field shown conditionally for "Custom domain" option
- [ ] One-way-door warning about namespace permanence
- [ ] Step 1 calls POST /api/setup/configure-instance
- [ ] Step 2 calls POST /api/auth/setup (unchanged behavior)
- [ ] checkAuthStatus() reads instance_configured to show correct step on page load
- [ ] Domain input strips accidental protocol prefix
- [ ] Keyboard-navigable and screen-reader accessible

## Verification

- Open `frontend/static/setup.html` in browser — visually verify two-step flow
- Step 1 shows three radio card options, domain input appears when "Custom domain" selected
- One-way-door warning is visible
- `grep -q "configure-instance" frontend/static/js/auth.js` — Step 1 calls the endpoint
- `grep -q "setup-step" frontend/static/setup.html` — step containers exist
- `grep -q "instance_configured" frontend/static/js/auth.js` — status field is read

## Inputs

- `frontend/static/setup.html` — existing setup page to redesign
- `frontend/static/js/auth.js` — existing auth JS to extend with multi-step flow
- `frontend/static/css/style.css` — existing auth styles to extend
- `backend/app/api/setup_routes.py` — T01 output: the configure-instance endpoint this frontend calls
- `backend/app/auth/schemas.py` — T01 output: StatusResponse with instance_configured field

## Expected Output

- `frontend/static/setup.html` — redesigned two-step wizard
- `frontend/static/js/auth.js` — updated with multi-step setup flow
- `frontend/static/css/style.css` — extended with wizard step styling
