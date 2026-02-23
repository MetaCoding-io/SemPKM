# Architecture Research: SemPKM v2.0 Tighten Web UI

## Summary

Five new subsystems integrate into the existing FastAPI + htmx codebase. Settings system is the foundation (LLM and theme depend on it). All subsystems use existing patterns — SQL for structured data, SPARQL for RDF queries, htmx partials for UI.

## Subsystem Architecture

### 1. Split Pane Manager

**Approach:** Pure JS-side concern using nested Split.js instances.

`EditorGroupManager` class manages multiple editor groups with per-group tab bars. Backend is unaware of groups — serves same htmx partials to any target. State stored in sessionStorage.

- Drag-to-split deferred for v2.0; use context menu "Split Right/Down" instead
- Each editor group is a `<div>` with its own tab bar and content area
- Split.js creates horizontal/vertical splits between groups
- Tab state per group stored in sessionStorage (extends current single-group tab model)

**Module placement:** `frontend/static/js/editor-groups.js` (new)

### 2. Settings System

**Approach:** SQL database storage (new `settings` table) with scope-based layering.

- Scopes: `global` < `user` (user overrides global)
- Schema registry in Python defines valid keys, types, and defaults
- Extends existing `InstanceConfig` pattern from auth module
- Mental models can register settings via manifest

**API surface:**
- `GET /api/settings/{scope}` — read settings for scope
- `PATCH /api/settings/{scope}` — update settings
- `GET /api/settings/schema` — get available settings with types/defaults

**Database:**
```sql
CREATE TABLE settings (
    id INTEGER PRIMARY KEY,
    scope TEXT NOT NULL,          -- 'global' or 'user:{user_id}'
    key TEXT NOT NULL,
    value TEXT NOT NULL,          -- JSON-encoded value
    updated_at DATETIME,
    UNIQUE(scope, key)
);
```

**Module placement:** `backend/app/settings/` (new module: models.py, service.py, router.py, schema.py)

### 3. LLM Proxy

**Approach:** `httpx` async streaming to OpenAI-compatible APIs, `sse-starlette` EventSourceResponse for SSE to client.

- No OpenAI SDK dependency — raw HTTP to `/v1/chat/completions`
- API keys stored in settings (server-side only, masked in API responses)
- Nginx needs `proxy_buffering off` for SSE passthrough

**API surface:**
- `POST /api/llm/chat` — streaming chat completion (SSE)
- `GET /api/llm/models` — list available models from configured provider
- `GET /api/llm/status` — test connection to configured provider

**Module placement:** `backend/app/llm/` (new module: service.py, router.py)

### 4. Event Log Explorer

**Approach:** SPARQL queries over event named graphs (already stored by EventStore).

- New read-only `LogService` cleanly separated from write-path `EventStore`
- Paginated timeline with operation/IRI/date filters
- Inline diff expansion (compare event payload to previous state)
- Undo = generate inverse command and submit to existing command API

**SPARQL pattern for timeline:**
```sparql
SELECT ?g ?type ?ts ?user ?target
FROM NAMED <urn:sempkm:events>
WHERE {
    GRAPH ?g {
        ?g a ?type ;
           sempkm:committedAt ?ts ;
           sempkm:performedBy ?user ;
           sempkm:target ?target .
    }
}
ORDER BY DESC(?ts)
LIMIT 50 OFFSET ?offset
```

**Module placement:** `backend/app/events/log_service.py` (new, alongside existing store.py)

### 5. Theme System

**Approach:** CSS custom properties with `data-theme` attribute on `<html>`.

- localStorage persistence for theme preference
- Anti-FOUC inline script in `<head>` (reads localStorage before paint)
- Custom DOM event `themeChanged` for loose coupling
- Cytoscape, CodeMirror react to theme changes independently
- Settings system stores preference server-side for cross-device sync

**Module placement:**
- `frontend/static/css/theme-dark.css` (dark mode overrides)
- `frontend/static/js/theme.js` (toggle logic, ~20 lines)
- Inline `<script>` in base template for anti-FOUC

## Implementation Order (dependency-based)

1. **Settings System first** — LLM proxy depends on it for config, theme depends on it for persistence
2. **Theme System second** — CSS-only change, low risk, high visible impact
3. **Bottom Panel + Split Panes** — Layout infrastructure needed before event log
4. **Event Log Explorer** — Needs bottom panel to live in
5. **LLM Proxy last** — Depends on settings, least user-facing in v2.0

## Confidence Assessment

| Area | Level | Reason |
|------|-------|--------|
| Split Panes | HIGH | Direct codebase analysis of existing Split.js + verified nested support |
| Settings | HIGH | Extends proven existing SQL patterns (InstanceConfig, auth models) |
| LLM Proxy | HIGH | sse-starlette verified, httpx already in deps |
| Event Log | HIGH | SPARQL patterns derived from existing event models and store.py |
| Theme | HIGH | CSS custom properties already in use, anti-FOUC well-established |

## Open Questions

- Event log SPARQL performance at scale (>10K named graphs) — needs RDF4J LMDB index validation
- CodeMirror 6 theme with CSS `var()` — may need CM6 `dark` flag toggling on theme switch
- `sse-starlette` vs plain `StreamingResponse` with manual SSE formatting — both work
