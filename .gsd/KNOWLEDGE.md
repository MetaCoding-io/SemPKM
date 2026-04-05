# Project Knowledge

Append-only register of project-specific rules, patterns, and lessons learned.
Agents read this before every unit. Add entries when you discover something worth remembering.

## Rules

| # | Scope | Rule | Why | Added |
|---|-------|------|-----|-------|
| R01 | git / GSD | **Never use worktree isolation mode.** Use `taskIsolation.mode: branch` or `none` in `.gsd/preferences.md`. | Worktree mode caused catastrophic data loss 3+ times: code was built in `.gsd/worktrees/<MID>/`, only `.gsd/` artifacts were committed to main, the worktree was cleaned up, and source code was permanently lost. M009-M010 lost the entire App Platform + RSS Reader. M019-M022 lost 4 sync apps. M027-M028 lost Notion Import + AI Features. ~115 files across 8 milestones were only recoverable from dangling git objects. | 2026-03-21 |
| R02 | git / GSD | **After every milestone or slice completion, verify source files exist on the integration branch.** Run: `git diff --stat HEAD~1` and confirm non-`.gsd/` files are present. If a commit only touches `.gsd/` files, the code was not merged. | The auto-commit mechanism commits `.gsd/` planning artifacts but does NOT commit source code from worktrees. This silent failure looks like a successful completion. | 2026-03-21 |
| R03 | git | **Never run `git gc` or `git prune` without first auditing dangling commits.** Run `git fsck --lost-found` and check for source files before allowing garbage collection. | Dangling commits are the last line of defense for unmerged worktree code. Once garbage-collected, the code is permanently gone. | 2026-03-21 |
| R04 | GSD / roadmap | **Roadmap `## Slices` section must use checkbox format, not heading format.** Correct: `- [ ] **S01: Title** \`risk:level\` \`depends:[]\``. Wrong: `### S01: Title` with bullet metadata. The auto-mode dispatcher parses checkbox lines to find eligible slices — heading-style slices are invisible to it, causing "No slice eligible" even when slices exist. | Blocked auto-mode dispatch for 5+ consecutive attempts on M033. The planner generated `### S01:` headings instead of `- [ ] **S01:**` checkboxes. | 2026-03-21 |
| R05 | git / GSD | **After every auto-mode commit, verify no source files were deleted.** Run: `git diff-tree --no-commit-id -r --diff-filter=D HEAD` and confirm zero non-`.gsd/` deletions. If the commit deleted source files, recover immediately from the parent commit. | Auto-mode commit 99e585b1 ("M030 E2E test suite") silently deleted 26 source files from 6 prior milestones (M010, M018-M022, M027, M028) including the entire rss-feeds model, 7 mock API servers, 8 E2E specs, the Notion import executor, and the AI router. The agent's `git add -A` captured a working tree state that was missing files from earlier recovery commits. The deletion was invisible — the commit message described only what was *added*, not what was removed. | 2026-03-21 |
| R06 | git / GSD | **Never use `git add -A` or `git add .` in auto-mode commits.** Use `git add <specific-files>` listing only the files the current task created or modified. | `git add -A` stages the entire working tree, including deletions of files the agent never touched. If the working tree is missing files (e.g., from a prior session's recovery that wasn't in the current checkout), they get silently deleted from the repository. This is how 99e585b1 destroyed 26 files — the agent added its 7 new test files but `git add -A` also staged the removal of 26 unrelated files. | 2026-03-21 |
| R07 | GSD / parallel | **Never use parallel auto-mode (`parallel.enabled: true`) with `git.isolation: "none"`.** Workers share the same `.gsd/` directory and can write artifacts for milestones they don't own. `GSD_MILESTONE_LOCK` only filters what `deriveState()` sees — it does NOT prevent file writes. A parallel worker can fabricate SUMMARY, VALIDATION, and slice/task summaries for another milestone, marking it "complete" when no real code was built. | The M033 worker created M032's entire completion artifact tree (SUMMARY, VALIDATION, S01-S03 summaries, T01-T03 summaries) in commit dc723e25, skipping M032 entirely. M032 had to be manually reopened. | 2026-03-22 |
| R08 | git / secrets | **Never commit `.env` files with real API keys.** `.env` must be in `.gitignore` AND verified untracked (`git ls-files .env` must return empty). Use `secure_env_collect` to manage secrets. If a `.env` with secrets is accidentally committed, it must be scrubbed from history with `git-filter-repo --invert-paths --path .env --force` followed by force-push and immediate key rotation at all affected providers. GitHub caches old blobs for up to 90 days after force-push — key rotation is mandatory regardless of history scrub. | `.env` with 8 live API keys (OpenAI, Anthropic, GitHub, Linear, YouTube, Spotify, Firebase) was tracked and pushed to a public GitHub repo across 8 commits. Despite being in `.gitignore`, it was tracked because it was added before the ignore rule or force-added. The `.gitignore` entry gave a false sense of security. Scrubbed via `git-filter-repo` rewriting all 2,504 commits, followed by force-push. | 2026-03-25 |
| R09 | Docker / E2E | **Never run `docker compose down -v` on any stack without explicit user confirmation.** Use `docker compose restart <service>` or `docker compose up -d --force-recreate <service>` to fix individual container issues. The `-v` flag destroys named volumes (database, triplestore data) which cannot be recovered. Even on the test stack, volume loss causes 40+ E2E test failures from missing initialized state (installed models, seed data, auth sessions). If a container won't start, diagnose the root cause (permissions, config, image) and fix it without touching volumes. | M046/S07/T03: nginx frontend container crashed due to `setgid(101) failed` from `security_opt: no-new-privileges`. The agent ran `docker compose -f docker-compose.test.yml down -v` to "start fresh", destroying test DB and triplestore volumes. The actual fix was removing `security_opt` from the frontend service — no volume wipe was needed. 42 E2E tests broke from the state loss. | 2026-03-30 |

## Patterns

| # | Pattern | Where | Notes |
|---|---------|-------|-------|
| 1 | SPARQL date comparison in rdflib: use `STRDT(SUBSTR(STR(NOW()), 1, 10), xsd:date)` instead of `xsd:date(NOW())` | `models/basic-pkm/rules/basic-pkm.ttl` | rdflib does not support `xsd:date()` cast — produces empty results. The STRDT+SUBSTR approach constructs a proper typed xsd:date literal that compares correctly with xsd:date values in FILTER. |
| 2 | MockResponse default data: use `data if data is not None else {}` not `data or {}` | `backend/tests/test_github_sync_engine.py` | Python `[] or {}` evaluates to `{}` because empty list is falsy. A mock returning `MockResponse(200, [])` silently becomes `{}` which gets iterated as a dict, producing cryptic KeyError failures. |
| 3 | Never embed N-Triples in SPARQL INSERT DATA for RDF4J — use `insert_graph()` with Graph Store protocol instead | `backend/app/services/validation.py`, `backend/app/triplestore/client.py` | rdflib N-Triples blank node IDs (e.g. `_:n333f21aad...`) cause RDF4J SPARQL parser to error with "Not a valid (absolute) IRI". The Graph Store protocol (POST with `Content-Type: text/turtle` to `/statements?context=<graph>`) bypasses SPARQL parsing entirely. |
| 4 | `_rdf_term_to_sparql` must handle `BNode` explicitly — rdflib `str(BNode())` returns the raw ID without `_:` prefix | `backend/app/services/validation.py` | BNode identifiers like `nf943a8d5...` look like relative IRIs when wrapped in `<...>`. Always check `isinstance(term, BNode)` and format as `_:{id}`. |
| 5 | Adding a new quadrant framework requires 6 coordinated edits | `backend/app/views/service.py`, `models/business-planning/` | (1) Add entry to `_QUADRANT_LABELS` dict keyed by framework id with 4 label tuples, (2) add keyword pair to `_AXIS_KEYWORD_PAIRS` for axis detection, (3) ontology classes (container + item), (4) SHACL shapes with exactly 2 `sh:in` properties of length 2, (5) ViewSpecs declaring `quadrant` renderer, (6) manifest icon entries. Missing any one causes silent failures (no labels, no axis detection, no view). |
| 6 | Adding a new custom renderer requires 4-layer wiring | `backend/app/views/{registry,router,service}.py`, templates, JS, CSS | (1) Add renderer name to `RENDERER_REGISTRY` dict in registry.py, (2) add to `_VALID_RENDERERS` set in router.py, (3) add elif branches in `generic_view()` and `generic_view_data()`, (4) add `_detect_*`, `_build_*_select`, `execute_*_query` methods to ViewSpecService, (5) create Jinja2 template + JS + CSS. Proven across 4 renderers (quadrant, bmc, okr, decision-matrix). The `register_renderer()` infrastructure exists but is dead code — activating it would eliminate steps 1-3. |
| 7 | Settings category partials backed by JSON API use JS fetch() + htmx.ajax() reload | `backend/app/templates/browser/_context_rules.html`, `backend/app/browser/settings.py` | JSON API endpoints return JSON, not HTML fragments. htmx `hx-post` alone can't handle the round-trip. Pattern: `fetch('/api/...', ...)` for mutation → on success → `htmx.ajax('GET', '/browser/settings/<category>', {target: '#<container>'})` to reload the panel. Future Settings categories backed by JSON APIs should follow this pattern. |
| 8 | In-memory SQLite tests with FK constraints must import all referenced models | `backend/tests/test_rules_engine.py`, `backend/tests/test_context_service.py` | When a model has `ForeignKey('users.id')`, the `users` table must be registered in `Base.metadata` before `create_all()`. In-memory SQLite tests must `import app.auth.models.User` (or equivalent) even if User isn't directly used in the test — otherwise FK creation fails. |
| 9 | Mock firebase_admin via sys.modules dict patching, not MagicMock | `backend/tests/test_notification_service.py` | `messaging.send()` raises `UnregisteredError` on stale tokens. If you mock `firebase_admin.messaging` with a plain MagicMock, the `except messaging.UnregisteredError` clause fails with `TypeError: catching classes that do not inherit from BaseException is not allowed`. Fix: create a real class `class UnregisteredError(Exception): pass`, attach it to a mock module, and patch via `sys.modules['firebase_admin.messaging']`. |
| 10 | Multi-service app: alias imports when service modules export identically-named functions | `apps/media-scheduler/app.py` | When app.py imports from both `podcast_service` and `youtube_service`, functions like `get_existing_item_iris` and `mint_item_iri` collide. Alias the later imports with a prefix (e.g., `yt_get_existing_item_iris`). Each service module should also redefine shared constants (`MS_NS`, `APP_NS`) locally rather than cross-importing — keeps modules decoupled with zero risk of circular imports. Applies to any future service (Spotify, etc.) added to the same app. |

| 11 | SSE client pattern for App SDK apps subscribing to platform event streams | `apps/media-scheduler/services/context_service.py` | Use `ctx._get_platform_client()` → `client.stream("GET", url)` → `aiter_lines()` → custom `parse_sse_lines()` for SSE wire format. Spawn via `asyncio.create_task` in `on_startup`, cancel in `on_shutdown`. Add exponential-backoff reconnect (`min(2^count, 300)` seconds). Use `asyncio.Lock` around any expensive callback to prevent concurrent execution. Store listener task + debounce task as module-level variables for lifecycle management. |
| 12 | All SPARQL IRI interpolation uses `safe_iri()` from `app.sparql.builder`; all string escaping uses `sparql_escape_string()` | `backend/app/sparql/builder.py` | After M043/S01, there are zero local escape functions. All IRI interpolation in SPARQL queries goes through `safe_iri()` (rdflib URIRef.n3() with pre-validation). All string escaping goes through `sparql_escape_string()`. New modules that build SPARQL queries must import from `app.sparql.builder` — never write a local escape function. The builder also provides `values_clause()` for VALUES blocks and `triple_pattern()` for safe triple construction. |
| 13 | All frontend fetch() calls use `apiFetch(url, opts)` from `api-fetch.js`; new fetch calls must use `apiFetch()` | `frontend/static/js/api-fetch.js` | After M044/S01, zero bare fetch() calls remain in JS or HTML templates (verified by grep). `apiFetch()` returns raw Response on success, throws structured error ({status, body, response}) on non-2xx, silently catches AbortError (returns undefined), supports `{silent:true}` to suppress toasts. All existing callers use `{silent:true}` because each file has its own error UX. One intentional raw-fetch exemption: `auth.js` `/api/auth/me` (needs `?next=` on 401 redirect, annotated `// raw-fetch`). Verification: `rg '\bfetch\(' frontend/static/js/ -g '*.js' | grep -v apiFetch | grep -v '// raw-fetch' | grep -v vendor.js` must return zero results. |
| 14 | CSS decorative colors use `color-mix(in srgb, var(--_color-X) PCT%, transparent)` with theme primitives — never standalone `rgba()` | `frontend/static/css/theme.css`, all consumer CSS files | After M044/S04, zero standalone hex or rgba values remain outside theme.css. All decorative tints (BMC sections, quadrant colors, OKR status, decision-matrix ratings) use `color-mix(in srgb, var(--_color-*) N%, transparent)` referencing primitive tokens defined in theme.css. The primitives have dark-mode overrides in the `[data-theme="dark"]` block, so color-mix consumers auto-adapt. New decorative colors must: (1) add a `--_color-*` primitive to both light and dark blocks in theme.css, (2) reference via `color-mix()` in consumer CSS. Breakpoints standardized to 600px (mobile) and 768px (tablet). Verification: `rg '#[0-9a-fA-F]{3,8}\b' frontend/static/css/ --glob '!theme.css' | grep -v var( | wc -l` must return 0. |
| 15 | Never use Jinja2 `.append()` or `namespace()` for computation in templates — pre-compute in the Python view function | All `backend/app/templates/` and backing view routers | After M044/S05, zero `.append()` and zero `namespace()` hacks remain in templates. All list-building, grouping, counting, and boolean flags are computed in the Python view function and passed as template context variables. The `_partition_form_properties()` helper in `objects.py` handles form field classification for all 5 callsites. Importer routers use `_IMPORTER_CTX` module-level dicts spread via `**kwargs`. Verification: `rg '\.append\(' backend/app/templates/ -g '*.html' | wc -l` must return 0; `rg 'namespace\(' backend/app/templates/ -g '*.html' | grep -v base_namespace | grep -v info.namespace | wc -l` must return 0. |
| 16 | Shared importer partials at `backend/app/templates/importer/partials/` — new importers must use these | `backend/app/templates/importer/partials/{step_bar,upload_form,scan_trigger,import_progress,import_summary}.html` | After M044/S05, Notion and Obsidian importers share 5 parametrized partials. Each shared template uses context variables (`url_prefix`, `importer_name`, `steps`, `file_input_id`, etc.) passed from the importer-specific router. Structurally different templates (scan_results, preview, type_mapping, property_mapping) stay importer-specific. When adding a new importer, define a `_IMPORTER_CTX` dict in the router and include the shared partials — don't duplicate the 5 base templates. |
| 17 | All outbound HTTP calls must use `validate_outbound_url()` from `backend/app/security/ssrf.py` before making the request | `backend/app/federation/service.py`, `backend/app/services/webhooks.py` | After M045/S01, all 4 outbound HTTP code paths (federation sync, inbox post, inbox discovery, webhook dispatch) use the SSRF guard. New code that makes outbound HTTP requests to user-supplied URLs must call `validate_outbound_url(url)` first — it resolves DNS and rejects loopback/link-local/multicast/private/reserved IPs. Known limitation: DNS rebinding can bypass validation (resolve safe IP then private IP on actual connection). |
| 18 | ZIP file uploads must use `validate_zip_contents()` from `backend/app/security/zip_validator.py` before extraction | `backend/app/obsidian/router.py`, `backend/app/notion/router.py` | After M045/S02, both Obsidian and Notion importers validate ZIP central directory via `infolist()` before calling `extractall()`. Checks uncompressed size (2048 MB), file count (50,000), and per-entry compression ratio (100:1). New endpoints that accept ZIP uploads must call `validate_zip_contents(zip_file)` and catch `ValueError` for user-facing error messages. |
| 19 | Adding TBox surfaces (dashboards/workflows) to a Mental Model requires manifest v2 format + JSON definitions + source_model lifecycle | `models/ppv/manifest.yaml`, `models/ppv/dashboards/ppv.json`, `models/ppv/workflows/ppv.json`, `backend/app/services/models.py` | After M047, any model can ship operational surfaces by: (1) adding `manifest_version: "2.0"` to manifest.yaml, (2) adding `dashboards:` and/or `workflows:` entrypoints pointing to JSON files, (3) JSON files use the format matching DashboardService.create() / WorkflowService.create() params. Workflow steps referencing dashboards use `dashboard_name` strings resolved to UUIDs at install time via `_resolve_dashboard_names()`. Model-sourced surfaces are tagged with `source_model` column — uninstall deletes only model-sourced rows, preserving user-created ones. TBox creation failure is warning-level, not install failure (degraded mode). |

## Lessons Learned

| # | What Happened | Root Cause | Fix | Scope |
|---|--------------|------------|-----|-------|
| K001 | SHACL-AF stale-contact rule with `?today - "P90D"^^xsd:dayTimeDuration` doesn't work in rdflib's SPARQL engine | rdflib does not implement xsd:dayTimeDuration subtraction from xsd:date | Use `NOT EXISTS` for zero-interaction check in SHACL rules; use SavedQuery with direct date comparison for time-windowed checks | models/crm/rules, any SHACL-AF SPARQL using date arithmetic |
| K002 | Seed data `dcterms:created` with `xsd:dateTime` caused spurious `sh:Violation` when SHACL shape constrains that property to `xsd:date` | SHACL `sh:datatype xsd:date` is strict — `xsd:dateTime` values fail the check even though both represent temporal data | Match the seed data's `@type` to whatever the SHACL shape's `sh:datatype` declares for that property. Check shapes before authoring seed data. | Any model's seed data where shapes constrain date fields |
| K003 | Worktree isolation mode lost source code for 8 milestones (~115 files). Code was built in worktrees, only `.gsd/` artifacts committed to main, worktrees cleaned up. Files survived only as dangling git objects. | GSD auto-mode commits `.gsd/` state files to main but source code lives in the worktree on a `milestone/<MID>` branch. When the worktree is removed and the branch deleted, source code becomes unreachable (dangling). | (1) Set `taskIsolation.mode: none` in preferences. (2) Recovered all files from dangling commits via `git fsck --lost-found` + `git checkout <hash> -- <path>`. (3) Added Rules R01-R03 to prevent recurrence. | All milestones using worktree mode |
| K004 | Auto-mode dispatch stuck on "No slice eligible" for 5+ runs. All task code and summaries were correct but dispatch couldn't find any slice to execute. | The planner agent wrote the roadmap's `## Slices` section with `### S01: Title` markdown headings instead of the `- [ ] **S01: Title** \`risk:level\` \`depends:[]\`` checkbox format. The dispatcher regex only matches the checkbox format. | Rewrote the Slices section to use checkbox format. Added Rule R04 to KNOWLEDGE.md. The real fix is a validation step between planning output and dispatch — either the planner's system prompt enforces it harder, or a post-planning lint checks the roadmap format. | Any milestone roadmap planning |
| K005 | Auto-mode commit 99e585b1 silently deleted 26 source files from 6 prior milestones (M010, M018-M022, M027, M028). Deleted files included the rss-feeds Mental Model (4 files), 7 mock API servers, 8 E2E specs, the Notion import executor, AI router, and test fixtures. The deletion was only discovered weeks later during a planning audit. | The auto-mode agent used `git add -A` (or equivalent whole-tree staging) for its M030/S04 commit. The agent's working tree was missing files from earlier recovery sessions — likely because the agent's session started fresh and didn't have those files checked out. `git add -A` stages deletions for any tracked file absent from the working tree, so the commit silently removed 26 files the agent never intended to touch. | (1) Recovered all 26 files: 3 from commit a35c9e91 (M028 recovery), 6 from a35c9e91 (M027 recovery), 17 from ca981b55 (parent of destructive commit). (2) Added Rules R05-R06 to prevent recurrence. (3) Key insight: this is a *different* failure mode from K003 worktrees — these files were on main and were committed, then silently deleted by a later commit. The safeguard is never using `git add -A` in auto-mode. | All auto-mode commits; verification should check for unexpected deletions |
| K006 | Parallel auto-mode (M032+M033) caused M032 to be skipped. The M033 worker's "complete-milestone" unit committed fabricated M032 artifacts (SUMMARY, VALIDATION, all slice/task summaries) claiming M032 was done. Auto-mode then advanced to M033 tasks, researched M034, and only returned to M032 after manual intervention. | Workers with `git.isolation: "none"` share the `.gsd/` directory. `GSD_MILESTONE_LOCK` filters `deriveState()` visibility but doesn't restrict file writes. The completing-milestone prompt or the agent itself generated M032 planning artifacts and committed them alongside M033's own artifacts in a single `git add -A` commit (dc723e25). | (1) Disabled parallel mode (`parallel.enabled: false`). (2) Manually deleted fabricated M032 terminal artifacts (SUMMARY, VALIDATION, S02/S03 summaries). (3) Re-opened M032 S02+S03 in the roadmap. (4) Added Rule R07. Parallel mode needs filesystem-level write isolation per worker before it can be safely re-enabled. | Parallel mode with shared .gsd/ directory |
| K007 | `.env` with 8 live API keys (OpenAI, Anthropic, GitHub PAT, Linear, YouTube, Spotify client ID/secret, Firebase) was committed and pushed to a public GitHub repo across 8 commits over the project's lifetime. Despite `.env` being listed in `.gitignore`, it was tracked because it was added to git before the ignore rule was in place (or was force-added). The `.gitignore` entry gave a false sense of security — `git status` showed it as clean because changes to tracked-but-ignored files aren't flagged. | The auto-mode agent ran `secure_env_collect` which wrote secrets to `.env`, then subsequent `git add` or `git add -A` commands included it. The `.gitignore` doesn't prevent tracking of already-tracked files. | (1) Removed `.env` from git tracking via `git rm --cached .env`. (2) Replaced contents with placeholder-only template. (3) Scrubbed entire git history with `git-filter-repo --invert-paths --path .env --force` (rewrote all 2,504 commits). (4) Force-pushed all branches to GitHub. (5) Added Rule R08 requiring `git ls-files .env` verification. (6) ALL exposed keys must be rotated — GitHub caches old objects up to 90 days post-force-push. | Any project using `.env` for secrets — verify untracked status, not just `.gitignore` presence |
| K008 | M046/S07/T03: nginx frontend container crashed with `setgid(101) failed (Operation not permitted)` after Docker hardening commit added `security_opt: no-new-privileges` and `cap_drop: ALL`. The agent ran `docker compose -f docker-compose.test.yml down -v` to "start fresh", destroying the test stack's named volumes (database + triplestore). 42 E2E tests broke from the state loss — installed models, seed data, and auth sessions were gone. The data is recoverable by re-running `e2e/tests/00-setup/` specs, but the volume wipe was unnecessary. | The agent treated volume destruction as a quick fix for a container startup failure, without diagnosing the root cause first. The actual fix was removing `security_opt` from the frontend service in docker-compose.test.yml. No volume wipe was needed. | (1) Added Rule R09: never run `docker compose down -v` without explicit user confirmation. (2) When a single container won't start, diagnose the root cause from logs (`docker compose logs <service>`) and fix the config — don't nuke volumes. (3) Use `docker compose restart <service>` or `docker compose up -d --force-recreate <service>` for container-level fixes. | Any Docker stack — dev or test. Volume destruction is irreversible and disproportionate to most container startup failures. |

## E2E Test: SPARQL API Does Not Support UPDATE/DELETE

**Discovery date:** 2026-03-17  
**Context:** T02 E2E Playwright test for mental model expansion  

The `/api/sparql` endpoint (both GET and POST) only executes read queries (SELECT, ASK, CONSTRUCT, DESCRIBE). It does NOT support SPARQL UPDATE operations (INSERT, DELETE). Sending a DELETE query returns `400 Malformed SPARQL query`.

The triplestore client (`app.triplestore.client.TriplestoreClient`) has an `update()` method that works, but it's not exposed through any HTTP API endpoint.

**Impact:** E2E tests cannot clean up triplestore data (seed instances, created objects) via the API. Model uninstall is blocked when seed data exists because `check_user_data_exists()` queries `urn:sempkm:current` graph and finds instances.

**Workaround:** Make cleanup best-effort with skip-if-already-installed logic for idempotent reruns. For a proper fix, add a SPARQL UPDATE endpoint or a force-uninstall admin API.

## E2E Test: Docker Test Stack Volume Mounts From Worktree

**Discovery date:** 2026-03-17  
**Context:** T02 E2E Playwright test for mental model expansion  

The Docker test stack (docker-compose.test.yml) started from `.gsd/worktrees/M007/` mounts volumes from that worktree path, not from the main tree at `/home/james/Code/SemPKM/`. For example, `./models:/app/models:ro` resolves to `.gsd/worktrees/M007/models/`.

If model directories only exist in the main tree (e.g., after a T01 task copies them there), they must also be copied to the worktree's `models/` directory for the Docker container to see them.

**Check:** `docker inspect <container> --format '{{json .Mounts}}'` shows the resolved source paths.

## ninja-keys: Parent `children` Array Must List Child IDs

**Discovery date:** 2026-03-17  
**Context:** M012/S03/T03 — Command palette persona submenu

In ninja-keys, a parent command with `children: []` (empty array) does NOT auto-discover children by their `parent` property. The `children` array on the parent must contain the actual child IDs (e.g., `['persona-switch-abc123']`) for drill-down navigation to work. The `parent` property on children is only for breadcrumb display.

**Pattern:** When using `_refreshPersonaPaletteItems` or similar async population functions, always update both the child items' `parent` property AND the parent's `children` array with the child IDs.

## Cross-IIFE Guard Flags via window

**Discovery date:** 2026-03-17  
**Context:** M012/S03/T03 — workspace.js ↔ workspace-layout.js guard flag

`workspace.js` and `workspace-layout.js` are separate IIFEs. Variables declared inside one are not accessible from the other. To share a guard flag (like `_switchingPersona`), set it on `window` (e.g., `window._switchingPersona = true`) and check via `window._switchingPersona` in the other file.

## SPARQL API scopes to current state graph only

The `/api/sparql` endpoint (`backend/app/sparql/router.py`) calls `scope_to_current_graph()` which rewrites queries to only access `GRAPH <urn:sempkm:current>`. Event data lives in per-event named graphs (e.g. `urn:sempkm:event:abc123`) and is intentionally excluded to prevent data leakage.

**Consequence:** E2E tests cannot use the SPARQL API to query event metadata (operation types, affected IRIs). Use the event log UI or the event detail API endpoint (`/browser/events/{iri}/detail`) instead.

## Body save endpoint is POST not PUT

The save body endpoint is `POST /browser/objects/{encoded_iri}/body` with `Content-Type: text/plain` body. The task plan incorrectly specified PUT. The actual route is defined in `backend/app/browser/objects.py` as `@objects_router.post("/objects/{object_iri:path}/body")`.

## JSON API paths outside /api/ need _is_html_route exclusion

**Context:** `backend/app/main.py` has a `_is_html_route()` function that determines whether 401 errors should be returned as JSON or converted to 302 login redirects. It originally only excluded paths starting with `/api/`.

**Problem:** The `/.well-known/sempkm` discovery endpoint lives outside `/api/` but returns JSON. Without adding it to the exclusion list, unauthenticated requests got 302 redirects to `/login.html` instead of JSON `{"detail": "Not authenticated"}`.

**Rule:** Any new JSON API endpoint mounted outside the `/api/` prefix must also be excluded in `_is_html_route()`. Current exclusions: `/api/`, `/.well-known/`.

## SQLite naive datetimes vs timezone-aware Python datetimes

**Discovery date:** 2026-03-18
**Context:** M009/S07/T03 — App platform E2E test

SQLite stores datetimes without timezone info (naive). When Python code uses `datetime.now(timezone.utc)` to compute a timedelta against a SQLite-sourced value, it crashes with `TypeError: can't subtract offset-naive and offset-aware datetimes`.

**Fix:** Before subtracting, check `if dt.tzinfo is None: dt = dt.replace(tzinfo=timezone.utc)`. Applied in `AppManager.get_status()` for `instance.started_at`.

## Workspace explorer sections start collapsed

**Discovery date:** 2026-03-18
**Context:** M009/S07/T03 — App platform E2E test

The workspace sidebar explorer sections (FAVORITES, OBJECTS, VIEWS, DASHBOARDS, APPS, etc.) use a custom CSS toggle — the section needs `.expanded` class to show its body. They are NOT `<details>` elements. The section header has `onclick="this.parentElement.classList.toggle('expanded')"`.

**Impact on E2E tests:** After navigating to `/browser/`, the APPS section body content loads via htmx `hx-trigger="load"` but is hidden because the section is collapsed. Tests must click the section header to expand it before asserting on child content.

## E2E tests: Docker stack must run from main tree for auth fixture

**Discovery date:** 2026-03-18
**Context:** M009/S07/T03 — App platform E2E test

The Playwright auth fixture (`e2e/fixtures/auth.ts`) reads the setup token via `docker compose -f docker-compose.test.yml exec -T api cat ...` with `cwd` set to `git rev-parse --show-toplevel` (the main tree). If the Docker stack is started from a worktree, the auth fixture can't find the container because Docker Compose uses project-name scoping based on the directory.

**Workaround:** Either (a) sync worktree code to main tree and run Docker from main tree, or (b) start Docker from worktree AND update the auth fixture to use the worktree's compose file path.

## Playwright extension tests: chrome.storage.sync unreliable in persistent context

**Discovery date:** 2026-03-18
**Context:** M014/S05/T02 — E2E extension tests

When using `chromium.launchPersistentContext()` with `--load-extension`, settings saved via `chrome.storage.sync` on the options page may not be visible when the popup page loads in a new tab. The popup sees the "unconfigured" state even though the options page saved successfully.

**Fix:** Inject settings directly into `chrome.storage.local` via `page.evaluate()` on an extension page before navigating to the popup. The extension's `storage.js` has fallback from sync to local, so this works reliably.

## Playwright extension tests: SHACL form required fields block native form validation

**Discovery date:** 2026-03-18
**Context:** M014/S05/T02 — E2E extension tests

The SHACL renderer sets `required` on input elements, including those inside collapsed sections (RELATIONSHIPS, METADATA). When the form is submitted via button click, native browser validation fires before the JS `handleSave()` runs, and fails with "An invalid form control with name='' is not focusable" because the required fields are hidden.

**Fix:** Set `form.noValidate = true` via `page.evaluate()` before clicking the Save button. The extension's `handleSave()` does its own validation.

## Playwright extension tests: persistent context hangs navigating non-extension pages

**Discovery date:** 2026-03-18
**Context:** M014/S05/T02 — E2E extension tests

Navigating to `http://localhost:3901/browser/` in a page opened within the extension's persistent context can hang indefinitely (even with `waitUntil: 'domcontentloaded'`). The workspace page has SSE/long-polling connections that may interact poorly with the persistent context. Use API-only verification (SPARQL query) instead of UI verification for objects created via the extension.

## App template htmx URLs must use proxy prefix

**Discovery date:** 2026-03-18
**Context:** M016/S04/T01 — Linear Sync E2E test

App templates rendered by the SDK's `render_template()` are loaded into the workspace page via the proxy chain at `/app/{app_id}/_fragments/{fragment}`. However, htmx attributes inside those templates (e.g. `hx-post="/_fragments/connect/api-key"`) use absolute paths that bypass the proxy — the browser sends them directly to the origin, where no platform route matches `/_fragments/*`.

**Fix:** All htmx URLs in app templates must be prefixed with `/app/{app_id}/` so requests route through the `app_proxy_router` catch-all at `/app/{app_id}/{path:path}`. Example: `hx-post="/app/linear-sync/_fragments/connect/api-key"`.

**Impact:** Any future app that uses htmx forms in its templates must follow this pattern. A better long-term fix would be to inject the prefix via a Jinja2 global or context variable from the SDK.

## User guide has THREE files that must stay in sync

**Discovery date:** 2026-03-19
**Context:** M024 — Monday.com Sync App

There are **three** places that list user guide chapters:

1. `docs/guide/README.md` — markdown table of contents (source of truth)
2. `docs/guide/index.html` — static HTML sidebar for the standalone docs site
3. `backend/app/templates/guide.html` — in-app Docs & Tutorials page served at `/guide`

When adding a new chapter (e.g., a sync app guide), all three files must be updated together. The in-app `guide.html` was missed for chapters 25–36 because it's a Jinja2 template with hardcoded `<button>` elements — not auto-generated from README.md.

**Rule:** Any milestone that adds a user-guide chapter must update all three files. The docs update task should be part of the final slice or a dedicated docs slice.

---

### FastAPI Depends() Executes Before Function Body (D249, M025/S01/T01)

**Problem:** If a dependency function uses `token: str = Depends(get_session_token)` and `get_session_token` raises 401 when no cookie is present, a `settings.demo_mode` check in the function body never runs — FastAPI resolves all `Depends()` arguments *before* entering the function.

**Solution:** Replace the dependency chain with an optional parameter: `sempkm_session: str | None = Cookie(None)`. Then check `settings.demo_mode` as the first line. If not in demo mode, manually check for None and raise 401.

**Rule:** When adding a bypass/override at the top of a dependency function, verify that no `Depends()` parameter can raise before the function body runs. If it can, inline the parameter extraction.

### Container-side scripts need sys.path fix for app imports (M025/S02/T02)

**Problem:** Python scripts mounted at `/app/scripts/` via Docker volume cannot import the `app` package because `/app` is not on `sys.path`. The default path only includes `/app/.venv/lib/...` and the script's own directory. Running `python /app/scripts/seed-demo-data.py` fails with `ModuleNotFoundError: No module named 'app'`.

**Fix:** Add this block before any `from app.* import ...` statements:
```python
_app_root = str(Path(__file__).resolve().parent.parent)
if _app_root not in sys.path:
    sys.path.insert(0, _app_root)
```

**Rule:** Any new script under `scripts/` that imports from the `app` package must include this sys.path manipulation. FastAPI's uvicorn process doesn't need it because its working directory is `/app/`.

---

### pyshacl: `allow_warnings=True` means warnings don't affect `conforms`

**Discovered:** M030/S01/T02

When calling `pyshacl.validate(..., allow_warnings=True)`, the `conforms` return value stays `True` even when sh:Warning validation results are present. Warnings are captured in the results graph but don't cause non-conformance.

**Implication:** To detect if any warnings fired, you must inspect the results graph for `sh:ValidationResult` triples with `sh:resultSeverity sh:Warning`. Do NOT rely on `conforms is False`.

```python
# Correct: check results graph
for node in results_graph.subjects(RDF.type, SH.ValidationResult):
    severity = list(results_graph.objects(node, SH.resultSeverity))
    if any(str(s) == str(SH.Warning) for s in severity):
        # Warning found

# Wrong: conforms is True even with warnings
assert conforms is False  # FAILS when allow_warnings=True
```

---

### basic-pkm shapes are JSON-LD, not Turtle

**Discovered:** M030/S01/T02

The shapes file for basic-pkm is at `models/basic-pkm/shapes/basic-pkm.jsonld` (JSON-LD), not `.ttl`. The rules file IS Turtle at `models/basic-pkm/rules/basic-pkm.ttl`. When loading both into a combined graph:

```python
combined = Graph()
combined.parse("models/basic-pkm/shapes/basic-pkm.jsonld", format="json-ld")
combined.parse("models/basic-pkm/rules/basic-pkm.ttl", format="turtle")
```

---

### extract_scope_where_body() LIMIT clause edge case

**Discovered:** M031/S01/T03

`extract_scope_where_body()` uses an end-of-string regex (`\}\s*$`) to find the WHERE block's closing brace. Saved queries with `LIMIT`, `ORDER BY`, or other clauses after the closing brace return empty string — the regex doesn't match.

**Implication:** Callers should strip LIMIT/ORDER BY from the saved query text before passing to `extract_scope_where_body()`. The router's `_extract_where_body()` (brace-depth-counting version) handles these clauses correctly for query execution, but the scope injection utility does not.

```python
# Works: SELECT ?s WHERE { ?s a ex:Project }
extract_scope_where_body("SELECT ?s WHERE { ?s a ex:Project }")  # → "?s a ex:Project"

# Returns empty: SELECT ?s WHERE { ?s a ex:Project } LIMIT 10
extract_scope_where_body("SELECT ?s WHERE { ?s a ex:Project } LIMIT 10")  # → ""
```

---

### model_view_specs replaces all_specs in view templates

**Discovered:** M031/S01/T01

After carousel removal, view templates receive `model_view_specs` (only model-declared ViewSpecs for the active type) instead of the old `all_specs` (which merged generic + model-declared specs). The template guard is:

```jinja2
{% if model_view_specs is defined and model_view_specs | length > 0 %}
```

Dedicated view endpoints (`table_view()`, `cards_view()`, `graph_view()`) pass `model_view_specs: []` since they already serve a specific model-declared view. Only `generic_view()` populates this from `get_view_specs_for_type()`.

---

### PromotedViewData fields must use OPTIONAL SPARQL when listing

**Discovered:** M031/S02/T02

When extending `PromotedViewData` with new fields (`type_filter`, `scope_query_id`), the `list_promoted_views()` SPARQL must wrap all new predicates in OPTIONAL clauses. Without OPTIONAL, views saved without those fields (e.g., older query-based promoted views) are excluded from results entirely — the SPARQL pattern match fails if the triple doesn't exist.

This also applies to the original `fromQuery` predicate — making it OPTIONAL was necessary so generic saved views (which have no associated query) appear in the listing.

---

### Two-path pattern for saved views: generic vs. query-based

**Discovered:** M031/S02/T02

The Saved Views folder (`my_views.html`) needs two distinct code paths:
1. **Query-based promoted views** (created via "Pin as Saved View" on a saved query): use `openViewTab()` and `demoteView()` for unpin
2. **Generic saved views** (created via "Save View" toolbar button): use `openGenericViewTab(renderer, scopeQuery)` and `deleteSavedView()` for unpin

The distinguishing signal is whether the PromotedViewData has a `renderer_type` field — generic saves always have one; query-based promotions derive renderer from the ViewSpec.

---

### HTML5 drag-drop inside dockview panels needs stopPropagation()

**Discovered:** M031/S04/T02

dockview's panel drag system intercepts HTML5 drag events that bubble up from child elements. Any custom drag-drop UI within a dockview panel (kanban columns, sortable lists, etc.) must call `e.stopPropagation()` on `dragstart`, `dragover`, and `drop` handlers to prevent dockview from treating the drag as a panel detach/reorder operation. This is the same pattern as canvas resize handles (D127/CANVAS-01).

---

### dragLeave flicker prevention with contains(relatedTarget)

**Discovered:** M031/S04/T02

When implementing drag-over highlighting on a container element, the `dragleave` event fires when the cursor moves between child elements *within* the container — not just when it actually leaves. This causes the drag-over CSS class to flicker. Fix: check `e.currentTarget.contains(e.relatedTarget)` in the `dragleave` handler and only remove the highlight class when the cursor truly leaves the container.

```javascript
function onDragLeave(e) {
    if (e.currentTarget.contains(e.relatedTarget)) return; // still inside
    e.currentTarget.classList.remove('kanban-col-drag-over');
}
```

---

### Kanban status field detection uses SHACL sh:in, not hardcoded field names

**Discovered:** M031/S04/T01

`_detect_status_field()` scans all SHACL PropertyShapes for the type and finds the first with non-empty `sh:in` values, preferring properties with "status" in the path (case-insensitive). This is more general than the D286 planning decision which suggested hardcoding to `bpkm:taskStatus`. Any Mental Model type that adds `sh:in` enum constraints on a property will automatically work with the kanban view.

---

### Kanban test_kanban.py must run from backend/ directory

**Discovered:** M031/S04/T01

`pytest tests/test_kanban.py` must be run from the `backend/` directory (`cd backend && .venv/bin/python -m pytest tests/test_kanban.py -v`), not from the project root. The root `.env` file contains `LINEAR_API_KEY` which is rejected as an extra field by the Pydantic Settings model, causing import failures.

### Views needing full-height must use .view-flex-column wrapper — not calc()

**Discovered:** M031/S05/T04

Graph and kanban views used fragile `height: calc(100% - 90px)` which breaks when toolbar height changes. The fix is a shared `.view-flex-column` class (flex column, height:100%) with `flex:1; min-height:0` on the expandable child. Table/cards views don't need this — they use natural scrolling. Any new view type that must fill its panel should use this wrapper.

### Popovers inside dockview panels must escape stacking context via document.body

**Discovered:** M031/S05/T04

Any popover rendered inside a dockview panel is trapped in the panel's stacking context (position:relative). Elevating z-index won't help because dockview chrome has its own stacking context. The only reliable fix is `document.body.appendChild(popover)` with `position:fixed` and `getBoundingClientRect()` for positioning. Always add cleanup to remove the popover from body when the parent view/graph is destroyed.

### SPARQL vocab prefix exclusion: use specific sub-namespace allow-list, not broad prefix

**Discovered:** M031/S05/T01

The `_VOCAB_PREFIXES` tuple in `sparql/router.py` and the matching `KNOWN_VOCAB_PREFIXES` in `sparql-console.js` must list specific internal namespaces (urn:sempkm:query:, urn:sempkm:user:, etc.), NOT the broad `urn:sempkm:`. The broad entry caused all model ontology IRIs to be treated as vocabulary, preventing pill rendering. When adding a new internal namespace, add it to both backend and frontend lists.

---

### Builder autocomplete pattern: reference-field with hidden data-key input

**Discovered:** M031/S06/T02

IRI fields in dashboard/workflow builders use a `.reference-field` wrapper containing three elements: (1) a visible search `<input>` for user typing, (2) a hidden `<input data-key="field_name">` that stores the actual IRI value, and (3) a `.suggestions-dropdown` div. A shared helper function (`_builderAutocomplete(inputEl, endpoint)`) handles 300ms debounce, fetch, rendering, click-to-select, and click-outside dismiss. The save collector (`querySelectorAll('[data-key]')`) picks up the hidden input automatically. When adding new IRI fields to builders, follow this pattern rather than using plain text inputs.

### Verification grep checks: beware CSS class substring matches

**Discovered:** M031/S06/T01

When slice verification uses `grep -c 'some-class'` to verify a class is absent, any new class containing that string as a substring will create a false positive. T01 hit this with `step-config-renderer-auto` matching the `step-config-renderer` absence check. Solution: name replacement classes to avoid the substring (e.g., `wf-auto-renderer` instead of `step-config-renderer-auto`).

---

### E2E view selectors belong in SEL.views, not inline

**Discovered:** M031/S07/T01

All view-related E2E selectors (kanbanBoard, kanbanColumn, kanbanCard, scopeSelect, variantSelect, saveViewBtn) are centralised in `SEL.views` in `e2e/helpers/selectors.ts`. Future view tests should add selectors here rather than inlining CSS class strings in test files. This avoids selector drift when CSS classes change — update one place instead of hunting through specs.

### E2E: use openGenericViewTab helper, not UI clicks, to open view tabs

**Discovered:** M031/S07/T01

Opening view tabs in E2E tests should use the `openGenericViewTab(page, renderer, waitSelector, ...)` helper in `e2e/helpers/dockview.ts`, which calls `window.openGenericViewTab()` via `page.evaluate()` then waits for a DOM selector. This is more reliable than clicking through the explorer sidebar (which involves loading htmx partials, waiting for dockview panel creation, etc.). Timeout failures from this helper directly indicate whether the JS API or DOM rendering is broken.

---

### Planning estimates can be safely exceeded when the cost is marginal

**Discovered:** M031/S04

D286 (planning) called for hardcoding `bpkm:taskStatus` as the kanban status field. D291 (implementation) upgraded to general SHACL `sh:in` scan for ~20 extra lines. The SHACL approach is strictly better — supports any model type automatically — for negligible extra cost. When the implementation reveals a low-cost generalization that the plan didn't envision, prefer the better approach. Document the divergence in the decision log (D291 references D286).

### Dockview stacking context escape: always append to document.body

**Discovered:** M031/S05/T04

Any popover, tooltip, or overlay rendered inside a dockview panel is trapped in that panel's stacking context. Elevating `z-index` within the panel cannot escape the panel boundary. The only reliable approach is appending the element to `document.body` with `position:fixed` and computing coordinates via `getBoundingClientRect()`. Always register cleanup (e.g., `registerCleanup` callback) to remove body-appended elements when the panel is destroyed. This applies to graph popovers (D293), and will apply to any future hover card, context menu, or overlay inside dockview.

### data-sparql-loaded / data-chart-loaded are dedup guards, not readiness signals

**Discovered:** M032/S03/T01

`_executeSparqlWidgets()` sets `data-sparql-loaded="1"` on the element *before* calling `fetch('/api/sparql', ...)`. Similarly, `_initChartBlocks()` sets `data-chart-loaded="1"` before the Chart.js CDN load and SPARQL fetch. These attributes prevent re-execution on htmx re-swaps, but they do NOT indicate the async work has completed.

**Impact on E2E tests:** Waiting for `[data-sparql-loaded]` or `[data-chart-loaded]` to appear does not guarantee the content is ready. For stat-cards, wait until `[data-stat-target]` text is no longer "…" (the loading placeholder). For charts, wait until `Chart.getChart(canvas)` returns truthy or the canvas `toDataURL()` exceeds ~500 chars (non-blank).

### @slot:name convention for cross-command IRI references in batch payloads

**Discovered:** M032/S01/T01

The batch command endpoint (`POST /api/commands`) supports `@slot:name` references for cross-command dependencies. An `object.create` command with a `slot` field registers its minted IRI in a `slot_map`. Subsequent commands (e.g., `edge.create`) can use `@slot:slotName` as a value — the router resolves it to the actual IRI before execution. Unresolved references return HTTP 400.

**Pattern:** Commands execute sequentially. The `slot_map` accumulates as commands succeed. Order matters — a command referencing `@slot:X` must appear after the command that defines slot `X`.

```python
# In commands/router.py
slot_map = {}
for cmd in batch:
    if cmd.type == "object.create" and cmd.params.slot:
        slot_map[cmd.params.slot] = minted_iri
    # Resolve @slot: references in subsequent commands
    if value.startswith("@slot:"):
        resolved = slot_map.get(value[6:])
```

**Use beyond form-groups:** The convention is generic — any batch payload can use it. Future features (templates, import wizards, automation) that need to create linked objects in one API call can use `@slot:name` references.

### Cytoscape CSS 3D transforms require coordinate correction monkey-patch

**Discovered:** M033/S02/T02

Applying CSS 3D transforms (e.g., `perspective(800px) rotateX(55deg) rotateZ(-45deg)`) to a Cytoscape container causes click events to land on wrong nodes — the browser reports mouse coordinates in transformed screen space but Cytoscape expects untransformed coordinates. This is Cytoscape issue #1756.

**Fix:** Monkey-patch `cy.renderer().findContainerClientCoords` to apply the inverse DOMMatrix transform before Cytoscape processes click positions. For popover positioning, apply the forward DOMMatrix transform to convert Cytoscape model coordinates back to screen coordinates.

**Fragile:** The monkey-patch must be reapplied after layout changes. The DOMMatrix positioning assumes the transform is on `#cy-wrapper` — if the DOM hierarchy changes, popovers will misposition.

### CDN lazy-loading pattern for heavy JS libraries in view templates

**Discovered:** M033/S03/T02, M033/S04/T02

View templates that depend on heavy third-party libraries (FullCalendar 6.1.17 = ~400KB, Leaflet 1.9.4 + MarkerCluster 1.5.3 = ~200KB) use CDN lazy-loading: the template includes `<script>` tags with pinned CDN URLs, and the library is only fetched when the view tab is opened. This avoids bloating the initial workspace load.

**Risk:** CDN outage breaks these views entirely. The M029 vendor pipeline could absorb these libraries to eliminate the CDN dependency. Versions are pinned in the HTML templates — update requires editing the template file.

**Files:** `backend/app/templates/browser/calendar_view.html`, `backend/app/templates/browser/map_view.html`

### SHACL field detection heuristic: sh:datatype + well-known path IRI

**Discovered:** M033/S03/T01, M033/S04/T01

`_detect_date_fields()` and `_detect_geo_fields()` in `ViewSpecService` use a dual heuristic: (1) check SHACL PropertyShape `sh:datatype` (e.g., `xsd:date`, `xsd:dateTime`) and (2) match the `sh:path` IRI against a well-known list (e.g., `dcterms:date`, `schema:startDate`, `wgs84:lat`). This catches types that declare date/geo fields but use non-standard IRIs, and types that use standard IRIs but don't specify `sh:datatype`.

**Pattern:** Any future field-type-dependent renderer (timeline, gantt, etc.) should follow the same dual heuristic. The detection functions are on `ViewSpecService` and return structured results (field path IRIs + detected labels).

### Timeline _detect_date_fields priority: scheduledStart beats dueDate

**Discovered:** M034/S02/T03

The `_START_DATE_PRIORITY` list in `_detect_date_fields()` is `["scheduledstart", "startdate", "duedate", "targetdate", "created"]`. For the basic-pkm Task shape, which defines both `bpkm:scheduledStart` (xsd:dateTime) and `bpkm:dueDate` (xsd:date), the timeline SPARQL uses `scheduledStart` as the start field. Seed data tasks only populate `dueDate`, so the timeline view appears empty for seed tasks.

**Impact on E2E tests:** Tests that need tasks visible in the timeline must create tasks with `bpkm:scheduledStart` values, not `bpkm:dueDate`. The `createTask()` helper in `e2e/tests/02-views/timeline.spec.ts` demonstrates this pattern.

### Playwright SVG element visibility: use state:'attached' not toBeVisible

**Discovered:** M034/S02/T03

Frappe Gantt renders dependency arrows as `<g class="arrow">` SVG group elements. Playwright's visibility check reports these as "hidden" (`locator resolved to hidden <g class="arrow"></g>`) even when the arrows render visually in the browser. SVG group elements don't have intrinsic dimensions that Playwright can measure.

**Fix:** Use `page.waitForSelector('.arrow', { state: 'attached' })` instead of the default `{ state: 'visible' }`. Then assert count > 0 via `.count()`. This applies to any SVG sub-element (groups, paths, etc.) inside third-party charting libraries.

### Jinja2 dict key access: use col['items'] not col.items

**Discovered:** M034/S03/T03

In Jinja2, `col.items` on a Python dict resolves to the dict's `.items()` method (attribute lookup), not the `items` key. This caused `kanban_view.html` to crash with `TypeError: object of type 'builtin_function_or_method' has no len()` when the template used `{{ col.items | length }}` and `{% for item in col.items %}`.

**Fix:** Use bracket notation `col['items']` for dict key access when the key name collides with a dict method (`items`, `keys`, `values`, `get`, `update`, etc.). This is a Jinja2-specific gotcha — Python code `col["items"]` and `col.items` (via __getattr__) behave differently in Jinja2's attribute resolution order.

**Affected file:** `backend/app/templates/browser/kanban_view.html`

### python-dateutil rruleset.between() requires consistent naive/aware datetimes

**Discovered:** M034/S04/T02

`dateutil.rrule.rruleset.between(start, end)` raises `TypeError: can't compare offset-naive and offset-aware datetimes` if `start`/`end` are timezone-aware but the `dtstart` used in the rule is naive (or vice versa). RDF date/dateTime values parsed via `fromisoformat()` may be naive or aware depending on whether they include a `Z` suffix.

**Fix:** In the RRULE expansion code, strip timezone info from all datetimes before passing to rruleset: `dt.replace(tzinfo=None)`. The expansion window is computed as `datetime.now(timezone.utc).replace(tzinfo=None)` — getting UTC then stripping the tzinfo. This keeps all comparisons in naive-datetime space.

**Affected file:** `backend/app/views/service.py` — `_expand_rrule()` and `execute_calendar_query()` RRULE expansion block.

### nginx serves /js/ and /css/ but NOT /static/ — template paths must match

**Discovered:** M034/S04/T04

The nginx config (`frontend/nginx.conf`) defines `location /js/` and `location /css/` with `root /usr/share/nginx/html`. There is NO `/static/` location. Requests to `/static/js/foo.js` fall through to the catch-all proxy → backend, which returns 404.

**Impact:** `calendar_view.html` used `<script src="/static/js/calendar.js">` which returned 404, silently breaking all calendar functionality. Same issue affected `_field.html` with `recurrence-editor.js`.

**Rule:** All JS references in templates must use `/js/filename.js`, not `/static/js/filename.js`. All CSS references must use `/css/filename.css`. The Docker volume mount maps `frontend/static/` → `/usr/share/nginx/html/`, so the file at `frontend/static/js/calendar.js` is served at `/js/calendar.js`.

### htmx swap of <script src> races with subsequent inline scripts

**Discovered:** M034/S04/T04

When htmx swaps HTML containing `<script src="/js/foo.js"></script>` followed by `<script>if (typeof foo === 'function') foo();</script>`, the external script loads asynchronously but the inline script executes immediately. The function from the external script is not yet defined when the inline script runs.

**Fix:** Use the lazy-load pattern instead:
```javascript
(function() {
    function _boot() { /* use the loaded function */ }
    if (typeof targetFn === 'function') { _boot(); }
    else {
        var s = document.createElement('script');
        s.src = '/js/foo.js';
        s.onload = _boot;
        document.head.appendChild(s);
    }
})();
```

This pattern is already used by `recurrence-editor.js` (T03) and now `calendar_view.html` (T04).

### CopilotService module location: backend/app/copilot/ not backend/app/services/

**Discovered:** M035/S01/T01

CopilotService lives in `backend/app/copilot/service.py` as a dedicated package with `schemas.py` and `__init__.py`. Not in the flat `backend/app/services/` directory. The plan referenced `backend/app/services/copilot.py` but the executor chose a package structure. Future S02/S03 work (conversation persistence, personas) should add files to this package.

### SSE streaming from POST endpoint: use ReadableStream, not EventSource

**Discovered:** M035/S01/T03

The browser's `EventSource` API only supports GET requests. The copilot chat endpoint is POST (sends messages array as JSON body). `copilot.js` uses `fetch()` with `response.body.getReader()` and manual line-based SSE parsing. The parser handles three event types: `data:` (OpenAI streaming chunks), `event: sparql_query` (SPARQL detection), and `event: error`.

**Pattern:** Any future SSE endpoint that requires POST with a JSON body must use this ReadableStream approach on the frontend. The parsing logic is in `copilot.js` `_streamCopilotResponse()`.

### Copilot SPARQL extraction: three-tier heuristic from LLM response text

**Discovered:** M035/S01/T01

LLMs return SPARQL in unpredictable formats. `_extract_sparql_from_response()` tries three strategies in order: (1) fenced ` ```sparql ` code block, (2) any fenced code block containing a SELECT/ASK keyword, (3) heuristic line detection (lines starting with SELECT/PREFIX/ASK). This handles GPT-4, Claude, and Llama response styles. Mutation keywords in generic code blocks are rejected at the extraction stage.

### Custom SSE events coexist with OpenAI streaming format

**Discovered:** M035/S01/T02

The `/api/copilot/chat` endpoint emits both standard OpenAI `data: {"choices":[...]}` lines AND custom SSE events (`event: sparql_query`, `event: error`). The backend accumulates streamed content and emits `sparql_query` events when complete code blocks are detected. The frontend parser dispatches based on the `event:` line preceding the `data:` line. This mixed-event pattern enables inline SPARQL approval without a separate communication channel.

### SQLAlchemy auto-flush: do conditional checks BEFORE db.add()

**Discovered:** M035/S02/T02

When adding a row with `db.add(obj)` and then running a SELECT query on the same session (e.g., to count existing rows), SQLAlchemy auto-flushes the pending `add()` before executing the SELECT. This means the just-added object appears in the query results, even though `await db.commit()` hasn't been called yet.

**Impact:** `ConversationService.add_message()` auto-titles a conversation on the first user message by checking `SELECT COUNT(*) ... WHERE role='user'`. If the new message is added first, the count is 1 (not 0), so the "is this the first?" check fails and auto-titling never fires.

**Fix:** Move the conditional check (SELECT) before `db.add()`. The pending object isn't in the session yet, so the query sees the true state.

```python
# Correct: check BEFORE add
existing_count = await db.scalar(select(func.count(...)))
db.add(new_message)  # now add
if existing_count == 0:
    conversation.title = derive_title(content)

# Wrong: check AFTER add — auto-flush makes new_message visible
db.add(new_message)
existing_count = await db.scalar(select(func.count(...)))  # sees the pending add!
```

**Affected file:** `backend/app/copilot/conversation.py` — `add_message()` method


### Copilot tab lazy-load requires two-phase wait in E2E tests

**Discovered:** M035/S04/T02

The AI COPILOT tab is lazy-loaded via dynamic `import()` in workspace.js. The module only initializes when the tab is first clicked. In E2E tests, clicking the `button.panel-tab[data-panel="ai-copilot"]` tab triggers an async import + initialization chain. Simply waiting for `#copilot-container` to be visible is insufficient — the conversation header and input area aren't ready until the async fetch of conversations completes.

**Pattern:** The `openCopilotTab()` E2E helper uses a two-phase wait:
1. Click the tab button, wait for `#copilot-container` to be visible
2. Wait for `#copilot-conv-header` to render (signals async initialization complete)

**Affected file:** `e2e/tests/46-copilot/copilot.spec.ts`

### Mock LLM server: _select_response() route priority matters for backward compat

**Discovered:** M035/S04/T01

The mock LLM server at `e2e/mock-llm-api/server.py` uses keyword matching on user message content to select canned responses. Route checking order is: claims > SPARQL > create-object > summarize > generic. The claims route MUST stay first because M028 browser extension tests depend on messages containing "extract" or "claim" routing to the claims handler.

**Impact:** When adding new copilot-specific canned routes, insert them AFTER the claims check but BEFORE the generic fallback. A message matching multiple routes (e.g., "extract data and create a task") will hit the first matching route.

**Affected file:** `e2e/mock-llm-api/server.py` — `_select_response()` function

---

### Expo SDK 55: src/app/ route directory, not app/

**Discovered:** M037/S03/T01

Expo SDK 55's default template uses `src/app/` as the file-based routing directory (not `app/`). All screens, layouts, and route groups live under `mobile/src/app/`. This is configured in the template's `package.json` `main` field and `app.json` — don't change it.

**Impact:** All `mobile/src/app/(app)/(tabs)/` paths are correct for the tab navigator. Future slices (S04 zones, S05 calendar) add screens under this same tree.

### expo-router: root-level routes shadow group routes

**Discovered:** M037/S03/T03

expo-router matches root-level files in `src/app/` before group directories like `(app)/`. If `src/app/index.tsx` exists alongside `src/app/(app)/(tabs)/index.tsx`, the root file wins — the tab navigator never renders. Similarly, a `(app)/index.tsx` shadows `(app)/(tabs)/index.tsx`.

**Rule:** Delete any index/route files at shallower levels if they conflict with the intended deeper route group. The auth pattern requires: sign-in at root level (`src/app/sign-in.tsx`), everything else inside `(app)/` group with guard layout, tabs inside `(app)/(tabs)/`.

### Expo SDK 55: --non-interactive requires CI=1 env var

**Discovered:** M037/S03/T01

`npx expo start --non-interactive` does not work as a standalone CLI flag in SDK 55. Metro prints "use $CI=1 instead". For headless/CI verification, use `CI=1 npx expo start --no-dev` or `CI=1 timeout 20 npx expo start --no-dev --non-interactive`.

### expo-task-manager: TaskManager.defineTask MUST be at module top-level scope

**Discovered:** M037/S04/T02

`TaskManager.defineTask('task-name', callback)` must be called at the top level of a module — not inside a component, hook, or async function. The native side registers task callbacks at app initialization time. If the call is inside a component, the callback isn't registered when the OS triggers the background task, and the event is silently dropped.

**Pattern:** Define the task in a dedicated service file (e.g., `geofencing.ts`) at module scope. Import the file as a side-effect (`import '@/services/geofencing'`) in the root `_layout.tsx` before any component renders. The callback cannot use React context — read credentials from `expo-secure-store` directly.

### react-native-maps: LongPressEvent vs MapPressEvent types

**Discovered:** M037/S04/T03

`react-native-maps` TypeScript types distinguish between `MapPressEvent` (for `onPress`) and `LongPressEvent` (for `onLongPress`). Using `MapPressEvent` for the `onLongPress` handler causes a type error. The `LongPressEvent` type includes the `action` discriminant that identifies it as a long-press.

### expo-sensors does NOT require an app.json plugin entry for ≤1Hz sampling

**Discovered:** M037/S05/T01

`expo-sensors` (Accelerometer, Pedometer) at 1Hz or slower does not need an `expo-sensors` plugin entry in `app.json`. Android's `HIGH_SAMPLING_RATE_SENSORS` permission is only required for sampling rates above 200Hz. The package installs as a regular dependency without native config. Only `expo-calendar` needed a plugin entry (for calendar read permission).

### Pedometer walking override for low-variance steady-pace walking

**Discovered:** M037/S05/T02

Accelerometer magnitude variance alone misclassifies steady-pace straight-line walking as "stationary" because the magnitude stays nearly constant despite movement. Supplementing with `Pedometer.watchStepCount()` on a 3-second snapshot window resolves this — increasing step count overrides the variance-based classification to "walking". This dual-sensor pattern should be used whenever accelerometer-only classification proves insufficient.

### expo-notifications SDK 55: shouldShowBanner/shouldShowList replaces shouldShowAlert

**Discovered:** M037/S06/T04

In Expo SDK 55 (`expo-notifications ~55.0.10`), the `NotificationBehavior` interface requires `shouldShowBanner: boolean` and `shouldShowList: boolean` instead of the old `shouldShowAlert: boolean`. Using `shouldShowAlert` still compiles with a deprecation warning at runtime but causes a TypeScript error because the required fields are missing. The handler must return both `shouldShowBanner` and `shouldShowList` for foreground notification display to work.

**Affected file:** `mobile/src/services/notifications.ts` — `setupNotificationHandler()` function.

### Multi-service integration test fixture: wire real services on app.state, mock only externals

**Discovered:** M037/S07/T01

When testing cross-service integration (ContextService + RulesEngine + PersonaService + NotificationService), wire all services as real implementations against in-memory SQLite. Only mock truly external dependencies (Firebase = no-op via firebase_app=None). Wire services onto `app.state` matching the exact attribute names from `main.py` lifespan. Add dependency overrides for both `Depends()`-injected and `request.app.state`-accessed services. Disable rate limiter (`limiter.enabled = False`) on the test app to prevent interference across test methods.

**Reference implementation:** `backend/tests/test_context_integration.py` — 12 tests proving full context→persona→notification loop with real services and in-memory DB.

### firebase-admin no-op mode: safe when firebase_app is None

**Discovered:** M037/S06/T01

`NotificationService.__init__()` accepts an optional `firebase_app` parameter. When `None`, all dispatch methods become no-ops (return None without attempting to call `messaging.send()`). This means all 184 M037 tests pass without Firebase credentials, and the backend runs normally without push capability when `FIREBASE_CREDENTIALS_PATH` is empty. Import `firebase_admin.messaging` lazily inside `send_notification()` to avoid import failure when the package is installed but not initialized.


### App module test patching: patch on _app_mod, not _svc_mod

**Discovered:** M038/S01/T04

When testing app modules loaded via `importlib.util.spec_from_file_location()`, the app's fallback import path creates its own bound function references. Patching the original service module (`_svc_mod.fetch_feed`) has no effect because `app.py` already captured a reference to that function at import time. Patch the app module instead (`_app_mod.fetch_feed`). This applies to all App Platform apps that use the `importlib` fallback import pattern (try SDK import, except ImportError use importlib).

**Reference:** `backend/tests/test_media_scheduler.py` — `TestPollSources` class patches `_app_mod.fetch_feed`, `_app_mod.parse_feed_content`, etc.

### Starlette MutableHeaders: use `del`, not `pop()`, to remove headers

**Discovered:** M043/S02/T02

Starlette's `MutableHeaders` class does not implement `pop()`. Calling `response.headers.pop("some-header")` raises `AttributeError`. Use `del response.headers["some-header"]` instead. This applies to any custom middleware that modifies response headers (e.g., `_WellKnownCORSMiddleware` stripping `Access-Control-Allow-Credentials`).

**Affected file:** `backend/app/main.py` — `_WellKnownCORSMiddleware`

### slowapi headers_enabled=True crashes on Pydantic-model-returning endpoints

**Discovered:** M043/S04/T01

Setting `headers_enabled=True` on a `Limiter()` instance causes `response must be an instance of Response` errors when the decorated endpoint returns a Pydantic model instead of a raw `Response` object. slowapi's header injection tries to call `response.headers` on the Pydantic object, which doesn't have that attribute.

**Fix:** Keep `headers_enabled=False` and set `Retry-After` explicitly in a custom rate limit handler (`_rate_limit_exceeded_handler_with_logging`). The custom handler receives a proper `Request` + `RateLimitExceeded` exception and returns a `JSONResponse` with the header manually set.

**Affected file:** `backend/app/auth/rate_limit.py` — limiter instance, `backend/app/main.py` — custom handler registration

### Audit logging helper must manage its own DB session

**Discovered:** M043/S04/T02

`log_security_event()` in `backend/app/auth/audit.py` creates its own `async_session_factory()` session rather than accepting a session parameter. This is because: (1) the helper must never fail the parent operation, so it needs its own try/catch boundary, (2) the parent's session may not exist yet (failed login = no authenticated session), and (3) the helper is called from router handlers where the session lifecycle is managed by FastAPI Depends. The `_audit()` wrapper in `router.py` uses `getattr(request.app.state, 'async_session_factory', None)` — test environments that don't set the factory silently skip audit logging.

**Affected file:** `backend/app/auth/audit.py`, `backend/app/auth/router.py`

### Dockview panel dispose() → cleanup registry wiring

**Discovered:** M044/S02/T01

All three dockview content renderers (object-editor, view-panel, special-panel) in `workspace-layout.js` have `dispose()` methods that call `window.runCleanup(el.id)` on the panel root and all child elements with IDs. This is the correct teardown path for any JS code that registers cleanup via `window.registerCleanup(elementId, fn)`. When adding new panel types or view renderers, register cleanup functions keyed to the panel's root element ID — they fire automatically when dockview destroys the panel.

**Pattern for document/window listeners in per-panel JS:** Store handler references in module-scoped variables (not anonymous functions). Remove before re-adding to prevent stacking on panel reopen. Register a `registerCleanup()` callback that removes all document/window listeners + destroys library instances. See `calendar.js` and `canvas.js` for reference implementations.

**Affected files:** `frontend/static/js/workspace-layout.js`, `frontend/static/js/cleanup.js`, `frontend/static/js/calendar.js`, `frontend/static/js/canvas.js`

### Three-phase cross-file symbol migration pattern

**Discovered:** M044/S03

When renaming or relocating cross-file symbols (e.g., `window.X` → `window.SemPKM.X`), use a three-phase rollout:
1. **T01 — Add new exports + backward-compat shims:** Each JS file exports to the new location AND sets the old name as a shim (`window.openTab = window.SemPKM.openTab`). All callers continue working against old names.
2. **T02 — Migrate all consumers:** Templates, inline scripts, and E2E tests switch from old names to new names. Old shims still catch any missed references.
3. **T03 — Remove all shims:** Grep confirms zero old-name references remain, then remove all shim assignments.

This ensures zero breakage at any intermediate commit — the shim phase is the key safety mechanism. Applied to 228 exports across 26 JS files, 52 templates, and 40 E2E files with zero functional regressions.

**Affected files:** All `frontend/static/js/*.js` files exporting to window

### CSS color-mix() replaces rgba() for transparent theme colors

**Discovered:** M044/S04

Instead of `rgba(255, 182, 43, 0.1)` for semi-transparent decorative colors, use `color-mix(in srgb, var(--_color-amber-500) 10%, transparent)`. This pattern:
1. References theme tokens instead of hardcoded RGB values
2. Automatically adapts to dark mode (tokens can be overridden per-theme)
3. Eliminated 66 dark-mode override blocks in M044

Define primitive tokens in theme.css `:root` (e.g., `--_color-bmc-revenue: #59a14f`) and reference them via color-mix in component CSS. The `--_` prefix convention denotes internal/primitive tokens not intended for direct use by component authors.

**Affected files:** `frontend/static/css/theme.css`, `frontend/static/css/bmc.css`, `frontend/static/css/quadrant.css`, `frontend/static/css/okr.css`, `frontend/static/css/decision-matrix.css`

### Pydantic EmailStr rejects .local TLD — causes silent 422 on invite endpoints

**Discovered:** M046/S01/T01

Pydantic's `EmailStr` validator rejects the `.local` TLD (RFC 6762 multicast DNS special-use domain). An API endpoint using `EmailStr` for email validation returns 422 for addresses like `member@test.local`. If the caller doesn't check the response status, this fails silently — the downstream magic-link endpoint returns `token: null` and all auth-dependent tests break.

**Fix:** Use `example.com` (RFC 2606 reserved domain, universally accepted by email validators) for test email addresses that pass through `EmailStr` validation. Note: `OWNER_EMAIL` uses `test.local` and still works because the setup/magic-link endpoints use plain `str`, not `EmailStr`.

**Affected file:** `e2e/fixtures/auth.ts` — `MEMBER_EMAIL`
