---
depends_on: [M009]
---

# M024: Monday.com Sync App

**Gathered:** 2026-03-16
**Status:** Queued — pending auto-mode execution

## Project Description

Monday.com sync app with the unique challenge of webhook loop prevention. Monday's fully customizable column-based data model requires user configuration for every field mapping. GraphQL API with complexity-based rate limiting. Lowest priority task provider due to mapping complexity.

## Why This Milestone

Monday.com has a large user base but its column-centric model is the hardest to map. The critical technical challenge is webhook echo prevention — Monday has no webhook suppression, so API-originated changes re-trigger webhooks, causing infinite loops without a loop guard.

## User-Visible Outcome

### When this milestone is complete, the user can:

- Install Monday.com sync and authenticate via Monday OAuth
- Select boards to sync, configure column-to-property mapping
- See Monday items as bpkm:Task objects with configured status/priority mapping
- See Monday groups as taskGroup values
- Edit tasks bidirectionally without causing sync loops

### Entry point / environment

- Entry point: Admin > Applications > Install "Monday.com Sync"
- Environment: Docker Compose with M009 App Platform
- Live dependencies involved: Monday.com GraphQL API

## Completion Class

- Contract complete means: OAuth, column mapping configuration, LoopGuard implementation, GraphQL queries
- Integration complete means: items sync with user-configured mappings, no echo loops
- Operational complete means: complexity-based rate limit handling, webhook processing with loop guard

## Final Integrated Acceptance

- User maps Monday "Status" column to bpkm:taskStatus, items sync with correct status
- Changing a task in SemPKM doesn't trigger an infinite webhook loop
- Monday groups appear as taskGroup values on tasks

## Existing Codebase / Prior Art

- `.gsd/design/INTEGRATION-DOMAIN-MAPPING.md` § Monday.com — column mapping, LoopGuard implementation, webhook characteristics
- M016 — Linear sync pattern

## Relevant Requirements

- New: SYNC-17 (Monday.com sync)

## Scope

### In Scope

- Monday.com OAuth 2.0
- Board/group/item mapping
- User-configurable column → property mapping (setup wizard)
- Status column (custom labels) → configurable bpkm:taskStatus
- LoopGuard for webhook echo prevention (TTL-based recent changes tracking)
- Subitem → bpkm:parentTask (up to 5 levels, Enterprise)
- Dependency column → bpkm:dependsOn
- Tag column → bpkm:tags

### Out of Scope / Non-Goals

- Monday Workdocs, Dashboards, Automations, Apps framework
- Mirror columns (read-only via API)
- Board templates

## Technical Constraints

- Monday.com GraphQL API, complexity-based rate limiting (5M/query/minute)
- No delta query — poll or webhook based
- LoopGuard with 10s TTL window for echo detection
- App Platform SDK

## Integration Points

- **App Platform (M009)**, **bpkm:Task (M011)**, **M016 patterns**, **Monday.com GraphQL API**
