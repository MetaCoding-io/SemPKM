---
estimated_steps: 17
estimated_files: 1
skills_used: []
---

# T02: Wire 5 missing mock API services into docker-compose.test.yml

Add 5 mock API Docker services and their corresponding environment variables to `docker-compose.test.yml`. Follow the exact pattern of the existing mock-linear/mock-github/mock-jira/mock-monday services.

**Services to add (all use same pattern: python:3.12-slim, volume mount, python server.py, health check, sempkm-test network):**

1. `mock-todoist` — volume `./e2e/mock-todoist-api:/app:ro`
2. `mock-asana` — volume `./e2e/mock-asana-api:/app:ro`
3. `mock-caldav` — volume `./e2e/mock-caldav-api:/app:ro`
4. `mock-google-calendar` — volume `./e2e/mock-google-calendar-api:/app:ro`
5. `mock-outlook` — volume `./e2e/mock-outlook-api:/app:ro`

**Environment variables to add to the api service (apps inherit the API container's env):**
- `TODOIST_API_URL: http://mock-todoist:8080`
- `ASANA_API_URL: http://mock-asana:8080`
- `ASANA_TOKEN_URL: http://mock-asana:8080/-/oauth_token`
- `GCAL_API_URL: http://mock-google-calendar:8080`
- `GOOGLE_TOKEN_URL: http://mock-google-calendar:8080/oauth/token`
- `OUTLOOK_API_URL: http://mock-outlook:8080`
- `OUTLOOK_TOKEN_URL: http://mock-outlook:8080/oauth2/v2.0/token`

Note: CalDAV doesn't need an env var — the server URL is user-supplied via the connect form.

**Add depends_on entries** for all 5 new mock services to the api service's depends_on block (with `condition: service_healthy`).

## Inputs

- ``docker-compose.test.yml` — existing mock service definitions as pattern reference`
- ``e2e/mock-todoist-api/server.py` — mock server exists on disk`
- ``e2e/mock-asana-api/server.py` — mock server exists on disk`
- ``e2e/mock-caldav-api/server.py` — mock server exists on disk`
- ``e2e/mock-google-calendar-api/server.py` — mock server exists on disk`
- ``e2e/mock-outlook-api/server.py` — mock server exists on disk`

## Expected Output

- ``docker-compose.test.yml` — 5 new mock service definitions + env vars + depends_on entries`

## Verification

grep -c 'mock-todoist\|mock-asana\|mock-caldav\|mock-google-calendar\|mock-outlook' docker-compose.test.yml | grep -q '[5-9]' && grep -q 'TODOIST_API_URL' docker-compose.test.yml && grep -q 'GCAL_API_URL' docker-compose.test.yml && grep -q 'OUTLOOK_API_URL' docker-compose.test.yml && echo 'PASS'
