---
estimated_steps: 5
estimated_files: 30
skills_used:
  - review
  - code-optimizer
---

# T01: SPARQL injection triage — classify all f-string SPARQL modules (A03)

**Slice:** S01 — Injection, Access Control & Authentication Findings (A01, A03, A07)
**Milestone:** M042

## Description

Systematically analyze every backend module that constructs SPARQL queries via Python f-strings to determine which are exploitable injection vectors. The codebase has ~29 modules using f-string SPARQL patterns. For each, trace the interpolated variables back to their origin (HTTP request parameter, internal IRI, config value, system-generated) and classify the module's injection risk.

Also assess non-SPARQL injection vectors: Jinja2 template injection (is autoescaping on?), SQLAlchemy injection (any raw SQL?), and command injection (any subprocess/os.system calls?).

The output is an intermediate analysis document (`T01-SPARQL-TRIAGE.md`) that T02 will incorporate into the final S01-FINDINGS.md.

## Steps

1. **Enumerate all f-string SPARQL modules** — Run `rg -l 'f".*SELECT\|f".*INSERT\|f".*DELETE\|f".*PREFIX\|f".*CONSTRUCT\|f".*ASK\|f".*WHERE\|f".*DESCRIBE' backend/app/ --type py` and also `rg -l 'f".*<\{' backend/app/ --type py` to catch IRI interpolation patterns. Create the definitive list.

2. **Classify each module** — For each module in the list:
   - Find all f-string SPARQL lines with `rg -n 'f"' <file>` or `rg -n "f'" <file>`
   - Read the function containing each f-string to identify what variables are interpolated
   - Trace each variable: is it from an HTTP request parameter (`request.query_params`, `Query(...)`, path parameter, form data, JSON body)? Or from an internal service call, config, or system-generated value?
   - Classify as:
     - **confirmed-exploitable**: User-controlled HTTP input reaches f-string without sanitization
     - **likely-exploitable**: User input is 1-2 hops away (e.g., user-provided IRI stored and later used in query)
     - **safe**: Only internal/system values interpolated (ontology IRIs, config, UUIDs generated server-side)
   - For confirmed/likely modules, write a concrete exploit scenario (e.g., "A user could submit `object_iri` value containing `> } INSERT DATA { ... }` to break out of the SELECT and inject arbitrary triples")

3. **Assess the `scope_to_current_graph` defense** — Review `backend/app/sparql/client.py` for bypass vectors. Check: Can a user-submitted query with crafted FROM clauses bypass the graph scoping? Does `check_member_query_safety()` have evasion paths (e.g., mixed case, Unicode normalization, nested quotes)?

4. **Assess non-SPARQL injection vectors:**
   - Jinja2: Check if `autoescape` is enabled globally in the Jinja2Blocks setup in `main.py`. Grep for `|safe` filter usage in templates and `Markup()` in Python that might bypass autoescaping.
   - SQLAlchemy: Grep for `text()`, `execute(f"`, raw SQL patterns that bypass ORM parameterization.
   - Command injection: Grep for `subprocess`, `os.system`, `os.popen`, `eval(`, `exec(` in backend code.

5. **Write T01-SPARQL-TRIAGE.md** — Structure: (a) methodology, (b) classification table with all modules, (c) detailed findings for confirmed/likely-exploitable modules with exploit scenarios, (d) `scope_to_current_graph` defense analysis, (e) non-SPARQL injection assessment. Each finding must have: severity, affected files, exploit scenario, remediation.

## Must-Haves

- [ ] Every f-string SPARQL module classified (confirmed-exploitable / likely-exploitable / safe) with reasoning
- [ ] Exploit scenarios for every confirmed or likely-exploitable module
- [ ] `scope_to_current_graph` bypass analysis
- [ ] `check_member_query_safety` evasion analysis
- [ ] Non-SPARQL injection assessment (Jinja2, SQLAlchemy, command injection)
- [ ] Each finding has severity, affected files, exploit scenario, remediation

## Verification

- `test -f .gsd/milestones/M042/slices/S01/tasks/T01-SPARQL-TRIAGE.md`
- `grep -c "confirmed-exploitable\|likely-exploitable\|safe" .gsd/milestones/M042/slices/S01/tasks/T01-SPARQL-TRIAGE.md` returns >= 29

## Inputs

- `backend/app/views/service.py` — largest f-string SPARQL surface (101 f-strings)
- `backend/app/views/router.py` — view endpoint SPARQL (31 f-strings)
- `backend/app/browser/objects.py` — object CRUD SPARQL (25 f-strings)
- `backend/app/sparql/router.py` — user-facing SPARQL endpoint, enrichment queries
- `backend/app/sparql/client.py` — graph scoping and member safety check
- `backend/app/sparql/query_service.py` — saved query service (148 f-strings)
- `backend/app/ontology/service.py` — ontology SPARQL (95 f-strings)
- `backend/app/services/ops_log.py` — ops log SPARQL (60 f-strings)
- `backend/app/admin/router.py` — admin SPARQL (57 f-strings)
- `backend/app/services/models.py` — model service SPARQL (61 f-strings)
- `backend/app/models/registry.py` — model registry SPARQL (19 f-strings)
- `backend/app/browser/comments.py` — comment SPARQL (16 f-strings)
- `backend/app/browser/search.py` — search SPARQL (3 f-strings)
- `backend/app/browser/apps.py` — app commands SPARQL (20 f-strings)
- `backend/app/events/store.py` — event store SPARQL (12 f-strings)
- `backend/app/events/query.py` — event query SPARQL (13 f-strings)
- `backend/app/services/validation.py` — validation SPARQL (12 f-strings)
- `backend/app/services/shapes.py` — shapes SPARQL (4 f-strings)
- `backend/app/services/webhooks.py` — webhook SPARQL (12 f-strings)
- `backend/app/services/icons.py` — icon SPARQL (1 f-string)
- `backend/app/inference/service.py` — inference SPARQL (15 f-strings)
- `backend/app/rdf_import/executor.py` — RDF import SPARQL (6 f-strings)
- `backend/app/vfs/strategies.py` — VFS strategy SPARQL (21 f-strings)
- `backend/app/vfs/mount_router.py` — VFS mount SPARQL (41 f-strings)
- `backend/app/vfs/mount_collections.py` — VFS collections SPARQL (19 f-strings)
- `backend/app/sparql/mirror.py` — mirror SPARQL (21 f-strings)
- `backend/app/api/ai.py` — AI router SPARQL (32 f-strings)
- `backend/app/task_templates/service.py` — task templates SPARQL (12 f-strings)
- `backend/app/sparql/migrate_queries.py` — query migration SPARQL (25 f-strings)
- `backend/app/api/router.py` — API surface SPARQL (context-query endpoint)
- `backend/app/main.py` — Jinja2 autoescape configuration
- `backend/app/triplestore/client.py` — triplestore client (lower-level query execution)

## Expected Output

- `.gsd/milestones/M042/slices/S01/tasks/T01-SPARQL-TRIAGE.md` — SPARQL injection classification table + detailed findings + non-SPARQL injection assessment
