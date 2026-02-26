# Codebase Concerns

**Analysis Date:** 2026-02-25

## Tech Debt

**SMTP email delivery not implemented:**
- Issue: Magic link auth advertises SMTP support but actual email sending is a stub. When `smtp_host` is configured, the code detects it and returns a "link has been sent" message, but nothing is sent.
- Files: `backend/app/auth/router.py:132` (`# TODO: send email with token via SMTP`)
- Impact: Production deployments with SMTP configured silently discard magic links; users cannot log in. This blocks real multi-user cloud deployment.
- Fix approach: Implement `aiosmtplib` or `smtplib` email sending with the SMTP credentials from `settings`.

**Cookie `secure=False` hardcoded for production:**
- Issue: Session cookie is always set with `secure=False`, making it transmittable over plain HTTP.
- Files: `backend/app/auth/router.py:47`
- Impact: Credentials can be intercepted on non-HTTPS connections in production.
- Fix approach: Make `secure` configurable via a `settings.cookie_secure: bool = True` env var, defaulting to `True` for production.

**`Base.metadata.create_all` used instead of Alembic migrations at startup:**
- Issue: `main.py` calls `conn.run_sync(Base.metadata.create_all)` on startup instead of running `alembic upgrade head`. Alembic migrations exist (`001`, `002`) but are not applied automatically.
- Files: `backend/app/main.py:138`, `backend/migrations/versions/`
- Impact: On existing deployments where the DB was created by `create_all`, later migration scripts that add columns will never run. New tables added via migrations only won't be created by `create_all`.
- Fix approach: Add `alembic upgrade head` call in the lifespan startup, or integrate migration runner before `create_all`.

**Label cache not invalidated after browser-route writes:**
- Issue: `browser/router.py` creates `EventStore` instances directly (not via DI) and never calls `label_service.invalidate()` after commits. Only `commands/router.py` does not call invalidate either — `invalidate()` method exists on `LabelService` but is never called from any write path.
- Files: `backend/app/browser/router.py:697`, `backend/app/browser/router.py:1013`, `backend/app/browser/router.py:1120`, `backend/app/services/labels.py:128`
- Impact: After renaming an object, the old label persists in cache for up to 300 seconds (TTL). UI shows stale labels in nav tree and relations panel after saves.
- Fix approach: Call `label_service.invalidate(event_result.affected_iris)` after every `event_store.commit()`.

**`EventStore` instantiated ad-hoc instead of via DI in browser router:**
- Issue: `browser/router.py` constructs `EventStore(client)` locally in 4 route handlers rather than injecting from `app.state.event_store`.
- Files: `backend/app/browser/router.py:697`, `backend/app/browser/router.py:1013`, `backend/app/browser/router.py:1120`, `backend/app/browser/router.py:1298`
- Impact: Subtle inconsistency — if `EventStore` gains stateful behaviour (connection pool, metrics, etc.), browser routes bypass it.
- Fix approach: Add `get_event_store` dependency to `app/dependencies.py` and inject via `Depends`.

**`ViewSpecService.get_all_view_specs()` called on every sub-method:**
- Issue: `get_view_specs_for_type()` and `get_view_spec_by_iri()` both call `get_all_view_specs()` internally, which issues two SPARQL queries (model list + view spec list) on every call. Multiple view-related endpoints on a single page load will each repeat this.
- Files: `backend/app/views/service.py:141`, `backend/app/views/service.py:153`
- Impact: Excess SPARQL traffic, latency on pages that call these methods.
- Fix approach: Add a short TTL cache on `get_all_view_specs()` (or pass specs as parameter to callers).

**`source_model` attribution always empty with multiple installed models:**
- Issue: `ViewSpec.source_model` is set to `model_ids[0]` only when exactly one model is installed; empty string otherwise.
- Files: `backend/app/views/service.py:135`
- Impact: Cannot attribute view specs to their source model when multiple models are installed. Feature-incomplete.
- Fix approach: Fetch the model graph IRI per spec during query and match it back to a model ID.

**`datetime.now()` used (timezone-naive) in browser routes:**
- Issue: `browser/router.py` uses `datetime.now().isoformat()` for `dcterms:modified` timestamps, producing naive local-time strings.
- Files: `backend/app/browser/router.py:688`, `backend/app/browser/router.py:1111`
- Impact: Inconsistent timestamps in triplestore — `EventStore` uses `datetime.now(timezone.utc)` for event timestamps, but property modifications use naive local time.
- Fix approach: Replace with `datetime.now(timezone.utc).isoformat()`.

**Alembic migrations not connected to application startup:**
- Issue: `pyproject.toml` lists `alembic>=1.18` as a dependency and migration files exist, but `main.py` uses `Base.metadata.create_all` instead of running migrations. There is no documentation or script showing when to run `alembic upgrade head`.
- Files: `backend/app/main.py:138`, `backend/migrations/`
- Impact: Schema drift risk when new migrations are added.
- Fix approach: Add a startup migration runner or a documented deployment step.

---

## Known Bugs

**Magic link token logged to application log even when SMTP is configured:**
- Symptoms: `logger.info("Magic link token for %s: %s", body.email, token)` runs unconditionally before the SMTP branch check. In production with SMTP configured, the plaintext token appears in logs.
- Files: `backend/app/auth/router.py:129`
- Trigger: Any `/api/auth/magic-link` request when `smtp_host` is configured.
- Workaround: Deploy without configuring `smtp_host` (uses local token-return flow instead).

**Event detail user lookup: N+1 SQL query per event:**
- Symptoms: Event log endpoint issues one `SELECT` per unique user IRI in the event list inside a Python loop.
- Files: `backend/app/browser/router.py:1209-1218`
- Trigger: Viewing the event log with multiple authors.
- Workaround: Small user counts make this unnoticeable.

---

## Security Considerations

**CORS configured with `allow_origins=["*"]` + `allow_credentials=True`:**
- Risk: The combination of wildcard origin and `allow_credentials=True` is a security misconfiguration. Modern browsers block credentialed requests to wildcard origins (CORS spec), but this configuration is still incorrect and may cause unexpected behaviour or CORS bypass on misconfigured proxies.
- Files: `backend/app/main.py:268-270`
- Current mitigation: Session is cookie-based with `httponly=True`; the primary token cannot be stolen by JS.
- Recommendations: Restrict `allow_origins` to known trusted origins (frontend URL) in production, or remove `allow_credentials=True` if cross-origin JS API access is not needed.

**No rate limiting on authentication endpoints:**
- Risk: `/api/auth/magic-link` and `/api/auth/verify` have no rate limiting. An attacker can enumerate valid email addresses (via timing) or brute-force tokens.
- Files: `backend/app/auth/router.py`
- Current mitigation: Magic link tokens expire after 10 minutes (`max_age=600`).
- Recommendations: Add per-IP rate limiting (e.g. `slowapi` / `fastapi-limiter`) on `/api/auth/magic-link` and `/api/auth/verify`.

**IRI interpolation into SPARQL without validation:**
- Risk: User-controlled IRIs from URL path segments (`{object_iri:path}`, `{type_iri:path}`) are URL-decoded and interpolated directly into SPARQL using Python f-strings (e.g., `<{decoded_iri}>`). While IRIs placed inside `<>` delimiters are syntactically contained, a malformed IRI containing `>` could escape the angle-bracket context.
- Files: `backend/app/browser/router.py:413`, `backend/app/browser/router.py:468`, `backend/app/browser/router.py:601`, `backend/app/browser/router.py:733`, `backend/app/browser/router.py:844`, `backend/app/browser/router.py:1332`
- Current mitigation: Auth guard (all browser routes require `get_current_user`); only authenticated users can trigger these paths.
- Recommendations: Add IRI validation (e.g. check that decoded IRI is a valid absolute URI before interpolation) to prevent malformed IRI injection.

**Filter text user input interpolated into SPARQL REGEX with minimal escaping:**
- Risk: `filter_text` from query parameters is escaped for only `\` and `"` before insertion into `FILTER(REGEX(...))`. Other SPARQL special characters may allow regex injection or unexpected query behaviour.
- Files: `backend/app/views/service.py:227-230`, `backend/app/views/service.py:372-374`
- Current mitigation: Auth guard; authenticated users only.
- Recommendations: Use a more complete SPARQL string escaping function, or validate that `filter_text` is a plain search string.

**Default `base_namespace` uses `example.org`:**
- Risk: If an instance is deployed without overriding `BASE_NAMESPACE`, all created objects will have IRIs under `https://example.org/data/`. If `example.org` is ever dereferenced or the namespace is shared, IRI collisions occur.
- Files: `backend/app/config.py:15`
- Current mitigation: This is the development default; production deployments should set `BASE_NAMESPACE`.
- Recommendations: Document `BASE_NAMESPACE` configuration as a required step in deployment docs.

**Debug endpoints accessible to all authenticated users:**
- Risk: `/sparql` and `/commands` debug pages expose raw SPARQL console and command executor to all authenticated users (any role), not owner-only.
- Files: `backend/app/debug/router.py:12`, `backend/app/debug/router.py:20`
- Current mitigation: Users still must be authenticated; direct triplestore URL is not exposed.
- Recommendations: Add `Depends(require_role("owner"))` to debug endpoints, or guard behind a `settings.debug` flag.

---

## Performance Bottlenecks

**Browser router is a 1,371-line monolith:**
- Problem: `browser/router.py` handles settings, LLM config, workspace, nav tree, object CRUD, event log, lint, search, and more in one file. Each route handler is large and inline.
- Files: `backend/app/browser/router.py`
- Cause: Feature accretion over multiple development phases.
- Improvement path: Split into sub-routers by domain (settings, objects, events, search).

**`LabelService` TTL cache is process-local — not shared across workers:**
- Problem: The 300-second TTL `TTLCache` in `LabelService` is per-process. With multiple Uvicorn workers, each worker has its own cache; a write in worker A leaves stale labels in worker B's cache.
- Files: `backend/app/services/labels.py:37`
- Cause: In-process `cachetools.TTLCache` — acceptable for single-worker/single-process dev, fragile at scale.
- Improvement path: For multi-worker deployment, replace with Redis TTL cache, or accept the eventual-consistency degradation.

**`ViewSpecService` performs two sequential SPARQL queries for every view spec lookup:**
- Problem: `get_all_view_specs()` always runs a model-list SPARQL query followed by a view spec SPARQL query, even on a simple filtered lookup.
- Files: `backend/app/views/service.py:60-138`
- Cause: No caching layer on view spec data.
- Improvement path: Add a process-level TTL cache (5-10 minutes) on `get_all_view_specs()`.

**`TriplestoreClient` uses a single persistent `httpx.AsyncClient` with no connection pooling strategy:**
- Problem: A single `httpx.AsyncClient` is created at startup with `timeout=30.0`. Under high concurrency, all requests share this one client instance with its default connection pool limits.
- Files: `backend/app/triplestore/client.py:20`
- Cause: Simple singleton pattern.
- Improvement path: For high-load deployments, tune `httpx.Limits` (max connections) and consider separate clients for read vs write paths.

---

## Fragile Areas

**Alembic migration vs `create_all` co-existence:**
- Files: `backend/app/main.py:138`, `backend/migrations/versions/001_initial_auth_tables.py`, `backend/migrations/versions/002_user_settings.py`
- Why fragile: `create_all` creates tables from ORM models directly. If a migration adds a column that differs from the ORM model, or if the ORM model diverges, `create_all` and Alembic become inconsistent.
- Safe modification: Always update both the ORM model (`backend/app/auth/models.py`) and add a new migration file. Never rely solely on `create_all` for schema updates.
- Test coverage: No unit tests for schema migration logic.

**`validation/report.py` uses `hash()` as fallback for validation IRI:**
- Files: `backend/app/validation/report.py:155`
- Why fragile: Python `hash()` is not stable across processes (Python 3.3+ hash randomization). The fallback path `f"urn:sempkm:validation:{hash(self.event_iri)}"` will produce different IRIs in different processes for the same event, making validation reports unreachable.
- Safe modification: Always use the primary path (`urn:sempkm:event:` prefix extraction). The fallback should raise an error rather than produce an unstable IRI.
- Test coverage: Not tested.

**`scope_to_current_graph()` uses regex on SPARQL text — can be fooled:**
- Files: `backend/app/sparql/client.py`
- Why fragile: Graph scoping is injected by searching for `FROM` and `GRAPH` keywords in query text. A query with these words inside string literals or comments will incorrectly be treated as already scoped and not injected.
- Safe modification: Do not add FROM clauses with keywords inside literals. The current code works for well-formed simple queries.
- Test coverage: Only covered by e2e tests indirectly.

**`_MODELS_DIR = "/app/models"` hardcoded in browser router:**
- Files: `backend/app/browser/router.py:40`
- Why fragile: The models directory path is hardcoded as a module-level constant. If the Docker mount changes, or if running outside Docker, `SettingsService` and `IconService` silently fail to find models.
- Safe modification: Use `settings` or an environment variable for the models directory path.
- Test coverage: No unit tests; covered by e2e only.

---

## Scaling Limits

**Single-tenant only (no namespace isolation between users):**
- Current capacity: One tenant/instance; all users share `urn:sempkm:current` state graph and `urn:sempkm:user:{uuid}` IRIs.
- Limit: Not multi-tenant; cannot host multiple independent workspaces in one deployment.
- Scaling path: Multi-tenant design would require per-tenant named graph prefixes and per-tenant auth context.

**SQLite default for `database_url`:**
- Current capacity: Suitable for single-user or small team local deployment.
- Limit: SQLite with `aiosqlite` does not support true concurrent writes; under write contention, queries serialize.
- Scaling path: Set `DATABASE_URL` to a PostgreSQL URL for multi-user production deployments.

---

## Dependencies at Risk

**No pinned versions in `pyproject.toml` — version floor only:**
- Risk: All dependencies specify `>=` version floors, not exact pins. A future `uv sync` or `pip install` may pull breaking minor/major versions of rdflib, pyshacl, SQLAlchemy, etc.
- Files: `backend/pyproject.toml`
- Impact: Silent breaking changes in CI or new developer setup.
- Migration plan: Pin versions in `pyproject.toml` or commit `uv.lock` to source control and respect it in Docker builds.

---

## Missing Critical Features

**SMTP email delivery (magic link + invitations):**
- Problem: The email delivery path for magic links and user invitations is a recognized stub (`# TODO: send email with token via SMTP`).
- Blocks: Real multi-user cloud deployment where users cannot receive login tokens via the terminal log.

**No session cleanup job (expired sessions accumulate):**
- Problem: Session rows in the `sessions` table are never deleted when they expire naturally; only explicit logout deletes them. Long-lived deployments will accumulate thousands of stale session rows.
- Files: `backend/app/auth/service.py`
- Blocks: Database hygiene at scale.

---

## Test Coverage Gaps

**Zero backend unit or integration tests:**
- What's not tested: All Python business logic — auth service, event store, SPARQL serialization, label resolution, validation, commands, views service.
- Files: `backend/app/` (entire directory)
- Risk: Regressions in SPARQL generation, auth token logic, or command handlers go undetected until e2e tests catch them — or don't.
- Priority: High

**SPARQL injection / escaping logic:**
- What's not tested: `_serialize_rdf_term()` in `events/store.py`, `_escape_sparql()` in `services/webhooks.py`, `filter_text` REGEX injection in `views/service.py`, and `scope_to_current_graph()` in `sparql/client.py`.
- Files: `backend/app/events/store.py`, `backend/app/services/webhooks.py`, `backend/app/views/service.py`, `backend/app/sparql/client.py`
- Risk: A crafted literal or IRI in user data could produce malformed SPARQL, corrupting the triplestore or leaking data.
- Priority: High

**LLM proxy endpoint (SSE streaming):**
- What's not tested: `browser/router.py` `/llm/chat/stream` SSE endpoint — streaming, error handling, timeout behavior.
- Files: `backend/app/browser/router.py:263`
- Risk: Streaming errors silently swallowed; malformed LLM responses expose internal error strings to browser.
- Priority: Medium

**Validation report IRI stability (hash fallback):**
- What's not tested: The `hash()` fallback path in `validation/report.py:155` and its cross-process instability.
- Files: `backend/app/validation/report.py:155`
- Risk: Validation reports become unreachable across restarts if event IRI doesn't match the `urn:sempkm:event:` prefix pattern.
- Priority: Medium

**E2E setup wizard (5 known failing tests):**
- What's not tested reliably: `e2e/tests/00-setup/01-setup-wizard.spec.ts` fails on non-fresh Docker stacks because the setup wizard only runs on first boot.
- Files: `e2e/tests/00-setup/01-setup-wizard.spec.ts`
- Risk: Fresh-instance setup flow is not continuously verified in standard CI.
- Priority: Medium (infrastructure concern, not application bug)

---

*Concerns audit: 2026-02-25*
