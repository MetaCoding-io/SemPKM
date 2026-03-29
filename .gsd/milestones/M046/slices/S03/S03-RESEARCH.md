# S03 Research — App Platform: Subprocess Lifecycle in Test Container

## Summary

App subprocess lifecycle in the test container is broken by **three distinct bugs** and **missing infrastructure** (mock services + selectors). The tests that already have mock services + selectors (linear, github, jira, monday, app-platform) fail because apps never reach "running" status — the subprocess start call crashes. The tests for todoist, caldav, asana, rss-reader, media-scheduler, google-calendar, and outlook additionally have TypeScript compilation errors from missing selectors and missing Docker mock services.

## Recommendation

Fix the three backend bugs first (they block ALL app tests), then wire up missing mock services in docker-compose.test.yml, then add missing selectors. Work divides cleanly into: (1) backend bug fixes, (2) docker infrastructure, (3) E2E test compilation fixes.

---

## Implementation Landscape

### Bug 1: `platform_url` defaults to wrong port — apps can't reach platform API

**File:** `backend/app/main.py` lines 399–404  
**Impact:** All app subprocesses  

The `APP_BASE_URL` env var is not set in docker-compose.test.yml. The code defaults to `http://localhost:4000`. But port 4000 maps to the frontend (nginx) only in the dev compose; in the test compose, frontend is on port 3901 (external) / 80 (internal). Inside the API container, the API listens on `localhost:8000`. App subprocesses run inside the API container and need to call back to the platform. With `http://localhost:4000` nothing is listening, so health checks and all SDK client calls fail.

**Fix:** Add `APP_BASE_URL: http://localhost:8000` to docker-compose.test.yml's api service environment block.

### Bug 2: Scheduler naive/aware datetime comparison

**File:** `backend/app/apps/scheduler.py` line 257  
**Impact:** Scheduler crashes repeatedly once any app has run a task  

```python
elapsed = (now - last_run.started_at).total_seconds()
```

`now` = `datetime.now(timezone.utc)` (aware). `last_run.started_at` from SQLite is naive. Raises `TypeError: can't subtract offset-naive and offset-aware datetimes`.

**Fix:** Before the subtraction, normalize `last_run.started_at`:
```python
started = last_run.started_at
if started.tzinfo is None:
    started = started.replace(tzinfo=timezone.utc)
elapsed = (now - started).total_seconds()
```

This is the same pattern from Knowledge entry about SQLite naive datetimes (discovered M009/S07/T03).

### Bug 3: `get_secret()` vs `get_app_secret()` NameError (may be fixed)

**File:** `backend/app/apps/manager.py` line ~193  
**Impact:** All app start/auto_start calls  

The container logs show:
```
NameError: name 'get_secret' is not defined. Did you mean: 'get_app_secret'?
```

However, the current source code on disk is correct — it imports and calls `get_app_secret(app_id)`. The error occurred because the container ran an older version. Since docker-compose.test.yml mounts `./backend/app:/app/app`, a container restart should pick up the fix. **Verify this is genuinely fixed after rebuild; if the image baked the old code, a rebuild is needed.**

Note: The container IS running with `--reload` from the dev compose image. The test compose lacks a `command:` override, so it uses the image CMD. If the image was built by the dev compose (which adds `--reload`), the test container gets `--reload` too. The code should have auto-reloaded, but the logs show it didn't recover. This may be because the reload process saw the file change but the import caching kept the old bytecode for the subprocess invocation path.

### Missing Infrastructure: Docker Mock Services

**File:** `docker-compose.test.yml`

5 mock API servers exist on disk but aren't wired into the test stack:

| Mock Server | Path | Env Var Needed | Test Spec |
|---|---|---|---|
| mock-todoist | `e2e/mock-todoist-api/server.py` | `TODOIST_API_URL: http://mock-todoist:8080` | `37-todoist-sync` |
| mock-asana | `e2e/mock-asana-api/server.py` | `ASANA_API_URL: http://mock-asana:8080`, `ASANA_TOKEN_URL: http://mock-asana:8080/-/oauth_token` | `40-asana-sync` |
| mock-caldav | `e2e/mock-caldav-api/server.py` | `CALDAV_URL: http://mock-caldav:8080/` | `39-caldav-calendar` |
| mock-google-calendar | `e2e/mock-google-calendar-api/server.py` | `GOOGLE_CALENDAR_API_URL: http://mock-google-calendar:8080`, `GOOGLE_TOKEN_URL: http://mock-google-calendar:8080/oauth/token` | `36-google-calendar-sync` |
| mock-outlook | `e2e/mock-outlook-api/server.py` | `OUTLOOK_API_URL: http://mock-outlook:8080`, `OUTLOOK_TOKEN_URL: http://mock-outlook:8080/oauth2/v2.0/token` | `38-outlook-sync` |

Each mock server follows the same pattern as the existing 4 mocks: python:3.12-slim image, volume mount of server directory, `python server.py` command, health endpoint at `/health`, port 8080.

The env var names need to be verified against the actual app source code:

| App | Env var reading code |
|---|---|
| todoist-sync | `os.environ.get("TODOIST_API_URL", "https://api.todoist.com/rest/v2")` in `services/todoist_client.py` and `services/auth.py` |
| asana-sync | `os.environ.get("ASANA_API_URL", "https://app.asana.com/api/1.0")` and `os.environ.get("ASANA_TOKEN_URL", "https://app.asana.com/-/oauth_token")` in `services/asana_client.py` and `services/auth.py` |
| caldav-calendar | No env var for URL — the server URL is user-supplied via the connect form. The test fills `http://mock-caldav:8080/` directly in the form. So only a running mock-caldav Docker service is needed. |
| google-calendar | Needs checking — `os.environ.get("GOOGLE_CALENDAR_API_URL", ...)` etc. |
| outlook-calendar | Needs checking — `os.environ.get("OUTLOOK_API_URL", ...)` etc. |

**Important:** App subprocesses inherit the API container's environment. Env vars like `TODOIST_API_URL` set on the api service are visible to all spawned app processes.

### Missing Infrastructure: E2E Selectors

**File:** `e2e/helpers/selectors.ts`

Missing selector groups (referenced by test specs but not defined):
- `SEL.todoistSync` — 14 TS errors in `37-todoist-sync/todoist-sync.spec.ts`
- `SEL.asanaSync` — 18 TS errors in `40-asana-sync/asana-sync.spec.ts`
- `SEL.caldavCalendarSync` — 17 TS errors in `39-caldav-calendar/caldav-calendar-sync.spec.ts`
- `SEL.googleCalendarSync` — 17 TS errors in `36-google-calendar-sync/google-calendar-sync.spec.ts`
- `SEL.outlookCalendarSync` — 17 TS errors in `38-outlook-sync/outlook-calendar-sync.spec.ts`
- `SEL.rss` — 36 TS errors in `31-rss-reader/rss-reader.spec.ts`
- `SEL.apps.installDetails`, `SEL.apps.installPathInput`, `SEL.apps.sidebarAppsSection`, `SEL.apps.appsTree` — referenced in rss-reader.spec.ts but not in the `apps` group

Total: 133 TS compilation errors across the E2E test suite (68 from these missing selectors, plus 65 from extension tests' `chrome` global).

The selector values can be derived from the actual test HTML templates. Pattern: each selector is a CSS selector string matching the HTML element id/class in the app's connect/settings templates.

### App Dependencies That Need Network Access

Some apps have real pip dependencies:
- `asana-sync`: `markdownify`
- `caldav-calendar`: `icalendar`
- `rss-reader`: `feedparser>=6.0`, `trafilatura>=2.0`
- `media-scheduler`: `feedparser>=6.0`

The `uv pip install` inside the container downloads from PyPI. The container needs outbound internet access during app installation. This should work by default (Docker networking), but `cap_drop: ALL` plus `no-new-privileges:true` don't block networking — they only drop Linux capabilities.

---

## Key Files

| File | Role |
|---|---|
| `backend/app/apps/manager.py` | AppManager — subprocess lifecycle (install, start, stop, health check, crash recovery) |
| `backend/app/apps/scheduler.py` | AppScheduler — periodic task execution, has datetime bug |
| `backend/app/apps/tokens.py` | JWT token generation for app auth, has both `get_secret()` and `get_app_secret()` |
| `backend/app/main.py` (lines 395-440) | AppManager initialization, platform_url resolution, auto_start call |
| `backend/sdk/sempkm_app_sdk/runner.py` | SDK runner — subprocess entry point, starts uvicorn on UDS |
| `docker-compose.test.yml` | Test stack definition — missing 5 mock services and APP_BASE_URL |
| `e2e/helpers/selectors.ts` | Shared E2E selectors — missing 6+ selector groups |
| `e2e/mock-todoist-api/server.py` | Mock Todoist API (383 lines, exists but not wired) |
| `e2e/mock-asana-api/server.py` | Mock Asana API (970 lines, exists but not wired) |
| `e2e/mock-caldav-api/server.py` | Mock CalDAV server (677 lines, exists but not wired) |
| `e2e/mock-google-calendar-api/server.py` | Mock Google Calendar API (488 lines, exists but not wired) |
| `e2e/mock-outlook-api/server.py` | Mock Outlook API (560 lines, exists but not wired) |

## Natural Task Seams

1. **Backend bug fixes** (scheduler.py datetime fix, main.py APP_BASE_URL, verify tokens.py) — blocks everything; small focused changes, easy to verify with unit tests or container restart
2. **Docker infrastructure** (add 5 mock services to docker-compose.test.yml, add env vars to api service) — blocks sync app tests for todoist/asana/caldav/google/outlook
3. **Selector additions** (add 6+ selector groups to selectors.ts) — blocks TS compilation of the failing test specs. Values must match the actual HTML templates from each app.
4. **Verification** — rebuild test stack, run the full set of affected E2E tests

Tasks 1 and 2 are independent. Task 3 depends on understanding the HTML output of each app (to derive correct CSS selectors). Task 4 depends on all three.

## Risks

1. **Network access for pip in container** — If the test container can't reach PyPI (firewall, offline CI), apps with real deps (asana, caldav, rss, media-scheduler) will fail to install. Mitigation: pre-build app venvs in the Docker image or use a pip cache volume.
2. **Selector drift** — The selector values in tests must match the actual HTML rendered by app templates. If app templates have changed since the tests were written, selectors may be wrong even after adding them to selectors.ts.
3. **Stale container state** — The test stack shares project name `sempkm` with the dev stack. If dev containers exist, `docker compose -f docker-compose.test.yml up` may reuse dev containers/images with wrong CMD. Consider adding `name: sempkm-test` to the test compose file.
