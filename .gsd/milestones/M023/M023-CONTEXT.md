---
depends_on: [M009]
---

# M023: Jira Sync App

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

Jira Cloud bidirectional sync app. Maps Jira issues to `bpkm:Task` objects with JQL-based filtered sync, Atlassian Document Format (ADF) → Markdown conversion, `statusCategory`-based status normalization, and Epic → Milestone mapping. The most complex task provider integration due to Jira's workflow customization depth.

## Why This Milestone

Jira dominates enterprise project management. Its `statusCategory.key` provides reliable status normalization across custom workflows. ADF→Markdown conversion is the main technical challenge. JQL enables powerful filtered sync ("sync only issues from Sprint X updated in last 15 minutes").

## User-Visible Outcome

### When this milestone is complete, the user can:

- Install Jira sync and authenticate via Atlassian Connect OAuth
- Select Jira projects to sync, optionally filter by JQL
- See Jira issues as bpkm:Task objects with rich descriptions (ADF converted to Markdown)
- See Jira Epics mapped to bpkm:Milestone
- See issue links ("blocks"/"is blocked by") as bpkm:dependsOn edges
- See Sprint names as taskGroup values
- Edit issue title/description in SemPKM, changes reflected in Jira

### Entry point / environment

- Entry point: Admin > Applications > Install "Jira Sync"
- Environment: Docker Compose with M009 App Platform
- Live dependencies involved: Jira Cloud REST API v3

## Completion Class

- Contract complete means: Atlassian OAuth, JQL filtering, ADF↔MD conversion, statusCategory normalization
- Integration complete means: issues sync with correct status/priority/assignee, epics as milestones
- Operational complete means: webhook processing, JQL-based incremental sync, rate limit handling

## Final Integrated Acceptance

- User syncs a Jira project, issues appear with Markdown-converted descriptions
- Custom workflow statuses normalize correctly via statusCategory (To Do→todo, In Progress→in-progress, Done→done)
- Jira Epic "Sprint 1" appears as bpkm:Milestone with linked tasks

## Existing Codebase / Prior Art

- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` § Jira — complete mapping, ADF conversion, statusCategory strategy
- M016 — Linear sync pattern

## Relevant Requirements

- New: SYNC-16 (Jira sync)

## Scope

### In Scope

- Atlassian Connect OAuth 2.0
- Issue → bpkm:Task with full field mapping
- Epic → bpkm:Milestone (configurable: Epic as Project vs Milestone)
- ADF → Markdown conversion (headings, paragraphs, lists, code blocks, mentions, links)
- Markdown → ADF conversion for push-back
- statusCategory-based normalization
- JQL-based filtered sync
- Issue link types → bpkm:dependsOn (for "blocks" link type)
- Sprint → taskGroup, Component → tags
- Webhook processing (project-scoped)

### Out of Scope / Non-Goals

- Jira Service Management, Jira Software boards, Confluence pages
- Custom field round-trip (blank-node approach deferred)
- Jira Server/Data Center (Cloud only)

## Technical Constraints

- Jira Cloud REST API v3, ADF format for rich text
- Rate limit: ~100 requests/sec burst
- adf-to-md / md-to-adf conversion libraries
- App Platform SDK

## Integration Points

- **App Platform (M009)**, **bpkm:Task (M011)**, **M016 patterns**, **Jira Cloud REST API**
