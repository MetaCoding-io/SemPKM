---
depends_on: [M009]
---

# M022: Asana Sync App

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

Asana bidirectional sync app. Maps Asana tasks (with subtasks, sections, custom fields) to `bpkm:Task` objects. More complex than Linear/GitHub due to Asana's custom-field-based status/priority (no native enum) and section-based Kanban mapping.

## Why This Milestone

Asana has a large user base across teams and professionals. Its lack of native status/priority fields means sync requires user configuration during setup — establishing the pattern for "configurable field mapping" that Monday.com and other custom-field-heavy providers will also need.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Install Asana sync and authenticate via Asana OAuth
- Select workspaces and projects to sync
- Configure status mapping (Asana custom field or section names → bpkm:taskStatus)
- Configure priority mapping (Asana custom field → bpkm:priority)
- See Asana tasks as bpkm:Task objects with subtask nesting (up to 5 levels)
- See Asana tags as SemPKM tags, followers as linked Persons

### Entry point / environment

- Entry point: Admin > Applications > Install "Asana Sync"
- Environment: Docker Compose with M009 App Platform
- Live dependencies involved: Asana REST API

## Completion Class

- Contract complete means: OAuth, configurable field mapping, subtask nesting, custom field discovery
- Integration complete means: tasks sync with user-configured status/priority mapping
- Operational complete means: webhook processing, rate limit handling, opt_fields optimization

## Final Integrated Acceptance

- User configures "In Progress" section → in-progress mapping, tasks appear with correct status
- Subtasks appear as child tasks linked via bpkm:parentTask
- Custom "Priority" field maps to bpkm:priority levels

## Existing Codebase / Prior Art

- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` § Asana — complete mapping, status/priority via custom fields, section-based mapping
- M016 — Linear sync pattern

## Relevant Requirements

- New: SYNC-15 (Asana sync)

## Scope

### In Scope

- Asana OAuth 2.0
- Task, subtask, project, section mapping
- Custom field discovery and configurable mapping (status, priority, story points)
- Section-based status mapping (alternative to custom field)
- Subtask nesting (up to 5 levels)
- Webhook processing (project-scoped, GID-only payloads)
- Settings: workspace/project selection, field mapping configuration

### Out of Scope / Non-Goals

- Asana Portfolios, Goals, Approvals, Custom Rules

## Technical Constraints

- Asana REST API, cost-based rate limiting (~1500 requests/min)
- opt_fields required for efficient queries
- Webhook payloads contain only GIDs — follow-up GET required
- App Platform SDK

## Integration Points

- **App Platform (M009)**, **bpkm:Task (M011)**, **M016 patterns**, **Asana REST API**
