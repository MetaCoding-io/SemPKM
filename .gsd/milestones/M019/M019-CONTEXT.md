---
depends_on: [M009]
---

# M019: Todoist Sync App

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

Todoist bidirectional sync app. Simple REST API, individual user focus. Maps Todoist tasks to `bpkm:Task` objects with projects, labels, priorities, and due dates. Quick build leveraging patterns from M016 (Linear).

## Why This Milestone

Todoist has a large individual user base. Its simple data model (tasks, projects, labels) maps cleanly to bpkm:Task. This is the easiest sync app after Linear — validates the pattern works for simpler APIs too.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Install Todoist sync app and authenticate via Todoist OAuth
- Select projects to sync
- See Todoist tasks as bpkm:Task objects
- Edit tasks bidirectionally
- See Todoist labels as tags, priority (1-4) mapped to SemPKM priority levels

### Entry point / environment

- Entry point: Admin > Applications > Install "Todoist Sync"
- Environment: Docker Compose with M009 App Platform
- Live dependencies involved: Todoist REST API v2

## Completion Class

- Contract complete means: OAuth, pull/push sync, field mapping, unit tests
- Integration complete means: tasks appear correctly, edits round-trip
- Operational complete means: reliable polling, handles Todoist API errors

## Final Integrated Acceptance

- User syncs Todoist project, tasks appear with correct priorities and due dates
- User completes a task in SemPKM, it's marked complete in Todoist

## Existing Codebase / Prior Art

- M016 — Linear sync app pattern
- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` — Todoist priority mapping (1-4)

## Relevant Requirements

- New: SYNC-12 (Todoist sync)

## Scope

### In Scope

- Todoist OAuth 2.0 + REST API v2
- Task → bpkm:Task mapping (content, description, priority, due, labels, project)
- Project → bpkm:Project mapping
- Label → tags mapping
- Bidirectional sync with conflict resolution
- Settings: project selection, poll interval

### Out of Scope / Non-Goals

- Todoist comments, sections, filters
- Todoist Karma/productivity stats
- Sub-task nesting beyond one level

## Technical Constraints

- Todoist REST API v2
- App Platform SDK
- Simple API — no GraphQL, no complex webhook payloads

## Integration Points

- **App Platform (M009)**, **bpkm:Task (M011)**, **M016 patterns**
