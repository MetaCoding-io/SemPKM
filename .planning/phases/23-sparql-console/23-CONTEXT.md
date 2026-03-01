# Phase 23: SPARQL Console - Context

**Gathered:** 2026-02-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Embed the @zazuko/yasgui v4.5.0 SPARQL console into SemPKM's existing bottom panel, replacing the placeholder SPARQL tab stub. Includes a custom YASR renderer for SemPKM object IRI links and localStorage query persistence. No backend changes required — existing `/api/sparql` endpoint is Yasgui-compatible.

</domain>

<decisions>
## Implementation Decisions

### UI Location
- SPARQL Console lives in the bottom panel SPARQL tab only (replaces existing stub)
- Not a workspace tab — users access it via Ctrl+J → SPARQL tab
- Consistent with where the placeholder already exists

### IRI Link Behavior
- Clicking a SemPKM IRI in SPARQL results opens the object in the active editor group
- Same pattern as `openTab()` used by nav tree — not a new tab, opens in whichever group user last used
- Mirrors VS Code "open in active editor" behavior

### Query Persistence
- localStorage key: `sempkm-sparql` (committed in DECISIONS.md)
- Tabs and query history survive full browser session close/reopen

### Authentication
- Existing session cookie handles auth transparently — no changes needed
- Yasgui sends cookies with requests automatically (same-origin)

### Dark Mode
- Dark mode overrides must apply to Yasgui UI
- Use CSS custom property overrides via `--yasgui-*` or class-based targeting to match workspace theme tokens

### Claude's Discretion
- Exact Yasgui configuration options (endpoint URL, default query, plugin selection)
- Whether to show both SPARQL query and result panes by default or collapse result pane initially

</decisions>

<specifics>
## Specific Ideas

- The existing bottom panel SPARQL tab is already stubbed — Phase 23 fills it in
- Custom YASR cell renderer: detect SemPKM IRIs (matching `https://` scheme in the triplestore domain), render as clickable links that call `openTab()` with the IRI
- The `/api/sparql` endpoint already works — Yasgui just needs to be pointed at it

</specifics>

<deferred>
## Deferred Ideas

- SPARQL Console as a workspace tab (full editor group tab) — not needed for v2.2, bottom panel is sufficient
- Query sharing / export — future phase

</deferred>

---

*Phase: 23-sparql-console*
*Context gathered: 2026-02-28*
