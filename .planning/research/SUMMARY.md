# Research Summary: v2.0 Tighten Web UI

## Key Decisions from Research

### Libraries
- **Driver.js replaces Shepherd.js** — Shepherd.js v14 is AGPL-3.0. Driver.js is MIT, 5kb, zero-dep.
- **Only 4 new JS libs needed**: SortableJS (tab drag), Driver.js (tours), Lucide (icons), jsondiffpatch (event diffs). ~61kb gzip total.
- **No new backend dependencies** — httpx (existing) for LLM proxy, existing SQLAlchemy for settings.

### Architecture
- **Settings system is the foundation** — LLM proxy and dark mode depend on it. SQL storage.
- **Split panes are pure JS** — nested Split.js with EditorGroupManager class. Backend unaware of groups.
- **LLM proxy** — httpx async streaming + sse-starlette. Nginx needs `proxy_buffering off`.
- **Theme system** — CSS custom properties + `data-theme` attribute + anti-FOUC inline script.
- **Event log** — SPARQL over event named graphs with cursor-based pagination and lazy diffs.

### UX Patterns
- **Read-only view is highest-impact** — default to read mode, Edit button switches to SHACL form. `Ctrl+E` toggle.
- **Split panes: horizontal-only for v2.0** — 80% of value at 40% of cost. Max 4 groups.
- **Sidebar: VS Code Activity Bar** — 48px icon rail when collapsed, 220px expanded. Groups: Home, Admin, Meta, Apps, Debug.
- **Dark mode: tri-state** — System/Light/Dark. VS Code "Dark+" colors. Flash prevention via inline `<head>` script.
- **Settings: localStorage for v2.0** — except LLM API keys (server-side encrypted). VS Code-style GUI.

### Critical Pitfalls
1. **Split.js has no dynamic pane API** — must destroy/recreate. Design editor group data model FIRST.
2. **Dark mode misses CodeMirror, Cytoscape, ninja-keys** — each needs explicit integration.
3. **htmx afterSwap listener accumulation** — fix cleanup architecture BEFORE adding new features.
4. **Nginx buffers SSE** — LLM streaming silently breaks without explicit config.
5. **Event log OFFSET pagination degrades** — use cursor-based pagination from day one.

## Implementation Order (dependency-based)

1. **Bug fixes + afterSwap cleanup** — foundational, unblocks everything
2. **Read-only object view** — highest-impact UX change
3. **Sidebar reorganization + user menu + collapsible** — navigation modernization
4. **Dark mode + rounded tabs** — visual polish (CSS custom properties already in place)
5. **Split panes + bottom panel** — layout infrastructure (biggest engineering effort)
6. **Settings system + node type icons** — configuration infrastructure
7. **Event log explorer** — lives in bottom panel
8. **LLM connection config** — depends on settings, needs nginx SSE config
9. **Driver.js tutorials** — last, since tours reference UI elements that must exist

## Risk Assessment

| Area | Risk | Mitigation |
|------|------|------------|
| Split panes | HIGH | Horizontal-only for v2.0; design data model first |
| Dark mode + CodeMirror | MEDIUM | Compartment-based theme switching per instance |
| Event log performance | MEDIUM | Cursor pagination + event index graph |
| LLM streaming + nginx | LOW | Well-documented SSE config |
| Settings system | LOW | Start minimal (5-10 settings), expand later |
