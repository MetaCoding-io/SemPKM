---
estimated_steps: 4
estimated_files: 3
skills_used: []
---

# T01: Extend schema and redesign admin catalog pages

**Slice:** S06 — App Catalog Pages
**Milestone:** M033

## Description

Add optional catalog metadata fields (`category`, `features`, `readme`) to `AppManifestSchema` and redesign the admin app detail page from ops-monitoring-first to catalog-showcase-first. The detail page should lead with description, a features checklist, and a permissions summary. Operational data (PID, uptime, logs, task history, renderer overrides) should be pushed into a collapsible `<details>` "Operations" section. The admin list page should show category badges on app cards when the field is populated. All changes must be backward-compatible — the 11 existing app manifests have none of these new fields.

## Steps

1. **Add optional fields to `AppManifestSchema`** in `backend/app/apps/manifest.py`:
   - `category: str = Field(default="", max_length=64)` — app category (e.g., "sync", "reader", "calendar")
   - `features: list[str] = Field(default_factory=list)` — list of feature descriptions
   - `readme: str = Field(default="", max_length=10000)` — markdown readme content
   - Place them in the "Identity" group, after `license`

2. **Redesign `backend/app/templates/admin/apps/detail.html`** — restructure the page layout:
   - Keep the existing header (back link, title row with name, version pill, status badge)
   - Keep the description paragraph right after header
   - Add a **Features** section: render `manifest.features` as a checklist with checkmark icons. Only show this section when `manifest.features` is non-empty.
   - Move the existing **Permissions** section up to be immediately after features (it's already present — just reorder)
   - Add a **Dependencies** section showing model dependencies from `manifest.dependencies.models` if any exist
   - Wrap ALL operational sections (Status stats-bar, Logs, Actions, Task History, Renderer Overrides) inside a single `<details>` element with `<summary><h2>Operations</h2></summary>`. This keeps the ops info accessible for admins but de-emphasizes it in favor of the catalog showcase.
   - Keep the "Data Statistics" placeholder — it can go inside the Operations details block too

3. **Update `backend/app/templates/admin/apps/list.html`** — add category badge:
   - In each app card, after the version pill and status badge row, show a category pill if `app.category` is non-empty
   - Use the existing `.version-pill` styling pattern but with a distinct background color (e.g., `var(--color-primary)` with low opacity)
   - The `admin_apps_list` route in `admin_router.py` already passes `manifest.description` — also pass `category` from the manifest to the template context. Add `"category": manifest.category if manifest else ""` to the app dict in the list builder loop.

4. **Verify** backward compatibility by parsing an existing manifest and confirming defaults:
   - `cd backend && python -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('../apps/rss-reader/manifest.yaml'); print(m.name, m.category, m.features)"`

## Must-Haves

- [ ] `AppManifestSchema` has `category`, `features`, `readme` fields with safe defaults
- [ ] Existing app manifests (no new fields) still parse without error
- [ ] Admin detail page shows features and permissions prominently at top
- [ ] Operational sections (status, logs, actions, tasks, renderers) are inside a collapsible `<details>` block
- [ ] Admin list page shows category badge when populated

## Verification

- `cd backend && python -c "from app.apps.manifest import AppManifestSchema; m = AppManifestSchema(appId='t', version='1.0.0', name='T', backend={'entrypoint': 'x:Y'}); assert m.category == ''; assert m.features == []; assert m.readme == ''"`
- `cd backend && python -c "from app.apps.manifest import AppManifestSchema; m = AppManifestSchema(appId='t', version='1.0.0', name='T', backend={'entrypoint': 'x:Y'}, category='sync', features=['Auto-sync', 'OAuth'], readme='# Hi'); assert m.category == 'sync'; assert len(m.features) == 2"`
- `cd backend && python -c "from app.apps.manifest import parse_app_manifest; m = parse_app_manifest('../apps/rss-reader/manifest.yaml'); assert m.features == []"` — existing manifests still parse
- `grep -q '<details>' backend/app/templates/admin/apps/detail.html` — ops section is collapsible
- `grep -q 'Operations' backend/app/templates/admin/apps/detail.html` — ops summary label exists
- `grep -q 'category' backend/app/apps/admin_router.py` — category passed to list template

## Inputs

- `backend/app/apps/manifest.py` — existing `AppManifestSchema` to extend
- `backend/app/templates/admin/apps/detail.html` — existing admin detail template to redesign
- `backend/app/templates/admin/apps/list.html` — existing admin list template to enhance
- `backend/app/apps/admin_router.py` — existing admin router (may need minor context addition)
- `apps/rss-reader/manifest.yaml` — example existing manifest for backward-compat testing

## Expected Output

- `backend/app/apps/manifest.py` — schema extended with `category`, `features`, `readme`
- `backend/app/templates/admin/apps/detail.html` — redesigned with catalog-first layout
- `backend/app/templates/admin/apps/list.html` — category badges added
- `backend/app/apps/admin_router.py` — category field added to list context
