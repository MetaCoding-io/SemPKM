---
id: T02
parent: S07
milestone: M033
provides:
  - Two-step setup wizard UI (deployment mode → account creation)
  - handleDeploymentStep() function for mode selection, domain validation, and API call
  - checkAuthStatus() reads instance_configured to show correct step
  - Radio card, step indicator, domain input, one-way-door warning CSS
key_files:
  - frontend/static/setup.html
  - frontend/static/js/auth.js
  - frontend/static/css/style.css
key_decisions:
  - Radio cards use label-wrapping-input pattern (click anywhere on card to select) rather than separate radio + label elements
  - Domain validation is inline (below input) rather than in the auth-message area — keeps error close to the field
  - Step indicator uses dot-line-dot with completed/active states, matching the auth-card's existing design language
patterns_established:
  - _showSetupStep() centralizes step visibility + indicator state in one function, called by both checkAuthStatus and handleDeploymentStep
  - Domain input uses max-height transition for smooth reveal animation (same pattern as other conditional inputs in the codebase)
observability_surfaces:
  - Step indicator shows current wizard step visually
  - Domain validation errors shown inline below the domain input
  - API errors (409/403) shown via showAuthMessage with descriptive text
  - Continue button shows "Configuring..." during API call
  - console.warn for auth status fetch failures
duration: 20m
verification_result: passed
completed_at: 2026-03-21
blocker_discovered: false
---

# T02: Setup wizard two-step UI

**Redesigned setup.html as a two-step wizard with deployment mode radio cards, domain validation, step indicator, and instance_configured-aware step routing**

## What Happened

Redesigned `frontend/static/setup.html` from a single account-creation form into a two-step wizard. Step 1 presents three deployment mode options (local, custom domain, configure later) as styled radio cards with a one-way-door warning about namespace permanence. Step 2 is the existing token + email account creation form, now wrapped in a `.setup-step` container.

Added `handleDeploymentStep()` to `auth.js` — manages radio card selection (toggling `.selected` class), conditional domain input visibility with smooth max-height animation, live namespace preview (showing the derived `https://{domain}/data/` URI), inline domain validation (rejects empty, rejects protocol prefixes), and the POST to `/api/setup/configure-instance`. Error responses are mapped to user-friendly messages (409 → "data already exists", 403 → "already configured").

Modified `checkAuthStatus()` to read the `instance_configured` field from `/api/auth/status`. When `setup_mode` is true and `instance_configured` is false, step 1 is shown. When `instance_configured` is true, step 1 is skipped and step 2 is shown directly — this handles page refreshes after deployment mode is already configured.

Added `_showSetupStep()` helper to centralize step visibility and step indicator state (dot active/completed classes, label text, connecting line state).

Extended `style.css` with step indicator (dots + connecting line), radio card styling (border, hover, selected state with accent), domain input group (conditional visibility via max-height transition), namespace preview (monospace, recessed background), one-way-door warning (amber/yellow box), and wider auth card for the wizard layout.

## Verification

All four task-level grep checks pass:
- `configure-instance` present in auth.js
- Step indicator, radio card, deployment mode, and setup-step CSS classes present in style.css
- `instance_configured` field checked in auth.js
- Two-step structure (step-1, step-2, deployment) in setup.html

Slice-level checks:
- All 26 unit tests pass (config model + endpoint)
- Namespace guard failure path test passes

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `grep -q "configure-instance" frontend/static/js/auth.js` | 0 | ✅ pass | <0.1s |
| 2 | `grep -q "step-indicator\|radio-card\|deployment-mode\|setup-step" frontend/static/css/style.css` | 0 | ✅ pass | <0.1s |
| 3 | `grep -q "instance_configured" frontend/static/js/auth.js` | 0 | ✅ pass | <0.1s |
| 4 | `grep -q "step-1\|step-2\|deployment" frontend/static/setup.html` | 0 | ✅ pass | <0.1s |
| 5 | `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py -v` | 0 | ✅ pass | 0.57s |
| 6 | `cd backend && .venv/bin/python -m pytest tests/test_instance_config.py::TestConfigureInstanceEndpoint::test_namespace_guard_409_when_data_exists -v` | 0 | ✅ pass | 0.41s |

## Diagnostics

- **Step routing**: On `/setup.html`, check which step is visible — if step 1 is shown, `instance_configured` was false; if step 2, it was true
- **Domain validation**: Enter `http://example.com` in the domain input — inline error should appear below the input, not in the message area
- **API call**: Open DevTools Network tab, select a mode, click Continue — should see POST to `/api/setup/configure-instance` with `{mode, domain?}` payload
- **Error display**: If the endpoint returns 409 or 403, the error message appears below the Continue button via `showAuthMessage()`

## Deviations

None. Implementation matches the task plan's three steps exactly.

## Known Issues

None.

## Files Created/Modified

- `frontend/static/setup.html` — redesigned with two-step wizard layout (step indicator, radio cards for deployment mode, domain input, one-way warning, existing account form in step 2)
- `frontend/static/js/auth.js` — added `handleDeploymentStep()`, `_showSetupStep()` helper; modified `checkAuthStatus()` to use `instance_configured` for step routing
- `frontend/static/css/style.css` — added step indicator, radio card, domain input group, namespace preview, one-way warning, and setup wizard card width styles
- `.gsd/milestones/M033/slices/S07/tasks/T02-PLAN.md` — added Observability Impact section per pre-flight check
