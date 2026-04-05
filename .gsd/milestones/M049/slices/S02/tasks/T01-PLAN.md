---
estimated_steps: 60
estimated_files: 4
skills_used: []
---

# T01: Add OTel dependencies, Jaeger Docker service, and config settings

Pure dependency and configuration task — no Python application logic. Adds the 6 OpenTelemetry packages to pyproject.toml (all from the same 0.61b0 release train), regenerates the lock file, adds Jaeger v2 to docker-compose.yml, and adds otel_enabled/otel_exporter_endpoint settings to the config class.

## Steps

1. Add these packages to the `[project.dependencies]` section of `backend/pyproject.toml`:
   - `opentelemetry-api~=1.31`
   - `opentelemetry-sdk~=1.31`
   - `opentelemetry-exporter-otlp-proto-http~=1.31`
   - `opentelemetry-instrumentation-fastapi~=0.52b0`
   - `opentelemetry-instrumentation-httpx~=0.52b0`
   - `opentelemetry-semantic-conventions~=0.52b0`
   Note: Version pins may need adjustment based on what's available in PyPI. Use `uv lock` output to determine the correct compatible versions. The key constraint is all `opentelemetry-instrumentation-*` packages must be from the same release train, and all core packages from the matching release.

2. Run `cd backend && uv lock` to regenerate the lockfile. If version conflicts arise, adjust pins to the latest compatible set.

3. Run `cd backend && uv sync` to install into the local venv.

4. Add two new fields to the `Settings` class in `backend/app/config.py`:
   ```python
   # OpenTelemetry tracing (optional — app works without Jaeger)
   otel_enabled: bool = False
   otel_exporter_endpoint: str = "http://jaeger:4318/v1/traces"
   ```
   Place them after the existing `posthog_*` settings block (or at the end of the class before `model_config`).

5. Add Jaeger v2 service to `docker-compose.yml`:
   ```yaml
   jaeger:
     image: jaegertracing/jaeger:2
     ports:
       - "16686:16686"   # Jaeger UI
       - "4318:4318"     # OTLP HTTP receiver
     environment:
       MEMORY_MAX_TRACES: "10000"
     mem_limit: 512m
     networks:
       - sempkm
   ```
   Place it after the `frontend` service, before the `networks:` section.

6. Add OTEL environment variables to the `api` service's `environment` block in `docker-compose.yml`:
   ```yaml
   OTEL_ENABLED: ${OTEL_ENABLED:-true}
   OTEL_EXPORTER_ENDPOINT: ${OTEL_EXPORTER_ENDPOINT:-http://jaeger:4318/v1/traces}
   ```

7. Verify: `cd backend && .venv/bin/python -c "from opentelemetry import trace; from opentelemetry.sdk.trace import TracerProvider; print('OK')"` succeeds.

## Must-Haves

- [ ] All 6 OTel packages in pyproject.toml with compatible version pins
- [ ] `uv lock` succeeds without conflicts
- [ ] `otel_enabled` and `otel_exporter_endpoint` fields in Settings class
- [ ] Jaeger v2 service in docker-compose.yml on sempkm network
- [ ] OTEL_ENABLED and OTEL_EXPORTER_ENDPOINT env vars on api service

## Verification

- `cd backend && uv lock --check` exits 0 (lockfile consistent)
- `cd backend && .venv/bin/python -c "from opentelemetry import trace; from opentelemetry.sdk.trace import TracerProvider; print('OK')"` prints OK
- `cd backend && .venv/bin/python -c "from app.config import settings; assert hasattr(settings, 'otel_enabled'); print('OK')"` prints OK
- `grep -q 'jaeger' docker-compose.yml` exits 0
- `grep -q 'OTEL_ENABLED' docker-compose.yml` exits 0

## Inputs

- `backend/pyproject.toml` — existing dependency list to extend
- `backend/app/config.py` — Settings class to add fields to
- `docker-compose.yml` — service definitions to extend

## Expected Output

- `backend/pyproject.toml` — updated with 6 OTel packages
- `backend/uv.lock` — regenerated lockfile
- `backend/app/config.py` — Settings class with otel_enabled and otel_exporter_endpoint
- `docker-compose.yml` — Jaeger service + OTEL env vars on api service

## Inputs

- `backend/pyproject.toml`
- `backend/app/config.py`
- `docker-compose.yml`

## Expected Output

- `backend/pyproject.toml`
- `backend/uv.lock`
- `backend/app/config.py`
- `docker-compose.yml`

## Verification

cd backend && uv lock --check && .venv/bin/python -c "from opentelemetry import trace; from opentelemetry.sdk.trace import TracerProvider; print('OK')" && .venv/bin/python -c "from app.config import settings; assert hasattr(settings, 'otel_enabled'); print('OK')"
