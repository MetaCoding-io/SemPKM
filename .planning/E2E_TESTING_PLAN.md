# SemPKM E2E Testing Plan — Playwright

## Overview

Build a comprehensive Playwright-based end-to-end test suite that validates SemPKM's
entire platform — from first-run setup through object CRUD, views, validation, admin
features, and multi-user flows. Tests run against isolated Docker Compose stacks with
fresh data volumes and deterministic seed data.

---

## Phase 0 — Test Infrastructure & Harness

**Goal:** Set up Playwright, Docker test harness, and authentication helpers so every
subsequent phase can focus on writing tests rather than fighting infrastructure.

### 0.1 Install Playwright & Dependencies

Create `e2e/` at the project root:

```
e2e/
├── package.json              # playwright, @playwright/test
├── playwright.config.ts      # base config
├── tsconfig.json             # TypeScript config
├── docker-compose.test.yml   # Isolated test stack
├── fixtures/
│   ├── auth.ts               # Authenticated page fixtures
│   ├── seed-data.ts          # Seed data constants (IRIs, titles)
│   └── test-harness.ts       # Docker lifecycle (setup/teardown)
├── helpers/
│   ├── api-client.ts         # Typed helpers for /api/* calls
│   ├── selectors.ts          # Shared CSS/data-testid selectors
│   └── wait-for.ts           # Custom waitFor helpers (htmx swaps, etc.)
├── tests/
│   ├── 00-setup/             # Phase 1: Setup wizard & auth
│   ├── 01-objects/           # Phase 2: Object CRUD
│   ├── 02-views/             # Phase 3: Table, cards, graph views
│   ├── 03-navigation/        # Phase 4: Workspace, tabs, command palette
│   ├── 04-validation/        # Phase 5: SHACL validation & lint panel
│   ├── 05-admin/             # Phase 6: Models & webhooks admin
│   ├── 06-settings/          # Phase 7: Settings & dark mode
│   └── 07-multi-user/        # Phase 8: RBAC & multi-user flows
└── scripts/
    ├── start-test-env.sh     # Launch test Docker stack
    ├── stop-test-env.sh      # Tear down + remove volumes
    └── wait-for-healthy.sh   # Poll health endpoint
```

### 0.2 Docker Test Harness (`docker-compose.test.yml`)

A parallel Docker Compose file that:

1. **Uses separate named volumes** (`rdf4j_test_data`, `sempkm_test_data`) so
   production data is never touched
2. **Maps to different host ports** (e.g. API on 8901, frontend on 3901) to avoid
   conflicts with a running dev instance
3. **Sets deterministic env vars**: fixed `SECRET_KEY` so token signing is
   reproducible, `SESSION_DURATION_DAYS=1` for quick expiry tests
4. **Builds from the same Dockerfiles** as production (no special test images)

```yaml
# docker-compose.test.yml (sketch)
services:
  triplestore:
    image: eclipse/rdf4j-workbench:5.0.1
    volumes:
      - rdf4j_test_data:/var/rdf4j
    networks: [sempkm-test]

  api:
    build: ./backend
    ports: ["8901:8000"]
    volumes:
      - ./backend/app:/app/app
      - ./config:/app/config:ro
      - ./models:/app/models:ro
      - sempkm_test_data:/app/data
    environment:
      TRIPLESTORE_URL: http://triplestore:8080/rdf4j-server
      REPOSITORY_ID: sempkm_test
      BASE_NAMESPACE: https://test.example.org/data/
      DATABASE_URL: sqlite+aiosqlite:///./data/sempkm_test.db
      SECRET_KEY: test-secret-key-for-e2e-only
      SESSION_DURATION_DAYS: 1
    depends_on:
      triplestore: { condition: service_healthy }
    networks: [sempkm-test]

  frontend:
    image: nginx:stable-alpine
    ports: ["3901:80"]
    volumes:
      - ./frontend/static:/usr/share/nginx/html:ro
      - ./frontend/nginx.conf:/etc/nginx/conf.d/default.conf:ro
    depends_on:
      api: { condition: service_healthy }
    networks: [sempkm-test]

volumes:
  rdf4j_test_data:
  sempkm_test_data:

networks:
  sempkm-test:
```

### 0.3 Test Lifecycle Scripts

- **`start-test-env.sh`**: `docker compose -f docker-compose.test.yml down -v &&
  docker compose -f docker-compose.test.yml up -d --build`
  (always starts fresh volumes)
- **`wait-for-healthy.sh`**: Polls `http://localhost:3901/api/health` with retries
  until 200 or timeout (60s). Exits non-zero on timeout.
- **`stop-test-env.sh`**: `docker compose -f docker-compose.test.yml down -v`

### 0.4 Playwright Config (`playwright.config.ts`)

```ts
export default defineConfig({
  testDir: './tests',
  fullyParallel: false,          // Sequential by default (stateful app)
  retries: 1,
  workers: 1,                    // Single worker — shared Docker state
  use: {
    baseURL: 'http://localhost:3901',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  globalSetup: './fixtures/test-harness.ts',
  projects: [
    { name: 'chromium', use: { ...devices['Desktop Chrome'] } },
  ],
});
```

### 0.5 Auth Fixture (`fixtures/auth.ts`)

Because the app uses passwordless magic-link auth with no SMTP configured (tokens
returned directly in API responses), the auth fixture can:

1. **First test run (setup):** POST `/api/auth/setup` with a known setup token
   extracted from the API container logs, then store the session cookie.
2. **Subsequent tests:** POST `/api/auth/magic-link` → capture token from response
   → POST `/api/auth/verify` → extract `sempkm_session` cookie → inject into
   browser context via `storageState`.

Provide two fixtures:
- `ownerPage` — authenticated as the instance owner
- `memberPage` — authenticated as an invited member

### 0.6 API Client Helper (`helpers/api-client.ts`)

Thin wrapper around `request.newContext()` for direct API calls:
- `apiClient.setup(token, email)` → POST `/api/auth/setup`
- `apiClient.createObject(type, props)` → POST `/api/commands`
- `apiClient.createEdge(source, target, predicate)` → POST `/api/commands`
- `apiClient.getHealth()` → GET `/api/health`
- `apiClient.sparql(query)` → POST `/api/sparql`

Used for **arranging test data** without going through the UI (faster, more reliable
for preconditions).

### 0.7 Data-testid Annotations (Backend Changes)

Add `data-testid` attributes to key Jinja2 templates for stable selectors:
- Navigation tree items, tab bar, editor area, property panel
- Type picker overlay, form fields, save button
- Table rows, card items, graph container
- Lint panel, validation badges
- Settings page sections, dark mode toggle
- Admin model list, webhook list

This is a small, incremental change — add testids as each phase of tests requires
them, not all at once.

---

## Phase 1 — Setup Wizard & Authentication

**Goal:** Verify the first-run experience and auth flows work end-to-end.

### Tests

| Test | Description |
|------|-------------|
| `setup-wizard.spec.ts` | Fresh instance redirects to `/setup.html` |
| | Enter setup token → instance claimed → redirected to workspace |
| | Setup token extracted from API container logs programmatically |
| | After setup, `/api/auth/status` returns `setup_complete: true` |
| `magic-link-login.spec.ts` | Request magic link → token in response (no SMTP) |
| | Verify token → session cookie set → `/api/auth/me` works |
| | Invalid token → rejected with 400 |
| | After logout → cookie cleared → workspace redirects to login |
| `setup-already-done.spec.ts` | Second setup attempt returns 400 "Setup already completed" |

### Preconditions
- Fresh Docker stack (clean volumes)
- Setup token read from `docker compose logs api`

### Key Assertions
- Session cookie `sempkm_session` is set/cleared correctly
- Redirect flow: unauthenticated → `/login.html` → verify → workspace
- Owner role assigned correctly after setup

---

## Phase 2 — Object CRUD

**Goal:** Verify creating, reading, editing, and deleting all four Basic PKM types.

### Tests

| Test | Description |
|------|-------------|
| `create-note.spec.ts` | Open type picker → select Note → fill title + body → save |
| | New note appears in nav tree |
| | Note body rendered with markdown |
| `create-concept.spec.ts` | Create Concept with prefLabel, definition |
| `create-project.spec.ts` | Create Project with title, status, priority, dates |
| `create-person.spec.ts` | Create Person with name, email, jobTitle |
| `edit-object.spec.ts` | Open existing object → edit mode → change title → save |
| | Verify updated title reflected in nav tree and object page |
| `edit-body.spec.ts` | Open note → edit markdown body → Ctrl+S → verify saved |
| `delete-object.spec.ts` | Delete object with no references → confirm deleted |
| | Try deleting object with references → verify rejection |
| `create-edge.spec.ts` | Create relationship between two objects |
| | Verify edge appears in related objects panel |
| `batch-commands.spec.ts` | Create multiple objects via API batch → verify all exist |

### Preconditions
- Authenticated as owner (use auth fixture)
- Seed data from Basic PKM model already loaded (auto-installed on first run)

### Key Assertions
- Objects appear in nav tree after creation
- SHACL form fields match the shape constraints for each type
- Event store records events (check via `/api/sparql`)
- Labels resolve correctly (IRI → human-readable title)

---

## Phase 3 — Views (Table, Cards, Graph)

**Goal:** Verify all three view renderers work with seed data and newly created objects.

### Tests

| Test | Description |
|------|-------------|
| `table-view.spec.ts` | Open "All Notes" table view → verify columns and row count |
| | Sort by title → verify order changes |
| | Filter text → verify rows filtered |
| | Click row → object tab opens |
| | Column visibility toggle → column hidden/shown |
| `cards-view.spec.ts` | Open "All Projects" cards view → verify cards rendered |
| | Click card → navigates to object |
| `graph-view.spec.ts` | Open graph view → Cytoscape canvas rendered |
| | Verify nodes present (check node count matches seed data) |
| | Double-click node → object tab opens |
| `view-with-new-data.spec.ts` | Create object via API → open table view → new row appears |

### Preconditions
- Authenticated as owner
- Seed data present (2 projects, 3 people, 3 notes, 3 concepts from Basic PKM)

### Key Assertions
- View specs execute SPARQL and render results
- Pagination works (if enough data)
- Cytoscape.js initializes without errors
- Table sorting is stable

---

## Phase 4 — Workspace & Navigation

**Goal:** Verify the IDE-style workspace: split panes, tabs, command palette, keyboard
shortcuts, sidebar.

### Tests

| Test | Description |
|------|-------------|
| `workspace-layout.spec.ts` | Workspace loads with sidebar, editor, properties panels |
| | Split.js panes are resizable (drag divider) |
| `tab-management.spec.ts` | Open multiple objects → tabs appear in tab bar |
| | Close tab → removed from bar |
| | Click tab → switches to that object |
| | Ctrl+W → closes active tab |
| `nav-tree.spec.ts` | Nav tree shows types as sections |
| | Expand section → objects listed |
| | Click object → opens in editor |
| | Sidebar collapse/expand toggle works |
| `command-palette.spec.ts` | Ctrl+K → command palette opens |
| | Type search query → results filter |
| | Select result → navigates to object |
| `keyboard-shortcuts.spec.ts` | Ctrl+N → type picker opens |
| | Ctrl+S → saves current object |
| | Ctrl+, → settings page opens |

### Key Assertions
- Split.js panes have correct initial proportions
- Tab state persists across navigation
- Command palette search matches by title

---

## Phase 5 — SHACL Validation & Lint Panel

**Goal:** Verify that SHACL validation runs asynchronously and results appear in the
lint panel.

### Tests

| Test | Description |
|------|-------------|
| `validation-runs.spec.ts` | Create object → validation enqueued → report generated |
| | Check `/api/validation/latest` returns report |
| `lint-panel.spec.ts` | Create object missing required field → lint panel shows violation |
| | Fix the field → re-validate → violation cleared |
| `validation-non-blocking.spec.ts` | Object saves even with validation errors |
| | Violations are displayed but don't prevent edits |

### Preconditions
- SHACL shapes loaded from Basic PKM model
- Need to wait for async validation queue to process

### Key Assertions
- Validation is eventual (async queue), not synchronous
- Violations display correct field name and severity
- Validation report accessible via API

---

## Phase 6 — Admin Features

**Goal:** Verify model management and webhook configuration (owner-only features).

### Tests

| Test | Description |
|------|-------------|
| `admin-models.spec.ts` | Navigate to `/admin/models` → Basic PKM listed |
| | Model card shows name, version, description |
| `admin-webhooks.spec.ts` | Create webhook → appears in list |
| | Edit webhook URL → saved |
| | Delete webhook → removed from list |
| `admin-access-control.spec.ts` | Member user cannot access admin pages (403) |

### Preconditions
- Owner and member users both set up (via auth fixture)

### Key Assertions
- Admin pages require owner role
- Webhook CRUD persists across page reloads
- Model list reflects installed models

---

## Phase 7 — Settings & Dark Mode

**Goal:** Verify the settings system and theme switching.

### Tests

| Test | Description |
|------|-------------|
| `settings-page.spec.ts` | Open settings (Ctrl+,) → categories displayed |
| | Change a setting → saved → persists on reload |
| `dark-mode.spec.ts` | Toggle dark mode → CSS variables change |
| | Theme persists across page reload |
| | Toggle back to light → reverts |
| `per-user-settings.spec.ts` | Owner sets dark mode → member still sees light mode |

### Key Assertions
- Settings stored in SQL user_settings table
- CSS custom properties change on theme toggle
- Per-user isolation works

---

## Phase 8 — Multi-User & RBAC

**Goal:** Verify role-based access control across owner, member, and guest roles.

### Tests

| Test | Description |
|------|-------------|
| `invite-member.spec.ts` | Owner invites member → invitation created |
| | Member accepts invitation → can log in |
| `member-permissions.spec.ts` | Member can create/edit objects |
| | Member cannot access admin pages |
| `guest-permissions.spec.ts` | Guest can view objects (read-only) |
| | Guest cannot create or edit objects |
| `session-expiry.spec.ts` | Expired session → redirected to login |

### Preconditions
- Owner account exists
- Invitation flow tested end-to-end

### Key Assertions
- RBAC enforced both client-side and server-side
- Cookie expiry matches `SESSION_DURATION_DAYS`
- Invitation tokens work correctly

---

## Implementation Strategy: Incremental Phases

### Recommended Build Order

1. **Phase 0** first (infrastructure) — this unblocks everything
2. **Phase 1** next (auth) — every subsequent test needs auth fixtures
3. **Phase 2** (CRUD) — core functionality, most value per test
4. **Phase 3** (views) — validates the primary UI
5. **Phase 4** (workspace) — validates the IDE experience
6. Phases 5–8 in any order after that

### Test Data Strategy

Each test run starts with **completely fresh volumes** (docker-compose down -v + up).
The Basic PKM starter model auto-installs on first run, providing:
- 2 Projects, 3 People, 3 Notes, 3 Concepts (seed data)
- SHACL shapes for all four types
- View specs for table, cards, and graph views

For tests that need **additional data beyond seed**, use the API client helper to
create objects via `POST /api/commands` before the UI assertions. This is faster
and more reliable than driving the full UI for test setup.

### htmx-Specific Testing Considerations

Since SemPKM uses htmx (not a SPA), Playwright tests need to account for:

1. **Partial page swaps**: htmx replaces DOM fragments, not full pages. Use
   `page.waitForSelector()` targeting the swapped element, not `page.waitForNavigation()`.
2. **No URL changes for partials**: Many interactions swap content without changing
   the URL. Assert on DOM content, not URL.
3. **HX-Request header**: htmx adds `HX-Request: true` header. The API client
   helper should NOT set this (to get full-page responses for arrangement).
4. **Form submission**: htmx forms use `hx-post`/`hx-put` instead of native form
   submission. Use `page.click()` on submit buttons rather than `page.fill()` + Enter.
5. **Loading indicators**: htmx adds `.htmx-request` class during swaps. Can be
   used as a "loading" signal to wait for.

### CI Integration (Future)

Once the test suite stabilizes:
- GitHub Actions workflow running on every PR
- Build test images → start stack → run Playwright → collect artifacts
- Failure screenshots and traces uploaded as artifacts
- Test results reported in PR comments

---

## What Gets Committed in Phase 0

The initial implementation commit (Phase 0) will include:

1. `e2e/package.json` + `e2e/tsconfig.json` + `e2e/playwright.config.ts`
2. `docker-compose.test.yml`
3. `e2e/scripts/` (start, stop, wait-for-healthy)
4. `e2e/fixtures/` (auth, test-harness, seed-data constants)
5. `e2e/helpers/` (api-client, selectors, wait-for)
6. `e2e/tests/00-setup/setup-wizard.spec.ts` — first working test as proof of concept
7. A few `data-testid` annotations in key templates

This gives us a working foundation that we can build on incrementally — one test
file at a time, across multiple sessions.
