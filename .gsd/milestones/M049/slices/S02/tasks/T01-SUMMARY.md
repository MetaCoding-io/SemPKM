---
id: T01
parent: S02
milestone: M049
key_files:
  - backend/pyproject.toml
  - backend/uv.lock
  - backend/app/config.py
  - docker-compose.yml
key_decisions:
  - Accepted OTel 1.40.0 / 0.61b0 (latest compatible with ~=1.31 / ~=0.52b0 pins) — all from same release train
duration: 
verification_result: passed
completed_at: 2026-04-05T20:29:38.535Z
blocker_discovered: false
---

# T01: Added 6 OpenTelemetry packages, Jaeger v2 Docker service, and otel_enabled/otel_exporter_endpoint config settings

**Added 6 OpenTelemetry packages, Jaeger v2 Docker service, and otel_enabled/otel_exporter_endpoint config settings**

## What Happened

Added opentelemetry-api, opentelemetry-sdk, opentelemetry-exporter-otlp-proto-http, opentelemetry-instrumentation-fastapi, opentelemetry-instrumentation-httpx, and opentelemetry-semantic-conventions to pyproject.toml. Resolved to 1.40.0 (core) and 0.61b0 (instrumentation) — same release train. Added otel_enabled (default False) and otel_exporter_endpoint settings to the Settings class. Added Jaeger v2 service to docker-compose.yml with OTLP HTTP receiver on port 4318, UI on 16686, 512MB memory limit. Added OTEL_ENABLED and OTEL_EXPORTER_ENDPOINT env vars to the api service.

## Verification

All 5 task verification checks pass: uv lock --check exits 0, OTel SDK imports succeed, config settings exist, jaeger and OTEL_ENABLED found in docker-compose.yml.

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && uv lock --check` | 0 | ✅ pass | 1000ms |
| 2 | `cd backend && .venv/bin/python -c "from opentelemetry import trace; from opentelemetry.sdk.trace import TracerProvider; print('OK')"` | 0 | ✅ pass | 500ms |
| 3 | `cd backend && .venv/bin/python -c "from app.config import settings; assert hasattr(settings, 'otel_enabled'); print('OK')"` | 0 | ✅ pass | 500ms |
| 4 | `grep -q 'jaeger' docker-compose.yml` | 0 | ✅ pass | 50ms |
| 5 | `grep -q 'OTEL_ENABLED' docker-compose.yml` | 0 | ✅ pass | 50ms |

## Deviations

None — initial edit ordering required a second pass for OTEL env vars but no functional change.

## Known Issues

None.

## Files Created/Modified

- `backend/pyproject.toml`
- `backend/uv.lock`
- `backend/app/config.py`
- `docker-compose.yml`
