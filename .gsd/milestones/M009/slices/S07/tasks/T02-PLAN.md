---
estimated_steps: 4
estimated_files: 2
---

# T02: Implement uninstall data cleanup in AppManager

**Slice:** S07 — Test App, E2E Tests & Integration Proof
**Milestone:** M009

## Description

The success criterion "Uninstall 'app + data' removes all app-prefixed IRIs from `urn:sempkm:current`" requires triplestore cleanup that `AppManager.uninstall()` doesn't yet perform. The method stores `self._triplestore_client` but never uses it. Add a `clean_data` parameter that, when True, executes SPARQL DELETE/CLEAR queries to remove all app-owned data before deleting the DB row. Also update the admin uninstall endpoint to accept and pass through the `clean_data` form parameter.

## Steps

1. **Add `clean_data` parameter to `AppManager.uninstall()`** in `backend/app/apps/manager.py`:
   - Change signature: `async def uninstall(self, app_id: str, clean_data: bool = False) -> None:`
   - After `await self.stop(app_id)` and before the DB deletion block, add a conditional block:
     ```python
     if clean_data and self._triplestore_client:
         logger.info("Cleaning triplestore data for app %s", app_id)
         try:
             # Delete triples where subject has app IRI prefix
             await self._triplestore_client.update(
                 f'DELETE WHERE {{ GRAPH <urn:sempkm:current> {{ ?s ?p ?o . FILTER(STRSTARTS(STR(?s), "urn:sempkm:app:{app_id}:")) }} }}'
             )
             # Delete triples where object has app IRI prefix
             await self._triplestore_client.update(
                 f'DELETE WHERE {{ GRAPH <urn:sempkm:current> {{ ?s ?p ?o . FILTER(STRSTARTS(STR(?o), "urn:sempkm:app:{app_id}:")) }} }}'
             )
             # Clear app state graph
             await self._triplestore_client.update(
                 f'CLEAR GRAPH <urn:sempkm:app:{app_id}:state>'
             )
             logger.info("Triplestore data cleaned for app %s", app_id)
         except Exception as exc:
             logger.warning("Failed to clean triplestore data for app %s: %s", app_id, exc)
     ```
   - Important: The triplestore cleanup is best-effort (wrapped in try/except). If it fails, uninstall still proceeds. This matches the existing error-handling pattern in uninstall (socket cleanup, data dir cleanup are also best-effort).
   - The triplestore client's `update()` method is the async SPARQL UPDATE method on the existing `TriplestoreClient` class already injected via `self._triplestore_client`.

2. **Check the triplestore client API** — The `_triplestore_client` is set in `AppManager.__init__()`. Verify it has an `update()` method for SPARQL UPDATE queries. If the method is named differently (e.g., `execute_update`, `sparql_update`), use the correct name. Look at `backend/app/triplestore/` for the actual client API.

3. **Update the admin uninstall endpoint** in `backend/app/apps/admin_router.py`:
   - Current signature at line ~285:
     ```python
     @app_admin_router.post("/admin/apps/{app_id}/uninstall")
     async def app_uninstall(
         request: Request,
         app_id: str,
         user: User = Depends(require_role("owner")),
     ):
     ```
   - Add `clean_data: bool = Form(False)` parameter:
     ```python
     @app_admin_router.post("/admin/apps/{app_id}/uninstall")
     async def app_uninstall(
         request: Request,
         app_id: str,
         user: User = Depends(require_role("owner")),
         clean_data: bool = Form(False),
     ):
     ```
   - Add `from fastapi import Form` to the imports if not already present.
   - Pass to manager: `await app_manager.uninstall(app_id, clean_data=clean_data)`
   - Update the log message to include clean_data: `logger.info("App %s uninstalled (by user %s, clean_data=%s)", app_id, user.id, clean_data)`

4. **Verify syntax** — Run ast.parse on both modified files.

## Must-Haves

- [ ] `AppManager.uninstall()` accepts `clean_data: bool = False` parameter
- [ ] When `clean_data=True`, three SPARQL queries execute: DELETE subject-prefix, DELETE object-prefix, CLEAR state graph
- [ ] Triplestore cleanup is best-effort (try/except, logged at WARNING on failure)
- [ ] Triplestore cleanup happens BEFORE DB row deletion (so it uses app metadata if needed)
- [ ] Admin uninstall endpoint accepts `clean_data: bool = Form(False)` and passes it through
- [ ] Both files pass `python -c "import ast; ast.parse(...)"`

## Verification

- `python -c "import ast; ast.parse(open('backend/app/apps/manager.py').read())"` — syntax OK
- `python -c "import ast; ast.parse(open('backend/app/apps/admin_router.py').read())"` — syntax OK
- `grep -c "clean_data" backend/app/apps/manager.py` — returns ≥3 (parameter + conditional + SPARQL block)
- `grep -c "clean_data" backend/app/apps/admin_router.py` — returns ≥2 (parameter + pass-through)
- `grep "STRSTARTS" backend/app/apps/manager.py` — returns 2 lines (subject + object cleanup)
- `grep "CLEAR GRAPH" backend/app/apps/manager.py` — returns 1 line

## Inputs

- `backend/app/apps/manager.py` — Current `uninstall()` method at line ~311. Has `self._triplestore_client` stored at `__init__` line ~74.
- `backend/app/apps/admin_router.py` — Current uninstall endpoint at line ~285. Already imports `Depends`, `Request`. May or may not import `Form`.
- The triplestore client's SPARQL UPDATE method needs to be discovered — check `backend/app/triplestore/` for the method name (likely `update()` or `execute_update()`).

## Expected Output

- `backend/app/apps/manager.py` — `uninstall()` with `clean_data` parameter and SPARQL cleanup block
- `backend/app/apps/admin_router.py` — `app_uninstall()` with `clean_data: bool = Form(False)` parameter

## Observability Impact

- **New log signals:** `app.apps.manager` logger emits INFO `"Cleaning triplestore data for app %s"` and `"Triplestore data cleaned for app %s"` on success; WARNING `"Failed to clean triplestore data for app %s: %s"` on failure.
- **Admin endpoint logging:** `app_uninstall` now logs `clean_data` value alongside user id — visible in `docker compose logs api`.
- **Inspection:** After uninstall with `clean_data=True`, query the triplestore directly: `SELECT * WHERE { GRAPH <urn:sempkm:current> { ?s ?p ?o . FILTER(STRSTARTS(STR(?s), "urn:sempkm:app:{app_id}:")) } }` should return zero results.
- **Failure state:** If triplestore cleanup fails, WARNING log appears but uninstall still completes — orphaned triples remain in `urn:sempkm:current` and `urn:sempkm:app:{app_id}:state` graph persists.
