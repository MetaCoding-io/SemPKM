# Phase 19: Bug Fixes and E2E Test Hardening - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Two workstreams: (1) fix a set of priority bugs discovered through usage plus the backend concerns from CONCERNS.md, and (2) harden the e2e test suite to verify Phase 10-18 features have coverage and the suite stays green. No new features — only fixes, polish, and test hardening.

</domain>

<decisions>
## Implementation Decisions

### UI Bugs to Fix (user-discovered)

1. **Docs/tutorials link does not work** — The Docs tab (Phase 18) link is broken; fix so the docs tab opens correctly.
2. **Tutorial links don't work** — When the docs tab does open, clicking tutorial links fails; fix the Driver.js tutorial launch.
3. **Tab reload on every click** — Clicking an already-active tab in the object browser reloads it; clicking a tab should be a no-op if already active.
4. **Split tab shows new tab content in old tab** — When splitting (Ctrl+\\), the old tab displays the new tab's content instead of its own; old tab must retain its content after a split.
5. **Edit button doesn't work on first touch** — The Edit/Done toggle fails on first click but works on subsequent clicks; must work on first interaction.
6. **Autocomplete concepts dropdown missing** — In edit mode, the autocomplete for reference properties (e.g. Concepts) does not show a dropdown; dropdown must appear and be selectable.

### Tag Pill Display

- Property scope: `model:basic-pkm:tags` values only
- Display format: `#Label` inside a rounded pill element (e.g. `<span class="tag-pill">#Notes</span>`)
- Visual only — no click/navigation action
- Apply in both read-only and edit form views wherever this property's values are rendered

### Tooltip Consistency

- Target locations: nav tree item hover + graph node hover
- Source style: use the graph view tooltip as the reference (shortened prefix labels, table-aligned layout, slightly larger than current nav tree tooltip)
- Tooltip should show: Type label + object label in a small table/grid layout with shortened IRI prefixes

### Backend Bug Fixes (CONCERNS.md)

- **Label cache**: Call `label_service.invalidate(event_result.affected_iris)` after every `event_store.commit()` in browser router write handlers
- **Datetime timezone**: Replace all `datetime.now()` in browser router with `datetime.now(timezone.utc)`
- **EventStore DI**: Add `get_event_store` dependency to `dependencies.py`, inject via `Depends` in browser router write handlers
- **IRI validation**: Add validation that decoded IRIs are valid absolute URIs before SPARQL interpolation
- **Cookie secure**: Add `COOKIE_SECURE` env var (default `True`); use it in session cookie creation

### CORS Fix

- Add `CORS_ORIGINS` env var: comma-separated list of allowed origins (e.g. `http://localhost:3901,https://myprod.com`)
- When `CORS_ORIGINS` is set: use those origins with `allow_credentials=True`
- When `CORS_ORIGINS` is not set: default to `["*"]` with `allow_credentials=False` (safe open fallback, no credential leakage)

### Debug Endpoint Auth

- `/sparql` and `/commands` debug pages: add `Depends(require_role("owner"))` guard
- Owner role required, no DEBUG flag needed — simple and consistent with other owner-only pages

### E2E Test Hardening

- Target: maintain ≥118/123 passing on chromium with no regressions
- The 5 failing setup wizard tests (`00-setup/01-setup-wizard.spec.ts`) are a known infrastructure issue — document with a clear comment in the test file and/or a README note; do not skip or tag them
- Add new tests for critical Phase 10-18 paths: dark mode toggle, settings save, event log, split panes, tutorial launch
- Scope: add tests to cover success criteria #5 and #6 from the roadmap

### Claude's Discretion

- Exact pill CSS (color, border-radius, font-size — match the app's existing design language)
- Tooltip component implementation (custom CSS tooltip vs. existing popover infrastructure)
- Specific file locations for new e2e test specs
- Order of bug fixes within plan 19-01

</decisions>

<specifics>
## Specific Ideas

- Tag pills: user specified `#Label` format with rounded pill shape — like a hashtag badge
- Tooltip style reference: graph view tooltip is the gold standard (shortened prefix labels make it much more readable than raw IRIs)
- CORS: the env var approach gives flexibility for Docker (prod) and separate-port (dev) setups without code changes

</specifics>

<deferred>
## Deferred Ideas

- Alembic migration runner at startup — tech debt from CONCERNS.md, deferred (not in scope for Phase 19)
- ViewSpecService TTL cache — performance improvement from CONCERNS.md, deferred
- SMTP email delivery — missing feature from CONCERNS.md, separate future work
- Session cleanup job — maintenance task, deferred
- Dependency pinning in pyproject.toml — deferred
- Rate limiting on auth endpoints — security hardening, deferred

</deferred>

---

*Phase: 19-bug-fixes-and-e2e-test-hardening*
*Context gathered: 2026-02-26*
