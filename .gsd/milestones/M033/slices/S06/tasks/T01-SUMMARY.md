---
id: T01
parent: S06
milestone: M033
provides:
  - AppManifestSchema extended with category, features, readme fields
  - Admin detail page redesigned catalog-first with ops collapsed
  - Admin list page shows category badges
key_files:
  - backend/app/apps/manifest.py
  - backend/app/templates/admin/apps/detail.html
  - backend/app/templates/admin/apps/list.html
  - backend/app/apps/admin_router.py
key_decisions: []
patterns_established:
  - "color-mix(in srgb, var(--color-primary) 15%, transparent) for category pill background"
observability_surfaces:
  - "Pydantic ValidationError on invalid category/features/readme at manifest parse time"
duration: 15m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Extend schema and redesign admin catalog pages

**Added category, features, readme fields to AppManifestSchema and redesigned admin detail page with catalog-first layout and collapsible Operations section**

## What Happened

Extended `AppManifestSchema` with three optional fields after `license`: `category` (str, max 64), `features` (list[str]), and `readme` (str, max 10000). All default to empty values for backward compatibility with existing manifests.

Redesigned the admin app detail template to lead with description, a features checklist (with Lucide check icons), permissions table, and model dependencies — the catalog showcase. All operational sections (status stats, logs, actions, task history, renderer overrides, data stats placeholder) are now inside a single `<details>` element with an "Operations" summary label.

Updated the admin list page to show a category pill on app cards when populated, using a semi-transparent primary-color background. Added `category` to the app dict built in `admin_router.py`'s list endpoint.

## Verification

- Schema defaults: `AppManifestSchema(appId='test', ...)` → `category == ''`, `features == []`, `readme == ''` ✓
- Extended fields: `AppManifestSchema(..., category='sync', features=['Auto-sync', 'OAuth'])` → parses correctly ✓
- Backward compat: `parse_app_manifest('../apps/rss-reader/manifest.yaml')` → `features == []`, no error ✓
- `grep '<details>'` in detail.html → found ✓
- `grep 'Operations'` in detail.html → found ✓
- `grep 'category'` in admin_router.py → found ✓

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `python -c "...AppManifestSchema(appId='test',...); assert m.category == ''"` | 0 | ✅ pass | 4s |
| 2 | `python -c "...AppManifestSchema(..., category='sync', features=[...]); assert m.category == 'sync'"` | 0 | ✅ pass | 4s |
| 3 | `python -c "...parse_app_manifest('../apps/rss-reader/manifest.yaml'); assert m.features == []"` | 0 | ✅ pass | 5s |
| 4 | `grep -q '<details>' backend/app/templates/admin/apps/detail.html` | 0 | ✅ pass | <1s |
| 5 | `grep -q 'Operations' backend/app/templates/admin/apps/detail.html` | 0 | ✅ pass | <1s |
| 6 | `grep -q 'category' backend/app/apps/admin_router.py` | 0 | ✅ pass | <1s |

### Slice-level checks (T01 scope):

| # | Check | Verdict |
|---|-------|---------|
| 1 | Schema defaults work | ✅ pass |
| 2 | Extended fields parse | ✅ pass |
| 3 | `openCatalogTab` in workspace.js | ⏳ T02 |
| 4 | Catalog routes in apps.py | ⏳ T02 |
| 5 | catalog_list.html exists | ⏳ T02 |
| 6 | catalog_detail.html exists | ⏳ T02 |
| 7 | Operations in admin detail | ✅ pass |
| 8 | Browse Catalog in explorer | ⏳ T02 |

## Diagnostics

- Inspect extended fields on any manifest: `.venv/bin/python -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('<path>'); print(m.category, m.features, m.readme)"`
- Category pill visibility: only renders when `manifest.category` is truthy (non-empty string)
- Features section: only renders when `manifest.features` is non-empty list
- Operations collapse: `<details>` element is initially closed; click to expand

## Deviations

- Task plan verification commands used `appId='t'` which violates the existing 2-char minimum constraint on `appId`. Used `appId='test'` instead — this is a plan typo, not a code issue.
- Added a Dependencies section showing model dependencies (from `manifest.dependencies.models`) between Features and Operations — the plan mentioned it and it naturally fits the catalog-first layout.

## Known Issues

None.

## Files Created/Modified

- `backend/app/apps/manifest.py` — Added `category`, `features`, `readme` fields to `AppManifestSchema`
- `backend/app/templates/admin/apps/detail.html` — Redesigned: catalog showcase at top, ops in collapsible `<details>`
- `backend/app/templates/admin/apps/list.html` — Added category badge pill on app cards
- `backend/app/apps/admin_router.py` — Added `category` to the app dict in list builder
- `.gsd/milestones/M033/slices/S06/S06-PLAN.md` — Added Observability section
- `.gsd/milestones/M033/slices/S06/tasks/T01-PLAN.md` — Added Observability Impact section
