# S04: Docker Permissions + Model Loading Diagnosis — Research

**Researched:** 2026-04-05
**Depth:** Light-to-targeted (stale data confirmed, Docker constraints well-understood)

---

## Summary

Two separate issues, both simpler than feared:

1. **Model loading (business-planning):** Confirmed stale data — NOT a pipeline bug. The model was installed 2026-03-23 from an older archive that only had 2 NodeShapes (EisenhowerMatrix + EisenhowerItem). The current archive has 33 NodeShapes across 1665 triples. The install pipeline is mechanically correct. Fix: uninstall and reinstall the model.

2. **Docker permissions:** The current Dockerfile + docker-compose work correctly on fresh volumes. `/app/data` is `chown`ed to `sempkm:sempkm` in the image layer, and Docker initializes fresh named volumes from the image. The backend has no entrypoint script — adding one improves robustness (ensures subdirectories exist, runs Alembic migrations). The `security_opt: no-new-privileges` + `cap_drop: ALL` constraints mean gosu/su-exec is NOT viable — the entrypoint must run as `sempkm`.

---

## Requirement Ownership

No active requirements are owned by this slice.

---

## Model Loading — Detailed Findings

### Evidence: Stale Install

Live triplestore query confirmed:
- **Installed shapes:** Only 2 (`EisenhowerMatrixShape`, `EisenhowerItemShape`) — 154 total triples in the shapes graph
- **Current archive:** 33 NodeShapes, 67 `@graph` entries, 1665 triples, 72KB JSON-LD file
- **Installed description:** Only mentions "Eisenhower Matrix for urgency×importance prioritization"
- **Current description:** Mentions 15+ frameworks (Eisenhower, BMC, OKR, Decision Matrix, SWOT, BCG, Ansoff, Stakeholder, Risk, Porter, PESTLE, Balanced Scorecard, RACI, Value Chain, Lean Canvas)
- **Install date:** 2026-03-23T05:44:50 — predates the current expanded archive

### Pipeline Verification

The SPARQL INSERT DATA for the full 33-shape archive is ~206KB. This is well within:
- RDF4J default POST size limits (Tomcat default 2MB)
- httpx timeout of 30s (TIMEOUT_DEFAULT in `backend/app/config.py:103`)
- RDF4J transaction update uses raw `application/sparql-update` content body (not form-encoded), so the `maxParameterCount: 1000` Tomcat limit does not apply

The transaction flow is sound: `begin_transaction()` → `transaction_update()` per graph → `commit_transaction()`, with rollback on error.

### Uninstall Blocker

The `remove()` method in `ModelService` (models.py:754) checks for user data before allowing removal. Since the installed model created seed data (EisenhowerItem instances exist in `urn:sempkm:current`), the standard uninstall will be BLOCKED with:
> "Cannot remove model 'business-planning': user data exists for types: ..."

**Options for the planner:**
- **Option A (recommended):** Delete the seed data objects first (via the existing `bulk_delete_objects` endpoint or a direct SPARQL DELETE), then uninstall, then reinstall.
- **Option B:** Add a `--force` flag to the remove endpoint that skips the user data check. More work, less safe.
- **Option C:** Directly clear the model's named graphs via SPARQL (`CLEAR GRAPH <urn:sempkm:model:business-planning:shapes>` etc), then unregister, then reinstall. Bypasses the service layer but is a one-time diagnostic fix.

### Key Files

| File | Role |
|------|------|
| `backend/app/services/models.py:350` | `install()` — 12-step pipeline |
| `backend/app/services/models.py:754` | `remove()` — with user-data guard |
| `backend/app/services/models.py:281` | `_build_insert_data_sparql()` — triple serialization |
| `backend/app/models/loader.py:50` | `load_jsonld_file()` — rdflib JSON-LD parser |
| `backend/app/models/loader.py:137` | `load_archive()` — loads all model graphs |
| `backend/app/triplestore/client.py:95` | `transaction_update()` — raw SPARQL body via PUT |
| `models/business-planning/manifest.yaml` | Current manifest with 33+ icon entries |
| `models/business-planning/shapes/business-planning.jsonld` | 72KB shapes file, 33 NodeShapes |

---

## Docker Permissions — Detailed Findings

### Current State

- **Backend Dockerfile:** Creates `sempkm` user (uid 1000, gid 999), `chown -R sempkm:sempkm /app/data`, then `USER sempkm`
- **No entrypoint script** — goes directly to `CMD ["uvicorn", ...]`
- **docker-compose:** `security_opt: no-new-privileges:true` + `cap_drop: ALL` on the API service
- **Volume:** `sempkm_data` named volume mounted at `/app/data`
- **Runtime user:** `sempkm` (uid 1000) confirmed via `docker exec ... id`

### Fresh Volume Behavior

On `docker compose down -v && docker compose up --build -d`:
1. Named volume `sempkm_data` is created fresh (empty)
2. Docker populates it from the image layer `/app/data` — owned by sempkm ✓
3. App starts as sempkm, creates `sempkm.db`, `.secret-key`, `.setup-token` — all correct ownership ✓
4. No permission errors expected

### Existing Volume — Root-Owned Files

Current state shows root-owned files only in:
- `/app/data/.federation-endpoints.json` — created by a process that ran as root
- `/app/data/imports/` tree — Obsidian import files created by a root process

These root-owned files don't block normal operation because:
- `.federation-endpoints.json` is read-only for the app
- `imports/` is only read during import processing

### gosu Is Not Viable

`no-new-privileges:true` prevents setuid/setgid binaries from gaining privileges. gosu uses setuid, so it would fail. The entrypoint must run as the `sempkm` user (which it already does via `USER sempkm`).

### Recommended Entrypoint

Add a `backend/docker-entrypoint.sh` that runs as sempkm:
1. `mkdir -p /app/data/apps /app/data/imports` — ensure subdirectories exist
2. Run Alembic migrations: `alembic upgrade head` — currently not automated
3. `exec "$@"` — hand off to uvicorn CMD

This is a robustness improvement, not a critical fix. The pattern already exists in `frontend/docker-entrypoint.sh`.

### Key Files

| File | Role |
|------|------|
| `backend/Dockerfile` | Creates user, sets perms, no entrypoint |
| `docker-compose.yml` | security_opt, cap_drop, volume mounts |
| `frontend/docker-entrypoint.sh` | Reference pattern for backend entrypoint |
| `backend/app/config.py:30-35` | Data directory paths (database_url, secret_key_path) |

---

## Recommendation

### Task Decomposition for Planner

**Task 1 — Backend Docker Entrypoint** (~15 min)
- Create `backend/docker-entrypoint.sh` following frontend pattern
- Ensure subdirectories, run alembic migrate, exec CMD
- Update `backend/Dockerfile` to add ENTRYPOINT before CMD
- Files: `backend/docker-entrypoint.sh` (new), `backend/Dockerfile`
- Verify: `docker compose build api && docker compose up -d api` succeeds, healthcheck passes

**Task 2 — Model Loading Diagnosis & Fix** (~20 min)
- Clear stale model data (SPARQL CLEAR GRAPH for shapes/ontology/views/rules graphs + unregister from models graph, or delete seed data then use the remove API)
- Reinstall business-planning model via the install endpoint
- Verify: SPARQL query `SELECT (COUNT(?s) AS ?count) WHERE { GRAPH <urn:sempkm:model:business-planning:shapes> { ?s a sh:NodeShape } }` returns 33
- Files: No code changes expected — this is a diagnostic/operational task. If pipeline issues found, `backend/app/services/models.py`

**Task 3 — Fresh Volume Integration Test** (~10 min)
- `docker compose down -v && docker compose up --build -d`
- Wait for healthchecks
- Verify all services healthy
- Install business-planning model, verify 33 shapes
- Files: None (verification only)

### Seam Notes

Tasks 1 and 2 are independent — they can be done in parallel. Task 3 depends on Task 1 completing (tests the entrypoint). Task 3 also tests the model install on fresh data (no stale data).

---

## Skill Discovery

No external skills needed — this is Docker/Docker Compose configuration and direct SPARQL/triplestore operations, all well-established in the codebase.

---

## Pitfalls

1. **Model uninstall user-data guard:** The standard `remove()` API will refuse to uninstall business-planning because seed data exists. The planner must account for this — either delete seed objects first, or use direct SPARQL to clear the model graphs.
2. **Alembic in entrypoint:** Adding `alembic upgrade head` to the entrypoint requires that alembic.ini and migrations/ are accessible at runtime. They are (COPY'd in Dockerfile). But the database might not exist yet on first run — alembic should handle this (SQLite creates on connect).
3. **security_opt constraint:** Do NOT attempt gosu/su-exec approaches. The entrypoint runs as sempkm. If permission issues occur on existing volumes, the user must manually fix ownership from the host.
