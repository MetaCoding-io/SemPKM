---
estimated_steps: 8
estimated_files: 1
skills_used: []
---

# T02: Deep link: open tab from ?tab= on page load

Handle the ?tab= query parameter on initial page load to open the referenced tab.

1. In workspace.js, after initWorkspaceLayout() completes (where dockview layout is restored), read ?tab= from the URL
2. If ?tab= is present:
   a. Check if the panel is already open (may have been restored from layout). If so, just focus it with setActive()
   b. If not open, determine the tab type from the ID format (raw IRI = object tab, 'view:*' = view tab, 'special:*' = special tab, etc.) and call the appropriate open*Tab() function
   c. For object tabs, call openTab(iri) — label will be fetched by the htmx partial
3. Do NOT clean the ?tab= from URL after processing — keeping it makes the URL persistently bookmarkable
4. Ensure this works with replaceState initial state from T01 (no duplicate history entry)

## Inputs

- `frontend/static/js/workspace.js (initWorkspaceLayout, openTab, openViewTab)`
- `T01 output (pushState/popstate handler)`

## Expected Output

- `frontend/static/js/workspace.js (modified — deep link handler)`

## Verification

Navigate to /browser/?tab=<known-object-iri>. Object tab opens and is focused. URL still shows ?tab=. Refresh the page — same object tab opens. Navigate to /browser/?tab=view:<viewId> — view tab opens.
