---
depends_on: [M009]
---

# M017: GitHub Issues Sync App

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

GitHub Issues + PRs bidirectional sync app for the M009 App Platform. Maps GitHub issues to `bpkm:Task` objects with label-based tags, milestone mapping, assignee resolution, and cross-repo dependency tracking. Developer audience — syncing the tool they already live in.

## Why This Milestone

Developers manage work in GitHub Issues. Syncing issues into SemPKM lets them link tasks to Notes, Concepts, and Projects — relationships that don't exist in GitHub. Cross-repo dependency visualization via the task graph is a unique value proposition.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Install the GitHub sync app and authenticate via GitHub OAuth
- Select repositories to sync
- See GitHub issues as `bpkm:Task` objects with status (open→todo, closed→done), labels as tags, assignees mapped to Persons
- See PRs linked to issues via edges
- Edit issue titles/descriptions in SemPKM and see changes in GitHub
- View cross-repo task dependencies in the task graph

### Entry point / environment

- Entry point: Admin > Applications > Install "GitHub Sync"
- Environment: Docker Compose with M009 App Platform
- Live dependencies involved: GitHub REST API

## Completion Class

- Contract complete means: OAuth flow, issue sync, PR linking, push-back, unit tests
- Integration complete means: issues appear as tasks, PRs link correctly, cross-repo edges render in graph
- Operational complete means: webhook processing for instant sync, rate limit handling, pagination for large repos

## Final Integrated Acceptance

- User syncs a repo with 50+ issues, all appear as tasks with correct metadata
- User closes an issue in SemPKM, it closes in GitHub
- PR linked to issue shows as edge in relations panel

## Risks and Unknowns

- **GitHub webhook delivery** — same localhost limitation as Linear. Polling for local dev.
- **PR-to-issue linking** — GitHub uses "Closes #42" in PR bodies. Need text parsing or API `timeline` events.

## Existing Codebase / Prior Art

- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` — GitHub not explicitly mapped but follows same bpkm:Task pattern
- M016 — Linear sync app establishes the sync pattern
- M009 — App Platform SDK

## Relevant Requirements

- New: SYNC-05 (GitHub OAuth), SYNC-06 (GitHub issue sync), SYNC-07 (GitHub PR linking)

## Scope

### In Scope

- GitHub OAuth App authentication
- Issue → bpkm:Task mapping (title, body, state, labels, assignees, milestone)
- PR → bpkm:Task with `externalProvider: "github-pr"` distinction
- PR-to-issue linking via edges
- Label → tags mapping
- GitHub milestone → bpkm:Milestone mapping
- Webhook endpoint for push events
- Settings: repo selection, sync direction, poll interval

### Out of Scope / Non-Goals

- GitHub Actions / workflow runs
- GitHub Discussions
- GitHub Projects (board) sync
- Code review comments
- Release/tag sync

## Technical Constraints

- GitHub REST API v3 (not GraphQL — simpler for this scope)
- Rate limit: 5000 requests/hour with token auth
- App Platform SDK (CommandClient, HttpClient)

## Integration Points

- **App Platform (M009)** — lifecycle, SDK, scheduler
- **bpkm:Task** — mapping target (M011)
- **GitHub REST API** — external dependency
- **M016 patterns** — reuse sync architecture, normalization, conflict resolution
