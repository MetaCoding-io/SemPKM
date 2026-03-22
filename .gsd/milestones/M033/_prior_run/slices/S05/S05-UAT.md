---
slice: S05
milestone: M033
title: "App Catalog Pages — UAT"
---

# S05 UAT: App Catalog Pages

## Preconditions

- SemPKM Docker stack running (`docker compose up -d`)
- At least one Mental Model installed (basic-pkm)
- Apps directory contains apps with `manifest.yaml` files (at least linear-sync, github-sync, etc.)
- Logged in as an owner-role user
- Workspace accessible at `/browser/`

---

## Test 1: Catalog Explorer Entry Visible

**Steps:**
1. Navigate to `/browser/`
2. Locate the APPS section in the left explorer sidebar
3. Click the APPS section header to expand it (if collapsed)

**Expected:**
- An "App Catalog" entry is visible in the APPS section with a grid icon
- The entry appears above any dynamically-loaded app pages
- The entry persists after the APPS section htmx content loads/reloads

---

## Test 2: Catalog Tab Opens from Explorer

**Steps:**
1. Click the "App Catalog" entry in the APPS explorer section

**Expected:**
- A new dockview tab opens with title "App Catalog" (or reuses existing tab if already open)
- The tab shows a card grid of available apps
- Each card displays: app name, truncated description, version badge, status badge
- The `test-app` entry is NOT shown in the listing
- Cards for installed apps show "installed" or "running" badge (green/blue)
- Cards for uninstalled apps show "available" badge (gray)

---

## Test 3: App Detail Page Navigation

**Steps:**
1. From the catalog card grid, click on any app card (e.g., "Linear Sync")

**Expected:**
- The tab content replaces with the detail page for that app (htmx in-panel navigation)
- Detail page shows:
  - App name and version in header
  - Status badge (available/installed/running/stopped)
  - Description section
  - Author and license (if present in manifest)
  - Model dependencies section listing required models
  - Permissions section showing granted capabilities (SPARQL, network domains, commands, background tasks)
  - Background tasks section with interval info (if app has tasks)
  - Settings section with setting labels (if app has settings)

---

## Test 4: Back Navigation from Detail

**Steps:**
1. From an app detail page, click the "← Back to Catalog" link

**Expected:**
- The tab returns to the card grid listing
- All apps are still shown with correct status badges

---

## Test 5: Install Button for Available App (Owner)

**Steps:**
1. Navigate to the detail page of an app that is NOT currently installed
2. Verify the "Install" button is visible

**Expected:**
- An "Install" button is shown (only for owner-role users)
- Clicking "Install" triggers `POST /browser/catalog/{app_id}/install`
- On success, the detail page re-renders with updated status badge (installed/running)
- The Install button is replaced by an Uninstall button

---

## Test 6: Uninstall Button for Installed App (Owner)

**Steps:**
1. Navigate to the detail page of an installed app
2. Verify the "Uninstall" button is visible

**Expected:**
- An "Uninstall" button is shown with a confirmation prompt (hx-confirm)
- Clicking "Uninstall" and confirming triggers `POST /browser/catalog/{app_id}/uninstall`
- On success, the detail page re-renders with "available" status badge
- The Uninstall button is replaced by an Install button

---

## Test 7: Non-Owner Cannot Install/Uninstall

**Steps:**
1. Log in as a non-owner user (viewer/editor role)
2. Navigate to an app detail page

**Expected:**
- No Install or Uninstall buttons are visible
- Directly POSTing to `/browser/catalog/{app_id}/install` returns 403
- Directly POSTing to `/browser/catalog/{app_id}/uninstall` returns 403

---

## Test 8: Nonexistent App Returns 404

**Steps:**
1. Navigate to `/browser/catalog/nonexistent-app-id`

**Expected:**
- A 404 response is returned
- No server error or crash

---

## Test 9: Install Error Renders in UI

**Steps:**
1. Trigger an install that fails (e.g., app with missing dependencies, or simulate via test mock)

**Expected:**
- The detail page re-renders with a red error alert box at the top
- The error message describes what went wrong
- The app's status badge remains unchanged (still "available")

---

## Test 10: Empty Catalog State

**Steps:**
1. Remove or empty the apps directory (test environment only)
2. Navigate to `/browser/catalog`

**Expected:**
- The catalog page renders without errors
- An empty state message is shown (no cards)

---

## Test 11: Tab Reuse on Repeat Click

**Steps:**
1. Click "App Catalog" in the explorer to open the catalog tab
2. Switch to a different tab
3. Click "App Catalog" again

**Expected:**
- No new tab is created
- The existing catalog tab is activated/focused

---

## Edge Cases

- **Malformed manifest**: An app directory with an unparseable `manifest.yaml` is silently excluded from the listing (logged at WARNING level). Other apps still appear.
- **Multiple status transitions**: Install → running → uninstall cycle should correctly update badges at each step without stale state.
- **Concurrent users**: Two owner sessions installing/uninstalling the same app simultaneously — second operation should either succeed or show an error, not crash.
