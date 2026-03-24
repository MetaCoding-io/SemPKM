---
id: S01
milestone: M037
title: "Backend Context API & Workspace Indicator"
status: done
tasks_completed: [T01, T02, T03, T04]
tasks_total: 4
duration: ~53m
verification_result: passed
completed_at: 2026-03-23
---

# S01: Backend Context API & Workspace Indicator — Summary

## What This Slice Delivered

A complete user context awareness backend — model, service, API, real-time SSE streaming, and workspace sidebar indicator — that serves as the foundation for all downstream context features (rules engine, mobile app, push notifications).

**Concrete capability:** An authenticated client can POST context snapshots (location zone, activity, time period, calendar event, device ID) to `POST /api/context/update`, retrieve the current context with staleness detection via `GET /api/context/current`, and receive real-time updates through `GET /api/context/stream` (SSE). The workspace sidebar shows a compact context indicator that updates in real-time and degrades to "Context unknown" when context is stale (>15 min TTL) or the SSE connection drops.

## Architecture

### New Package: `backend/app/context/`

| File | Purpose |
|------|---------|
| `models.py` | `UserContext` SQLAlchemy model — one row per user (upsert), FK to `users.id` with CASCADE |
| `service.py` | `ContextService` — `update()` (SELECT→INSERT/UPDATE, only writes provided fields), `get_current()` (computes `is_stale` from `updated_at` vs configurable TTL, default 900s) |
| `broadcast.py` | `ContextBroadcast` — SSE fan-out following `LintBroadcast` pattern, reuses `SSEEvent` dataclass |
| `router.py` | 3 endpoints: POST `/api/context/update` (rate-limited 12/min), GET `/api/context/current`, GET `/api/context/stream` (SSE with 30s keepalive) |

### Wiring

- `ContextService` + `ContextBroadcast` registered on `app.state` via `main.py` lifespan
- `get_context_service` and `get_context_broadcast` dependency functions in `dependencies.py`
- Context router included via `app.include_router(context_router)`
- Alembic migration 018 creates `user_context` table (chains from 017)

### Frontend

- `context-indicator.js` — IIFE fetching initial state, then consuming `EventSource('/api/context/stream')` for live updates
- `context-indicator.css` — Compact chip layout with dot separators, `.context-stale` dimming (opacity 0.5), Lucide icon sizing with `flex-shrink:0`
- Indicator placed between `#nav-pane` pane-header and pane-content — fixed while explorer sections scroll

## Key Decisions

| Decision | Rationale |
|----------|-----------|
| Reuse `SSEEvent` from `app.lint.broadcast` | Avoids duplicating the dataclass; both broadcasts emit the same event shape |
| Rate limit: 12/minute per IP via slowapi | Matches plan's ~1/5s target; uses existing slowapi infrastructure |
| Empty POST body → 422 (not silent accept) | Forces callers to send at least one field; prevents no-op writes |
| `model_dump(exclude_unset=True)` for partial updates | Distinguishes "not sent" from "sent as null" — only overwrites fields caller explicitly provided |
| Indicator between pane-header and pane-content | Fixed position while explorer sections scroll; visible regardless of collapsed state |

## Patterns Established

1. **Upsert pattern** in `ContextService.update()` — SELECT then INSERT/UPDATE, only writing fields explicitly provided via `exclude_unset`
2. **Naive datetime guard** — `replace(tzinfo=utc)` before timedelta math (existing K002 knowledge applied)
3. **SSE EventSource frontend pattern** — connect on DOMContentLoaded, listen for named events, fall back to stale state on error/disconnect
4. **Icon-to-context mapping** — `LOCATION_ICON`, `ACTIVITY_ICONS`, `TIME_ICONS` objects for extending with new context facets

## Test Coverage

- 13 service tests: insert, merge-update, partial update, staleness transitions (zero-TTL technique), upsert row uniqueness, TTL passthrough, calendar_busy default, device_id persistence
- 15 router tests: POST/GET success paths, SSE event publishing, empty body 422, partial fields, field length validation, null context, stale context, auth enforcement on all 3 endpoints, Pydantic model validation
- **28 total, all passing in <1s**

## Observability Surfaces

- `context.update` structured log on every upsert (user_id, location_zone, device_id)
- `context.stale` structured log when staleness detected on read (user_id, age_seconds, ttl)
- `GET /api/context/current` returns full state including `is_stale`, `updated_at`, `ttl_seconds`
- HTTP 429 with `Retry-After` on rate limit breach
- HTTP 422 with field-level Pydantic errors on invalid payload
- `#context-indicator` DOM element with `.context-stale` class for DevTools inspection
- `EventSource('/api/context/stream')` visible in browser Network tab

## What S02 Needs to Know

- **`ContextService`** is on `app.state.context_service` — call `get_current(user_id)` to get context dict with `is_stale`
- **`ContextBroadcast`** is on `app.state.context_broadcast` — hook `publish()` to trigger rule evaluation after each context update
- **The router already calls `broadcast.publish()`** after every successful update — S02 can add a subscriber to the broadcast for rule evaluation, or hook into the router's update flow
- **SSE event type is `context_update`** with JSON data containing all context fields — S02 can add a `persona_switched` event type to the same stream
- **Auth is dual-mode** — `get_current_user_or_api` accepts both session cookie and Bearer API token, so mobile app (S03) can authenticate with an API key

## Files Created

| File | Lines |
|------|-------|
| `backend/app/context/__init__.py` | ~1 |
| `backend/app/context/models.py` | ~45 |
| `backend/app/context/service.py` | ~155 |
| `backend/app/context/broadcast.py` | ~50 |
| `backend/app/context/router.py` | ~165 |
| `backend/migrations/versions/018_user_context.py` | ~45 |
| `backend/tests/test_context_service.py` | ~170 |
| `backend/tests/test_context_router.py` | ~250 |
| `frontend/static/js/context-indicator.js` | ~200 |
| `frontend/static/css/context-indicator.css` | ~80 |

## Files Modified

- `backend/app/main.py` — lifespan wiring + router inclusion
- `backend/app/dependencies.py` — 2 dependency functions
- `backend/app/templates/browser/workspace.html` — indicator HTML + CSS/JS links
