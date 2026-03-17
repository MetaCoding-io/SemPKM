---
depends_on: [M009]
---

# M016: Linear Sync App

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

First task provider integration app built on the M009 App Platform. Bidirectional sync between Linear and SemPKM's `bpkm:Task` type. Validates the full sync app pattern: OAuth setup, scheduled polling, webhook processing, status normalization, field mapping, conflict resolution, and push-back of SemPKM changes to Linear.

## Why This Milestone

Linear has the best API of all task providers (rich webhook payloads, clean `state.type` enum for status normalization, GraphQL, `updatedAt` filtering for delta sync). Building the Linear app first establishes the sync pattern that all subsequent provider apps will follow. Linear's startup audience overlaps heavily with SemPKM's target users.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Install the Linear sync app from Admin > Applications
- Authenticate with their Linear workspace via OAuth
- Select which Linear teams/projects to sync
- See Linear issues appear as `bpkm:Task` objects in the object browser
- See task status, priority, assignee, due dates, labels mapped to SemPKM fields
- Edit a task in SemPKM and see the change reflected in Linear
- See "Linear" provider icon and external link on synced tasks
- View sync history in Admin > Applications > Linear detail page

### Entry point / environment

- Entry point: Admin > Applications > Install "Linear Sync"
- Environment: Docker Compose with M009 App Platform running
- Live dependencies involved: Linear API (external), RDF4J triplestore

## Completion Class

- Contract complete means: OAuth flow completes, poll-tasks fetches issues, field mapping covers all mappable fields, push-changes updates Linear via API, unit tests for normalization/mapping
- Integration complete means: synced tasks appear in object browser with correct types/properties, edits round-trip, task dependency graph shows cross-project dependencies
- Operational complete means: scheduled polling runs reliably, handles API rate limits, survives Linear API errors gracefully, sync state persists across restarts

## Final Integrated Acceptance

To call this milestone complete, we must prove:

- User authenticates with Linear, selects a project, and tasks appear in SemPKM within one poll cycle
- Task status, priority, and assignee map correctly (Linear "In Progress" → bpkm:taskStatus "in-progress")
- User changes a task's status in SemPKM, the change appears in Linear
- Linear webhook triggers immediate sync (not waiting for next poll cycle)
- Admin detail page shows successful sync runs with counts

## Risks and Unknowns

- **OAuth in Docker** — Linear OAuth redirect URL must be reachable. For local dev, `http://localhost:3000/app/linear/callback` should work.
- **Webhook delivery to local instance** — Linear webhooks can't reach localhost. Polling-only for local dev; webhooks for deployed instances.
- **Rate limits** — Linear allows 1500 requests/hour. Large workspaces may need pagination and backoff.

## Existing Codebase / Prior Art

- `.gsd/design/MENTAL-MODELS-EXPANSION-DESIGN.md` — Task/Milestone type definitions with integration properties
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` § Linear — complete field mapping, status normalization, priority mapping, API characteristics
- M009 App Platform — SDK with CommandClient, HttpClient, StateClient, task scheduler
- M011 — basic-pkm v2 with bpkm:Task type

> See `.gsd/DECISIONS.md` for all architectural and pattern decisions.

## Relevant Requirements

- New: SYNC-01 (Linear OAuth), SYNC-02 (Linear pull sync), SYNC-03 (Linear push sync), SYNC-04 (Linear webhook processing)

## Scope

### In Scope

- `apps/linear-sync/` app directory with manifest, requirements, app.py
- OAuth 2.0 flow with Linear API
- Scheduled `poll-tasks` task: fetch issues via GraphQL, create/update bpkm:Task objects
- `push-changes` task: watch for changes to Linear-synced tasks, push back to Linear
- Linear webhook endpoint for immediate sync
- Full field mapping per INTEGRATION-DOMAIN-MAPPING.md
- Status normalization via `state.type` enum
- Priority normalization (0-4 → low/medium/high/critical)
- Assignee matching by email (create Person if not found)
- Settings page: workspace/team/project selection, sync direction, poll interval
- Conflict resolution: provider wins for status, last-write-wins for title/description

### Out of Scope / Non-Goals

- Linear comments sync (future)
- Linear project/cycle as dashboard (future)
- Linear attachments
- Linear custom views
- Multiple Linear workspace support (single workspace per install)

## Technical Constraints

- Built on M009 App Platform SDK (CommandClient, HttpClient, StateClient)
- All writes via EventStore (standard or bulk mode)
- IRI prefix: `urn:sempkm:app:linear-sync:`
- Network permission: `api.linear.app` domain
- Python GraphQL client (gql or httpx direct)

## Integration Points

- **App Platform (M009)** — manifest, lifecycle, SDK, scheduler, admin
- **EventStore** — bulk mode for initial sync, standard for incremental
- **bpkm:Task type** — field mapping target (requires M011 basic-pkm v2)
- **Linear GraphQL API** — external dependency
- **Person matching** — email-based lookup against existing Person/Contact objects

## Open Questions

- **Initial sync volume** — Large Linear workspaces may have thousands of issues. Bulk EventStore handles this but initial sync could take minutes. Progress indicator needed in admin UI.
- **Closed issue handling** — Sync completed/cancelled issues? Current thinking: yes, with configurable cutoff (e.g., "sync issues updated in last 90 days").
