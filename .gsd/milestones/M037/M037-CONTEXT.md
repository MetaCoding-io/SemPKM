---
depends_on: [M033]
---

# M037: User Context & Mobile App

**Gathered:** 2026-03-22
**Status:** Queued — pending auto-mode execution

## Project Description

Build a native mobile app (React Native, iOS + Android) that acts as a real-time context provider for SemPKM — delivering location, activity, time-of-day, and calendar context to the backend. The backend gains a Context API for storing and streaming user context, and a rules engine that automatically switches workspace personas based on context signals. This is the first mobile surface for SemPKM and the foundation for context-aware features across the platform.

## Why This Milestone

SemPKM currently has no awareness of what the user is doing outside the browser. The workspace looks the same whether you're at your desk deep in research, commuting on a train, or relaxing at home. Personas (M012) let users manually switch workspace layouts, but manual switching is friction — people don't do it.

A mobile app running in the background can continuously provide context: you're at the office (GPS geofence), it's 2pm (time), you have a focus block until 3pm (calendar), and you're stationary (motion). The backend uses this to automatically activate the right persona, filter notifications, and (in M038) schedule media.

This unlocks a category of features impossible without real-time context: the AI copilot (M035) can say "you have 3 tasks before your 3pm meeting" because it knows your calendar and location. The media scheduler (M038) can switch from podcasts to focus music when it detects you've arrived at the office.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Install the SemPKM mobile app on iOS or Android
- Configure home/work/other location zones via map interface in the mobile app
- See their current detected context (location zone, activity, time period) in the mobile app
- See their workspace persona automatically switch when they arrive at the office or return home
- Configure context→persona rules in the SemPKM settings UI (e.g., "at office during work hours → Project Manager persona")
- Receive context-filtered push notifications (overdue tasks only during work hours, not on weekends)
- See current context displayed in the workspace sidebar (small indicator showing detected location/activity)

### Entry point / environment

- Entry point: Mobile app (iOS/Android via React Native), SemPKM workspace (context indicator + auto-persona)
- Environment: Mobile device + Docker Compose backend
- Live dependencies involved: GPS, device calendar, device motion sensors, push notification service (FCM/APNs)

## Completion Class

- Contract complete means: mobile app reads GPS/calendar/motion, posts context to API, backend stores context and evaluates rules, persona switching triggers
- Integration complete means: arriving at office geofence triggers persona switch visible in workspace, calendar focus block suppresses notifications
- Operational complete means: background location works on both iOS and Android, context updates survive app backgrounding and device sleep, reconnects after network loss

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User installs mobile app, configures home and office geofences on the map
- User drives from home to office — mobile app detects location change and pushes context update
- Workspace persona automatically switches from "Home" to "Work" within 60 seconds of arrival
- User has a calendar focus block — mobile push notifications are suppressed during that block
- User opens workspace and sees context indicator showing "Office • Work Hours • Focus Block"
- Context rules are editable in SemPKM settings UI — user adds a new rule and it takes effect

## Risks and Unknowns

- **React Native is new to this project** — Everything is Python + vanilla JS currently. React Native adds a JavaScript build toolchain (Metro), platform-specific code (iOS/Android), and app store deployment. Significant new surface area.
- **iOS background location** — Apple requires "Always Allow" location permission with a specific use-case justification. App Store review may reject without compelling privacy disclosure. Geofencing (monitoring regions) is more battery-friendly and review-friendly than continuous GPS tracking.
- **Android background restrictions** — Android 12+ restricts background location and foreground service requirements. Need a foreground notification for persistent location monitoring.
- **Push notification infrastructure** — Firebase Cloud Messaging (Android) + APNs (iOS). The backend needs to store device tokens and dispatch notifications. This is new infrastructure — SemPKM currently has no push channel.
- **Context staleness** — If the mobile app loses connectivity or is killed by the OS, context becomes stale. Need a TTL on context (e.g., context older than 15 minutes is "unknown") and graceful degradation when context is unavailable.
- **Privacy sensitivity** — Location tracking is intimate data. Must be transparent, user-controllable, and stored minimally (current state only, no location history in the knowledge graph).

## Existing Codebase / Prior Art

- `backend/app/persona/` — PersonaService with CRUD, activation, state save (M012). Auto-persona switching hooks into activate_persona(). Verified on main.
- `backend/app/auth/dependencies.py` — `get_current_user_or_api` dual-auth for Bearer token API access. Mobile app authenticates the same way as the browser extension. Verified on main.
- `backend/app/config.py` — Settings model. Context rules can be stored as user settings or in a dedicated table.
- `extension/shared/api-client.js` — SemPKMClient pattern for external API access. The mobile app needs an equivalent in React Native (or reuse via React Native's fetch).
- `backend/app/apps/scheduler.py` — AppScheduler pattern for periodic tasks. Context rule evaluation could follow a similar tick-based pattern.
- `frontend/static/js/workspace.js` — Workspace init, persona loading, sidebar rendering. Context indicator would be a new sidebar element.
- `backend/app/middleware/` — TimingMiddleware pattern. Context middleware could inject current context into request state for use by any endpoint.
- M013 API surface — Bearer token auth, JSON responses, CORS headers. Mobile app uses the same API contract.

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions.

## Relevant Requirements

- New requirements: CTX-01 through CTX-10+ covering mobile app, context API, geofencing, auto-persona rules, push notifications, workspace context indicator

## Scope

### In Scope

**Mobile App (React Native):**
- Cross-platform iOS + Android from single codebase
- Onboarding: instance URL + API key configuration (matching extension pattern)
- Location monitoring via geofencing (define circular zones for home/work/gym/etc.)
- Activity detection (stationary/walking/driving/cycling via device motion)
- Time-of-day classification (morning/work-hours/evening/night, configurable boundaries)
- Device calendar read access for current/upcoming event context
- Background context updates pushed to SemPKM API at configurable interval
- Push notification display with context-aware filtering
- Minimal UI: context dashboard showing current detected state, zone map editor, settings

**Backend Context API:**
- `POST /api/context/update` — mobile app pushes context snapshot (location zone, activity, time period, calendar event)
- `GET /api/context/current` — any client reads current context (workspace, copilot, apps)
- Context stored in SQLite per-user (ephemeral state, not RDF — current state only, no history)
- Context SSE stream (`GET /api/context/stream`) for real-time workspace updates
- Context TTL — context older than configurable threshold (default 15 min) marked as "unknown"
- Alembic migration for context tables

**Automatic Persona Switching:**
- Context rules model: IF conditions (location=X AND timeOfDay=Y AND activity=Z) THEN persona=P
- Rules stored in SQLite per-user (or as user settings JSON)
- Rule evaluation on every context update — if matching rule differs from active persona, switch
- Rule management UI in SemPKM settings (add/edit/delete rules, test against current context)
- Override: manual persona switch takes priority until next context change (or configurable lock duration)

**Push Notifications:**
- Device token registration endpoint (`POST /api/notifications/register`)
- Firebase Cloud Messaging integration (Android) + APNs via FCM (iOS)
- Notification types: overdue tasks, upcoming events, validation warnings
- Context-aware filtering: suppress work notifications outside work hours, suppress all during focus blocks
- Notification preferences in mobile app settings

**Workspace Context Indicator:**
- Small status bar in workspace sidebar showing current detected context
- Updates in real-time via SSE context stream
- Shows: location zone icon, time period, activity indicator, active calendar event name
- Click expands to show context details and active rules

### Out of Scope / Non-Goals

- Full SemPKM workspace in mobile (browse objects, edit forms) — mobile is a context provider, not a full client
- Location history or GPS tracking (only current geofence state stored)
- Wearable device integration (Apple Watch, Fitbit)
- Bluetooth beacon proximity detection
- Context-based object creation (future — AI copilot could use context to suggest templates)
- App Store submission in this milestone (TestFlight/internal distribution first)

## Technical Constraints

- React Native with TypeScript for type safety
- iOS deployment target: 15.0+ (geofencing and background modes)
- Android min SDK: 26 (Android 8.0+, for foreground service requirement)
- Background location: geofencing API (CLLocationManager regions on iOS, GeofencingClient on Android) not continuous GPS
- Push notifications via Firebase Cloud Messaging (handles both platforms)
- Mobile app authenticates via Bearer token (existing get_current_user_or_api)
- Context API responses are JSON — no htmx, no HTML fragments
- Context data is ephemeral state in SQLite — NOT stored in the RDF triplestore
- Privacy: no location coordinates stored, only zone names (home/work/custom label)

## Integration Points

- **PersonaService (M012)** — activate_persona() called by context rule engine on match
- **Auth (M013)** — Bearer token auth for mobile API calls
- **M035 AI Copilot** — copilot reads current context to add situational awareness to responses
- **M038 Media Scheduler** — consumes context for time-of-day and activity-based media scheduling
- **Workspace sidebar** — context indicator element, SSE-driven real-time updates
- **Settings UI** — context rule management section
- **Push notification service** — new infrastructure, no existing pattern to follow

## Open Questions

- **React Native vs Flutter** — React Native is more familiar (JS ecosystem) but Flutter has better background processing and native performance. React Native is the default unless research surfaces a blocker.
- **Geofence count limits** — iOS limits to 20 simultaneous monitored regions. Android has a 100 limit. Most users need 3-5 zones (home, work, gym, etc.) so this should be fine, but document the limit.
- **Calendar permission scope** — Read-only access to device calendar for event titles and times. Do NOT sync calendar events into SemPKM (that's what M018-M021 calendar sync apps do). Only use for context detection.
- **Context update frequency** — How often should the mobile app push context? On every geofence transition (event-driven, not polling) + on calendar event start/end + on significant activity change. NOT on a fixed interval — that wastes battery.
- **Offline context** — If the mobile app can't reach the SemPKM backend, should it queue context updates? Yes — local queue with retry on reconnect. But queued context is stale by definition — apply TTL on receipt.
