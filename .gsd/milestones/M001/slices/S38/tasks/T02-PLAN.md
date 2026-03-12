# T02: 38-global-lint-dashboard-ui 02

**Slice:** S38 — **Milestone:** M001

## Description

Wire up SSE auto-refresh, health badge, and Command Palette for the lint dashboard.

Purpose: The dashboard from Plan 01 is static on load. This plan adds real-time auto-refresh via SSE events, a persistent health badge on the LINT tab showing violation counts (LINT-03), and Command Palette access.

Output: Live-updating lint dashboard with health badge visible on the LINT tab at all times, Command Palette integration.

## Must-Haves

- [ ] "User can see a health indicator badge on the LINT tab showing violation count without opening the panel"
- [ ] "Dashboard auto-refreshes when a validation run completes (via SSE)"
- [ ] "User can open the lint dashboard via Command Palette 'Toggle Lint Dashboard'"
- [ ] "Health badge updates in real-time after each validation event"

## Files

- `frontend/static/js/workspace.js`
