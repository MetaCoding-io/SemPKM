# T01: SPARQL Injection Triage — Module Classification

## Methodology

Every backend Python module using f-string SPARQL construction was identified via `rg -l 'f".*SELECT|f".*INSERT|...'` and `rg -l 'f".*<\{'`. For each module:

1. All f-string SPARQL lines were located
2. Interpolated variables were traced to their origin (HTTP request parameter, service call, config value, system-generated)
3. Any existing sanitization (`_validate_iri`, `_sparql_escape`) was noted
4. Module was classified as **confirmed-exploitable**, **likely-exploitable**, or **safe**
5. For confirmed/likely modules, a concrete exploit scenario was documented

### Input Categories

- **HTTP direct**: Value comes from `Query(...)`, path parameter, `Form(...)`, `request.json()`, `request.form()`
- **HTTP indirect**: Value was stored from HTTP input (e.g., in SQL), then retrieved and used in SPARQL
- **Internal IRI**: Value comes from triplestore query results, ontology constants, or generated URNs
- **Config/system**: Value from `settings.*`, environment, or server-generated UUIDs

### Sanitization Functions

| Function | Location | Escapes | Missing |
|---|---|---|---|
| `_validate_iri()` | `browser/_helpers.py` | Blocks `<>"\{}\n\r\t `, requires scheme, rejects unknown schemes | Comprehensive for IRI-in-angle-brackets pattern |
| `_sparql_escape()` | `browser/search.py`, `browser/workspace.py` | `\ → \\`, `" → \"`, `\n → \n` | `\r`, `\t` not escaped |
| `_escape_sparql()` | `vfs/mount_service.py` | `\ → \\`, `" → \"`, `\n → \n`, `\r → \r` | Most complete variant |
| `_sparql_escape_str()` | `api/router.py`, `api/ai.py` | `\ → \\`, `" → \"`, `\n → \n` | `\r`, `\t` not escaped |

---

## SPARQL Injection Classification Table

| # | Module | Classification | f-string Count | Input Source | Sanitization | Reasoning |
|---|--------|---------------|----------------|-------------|-------------|-----------|
| 1 | `sparql/router.py` | **confirmed-exploitable** | ~10 | HTTP direct (user SPARQL query) | `check_member_query_safety` + `scope_to_current_graph` | User submits arbitrary SPARQL via `/api/sparql` POST/GET. The `_enrich_sparql_results` function uses f-string VALUES clause with IRIs from triplestore results (safe). But the primary endpoint passes raw user query to triplestore — the safety check only blocks FROM/GRAPH/SERVICE for members; owners can query any graph. |
| 2 | `views/service.py` | **confirmed-exploitable** | ~101 | HTTP indirect (`type` from query string, `scope_filter` from saved query) | None on `type_iri` | `type_iri` from HTTP `?type=` query parameter reaches `<{type_iri}>` in SPARQL via `build_dynamic_query()` → `_build_default_select()` / `_build_shacl_select()` without `_validate_iri()`. |
| 3 | `views/router.py` | **confirmed-exploitable** | ~31 | HTTP direct (`type` query param, `scope_query` UUID) | `_validate_iri` only on calendar move endpoint | `type` from query string → `type_iri` → `_detect_date_fields(type_iri)`, `_detect_geo_fields(type_iri)`, `_detect_status_field(type_iri)` — all use `<{type_iri}>` in SPARQL. |
| 4 | `browser/objects.py` | **safe** | ~25 | HTTP direct (path param `object_iri`) | `_validate_iri()` on all entry points | Every endpoint validates decoded IRI before SPARQL interpolation. |
| 5 | `browser/search.py` | **confirmed-exploitable** | ~3 | HTTP direct (`type` query param, `q` query param) | `_validate_iri()` on `type`; `_sparql_escape()` on `q` | `type` param validated ✓. `q` in `object_search` uses `_sparql_escape` but injected into REGEX pattern `"{escaped}"` — incomplete escape (`\r`, `\t` missing, and SPARQL REGEX metacharacters not escaped). `q` in `tag_suggestions` properly escaped into string literal. |
| 6 | `browser/comments.py` | **safe** | ~16 | HTTP direct (path param `object_iri`) | `_validate_iri()` on all entry points | All decoded IRIs validated before SPARQL. Comment text goes through `_sparql_escape`. |
| 7 | `browser/apps.py` | **confirmed-exploitable** | ~20 | HTTP direct (`iri` query param) | None | `iri` from `Query(...)` goes directly into `<{iri}>` SPARQL without `_validate_iri()`. |
| 8 | `browser/events.py` | **likely-exploitable** | ~5 | HTTP direct (`q` query param) | Partial: `q.replace('"', '\\"')` only | `q` parameter escapes only `"` — missing `\` escape allows backslash injection. Inside `FILTER(CONTAINS(LCASE(STR(?iri)), LCASE("...")))`. Severity reduced because it's a read-only SELECT. |
| 9 | `browser/workspace.py` | **safe** | ~15 | HTTP direct (path params, tag values) | `_validate_iri()` for IRIs, `_sparql_escape()` for text | Consistently applies appropriate sanitization. |
| 10 | `browser/favorites.py` | **likely-exploitable** | ~2 | HTTP indirect (stored `object_iri` from `Form(...)`) | None on storage; None on retrieval | `object_iri` from form data stored in SQL without `_validate_iri()`, then used in `<{iri}>` SPARQL VALUES clause. Two-hop: user stores malicious IRI → later query uses it. |
| 11 | `admin/router.py` | **safe** | ~57 | HTTP direct (`model_id` path param) | None on `model_id` but requires owner role | `model_id` interpolated into `urn:sempkm:model:{model_id}:ontology` graph names. Path params are URL-segment-safe. Owner-only access limits exposure. |
| 12 | `ontology/service.py` | **safe** | ~95 | Internal IRI (from model manifests, triplestore) | N/A | All interpolated values are ontology graph IRIs from manifest loading or triplestore results. Not reachable from HTTP input. |
| 13 | `services/models.py` | **safe** | ~61 | Internal IRI (model_id from manifests, triplestore) | N/A | Model service operates on model registry data. `model_id` comes from on-disk manifest YAML, not HTTP. |
| 14 | `services/ops_log.py` | **safe** | ~60 | Internal IRI (system-generated UUIDs, config) | N/A | Ops log entries use server-generated IRIs. User-visible ops log browsing uses pre-built queries. |
| 15 | `services/validation.py` | **safe** | ~12 | Internal IRI (from triplestore query results) | N/A | Validation service queries use IRIs from shapes/ontology graphs. |
| 16 | `services/shapes.py` | **safe** | ~4 | Internal IRI (type IRI from triplestore) | N/A | Shapes service queries use class IRIs from ontology. |
| 17 | `services/webhooks.py` | **safe** | ~12 | Internal IRI (system-generated webhook IRIs) | N/A | Webhook CRUD uses `urn:sempkm:webhook:{uuid}` IRIs generated server-side. |
| 18 | `services/icons.py` | **safe** | ~1 | Internal IRI (type IRI from ontology) | N/A | Single query uses type IRI from ontology service. |
| 19 | `models/registry.py` | **safe** | ~19 | Internal IRI (model graph IRIs) | N/A | Registry queries use `urn:sempkm:model:*` graph names from manifests. |
| 20 | `events/store.py` | **safe** | ~12 | Internal IRI (system-generated event IRIs) | N/A | Event store uses `urn:sempkm:event:{uuid}` generated server-side. |
| 21 | `events/query.py` | **safe** | ~13 | Internal IRI (event IRIs from triplestore) | N/A | Event query service uses pre-built queries with system IRIs. |
| 22 | `inference/service.py` | **safe** | ~15 | Internal IRI (ontology/rule IRIs) | N/A | Inference uses ontology graph IRIs from model manifests. |
| 23 | `rdf_import/executor.py` | **safe** | ~6 | Internal IRI (import graph IRIs) | N/A | RDF import uses generated graph names. Input RDF files are parsed by rdflib, not string-interpolated. |
| 24 | `vfs/strategies.py` | **safe** | ~21 | Internal IRI (mount/type IRIs from triplestore) | N/A | VFS strategies use IRIs loaded from mount definitions in triplestore. |
| 25 | `vfs/mount_router.py` | **confirmed-exploitable** | ~41 | HTTP direct (JSON body: `group_by_property`, `date_property`, `scope_query`, `type_filter[]`) | `_escape_sparql` for string literals only | IRI fields (`group_by_property`, `date_property`, `scope_query`, `type_filter`) from JSON body inserted into `<{...}>` SPARQL without `_validate_iri()`. String fields (`name`, `path`, `strategy`, `filename_template`) properly escaped. |
| 26 | `vfs/mount_collections.py` | **safe** | ~19 | Internal IRI (mount IRIs from triplestore) | N/A | Collection queries use mount IRIs loaded from triplestore. |
| 27 | `sparql/mirror.py` | **safe** | ~21 | Internal IRI (mirror config, generated graph IRIs) | N/A | Mirror service uses internally generated mirror graph IRIs. |
| 28 | `sparql/query_service.py` | **safe** | ~148 | Internal IRI (user_id UUIDs, query_id UUIDs) | N/A | Saved query CRUD uses `urn:sempkm:query:{uuid}` and `urn:sempkm:user:{uuid}` — server-generated UUIDs. |
| 29 | `sparql/migrate_queries.py` | **safe** | ~25 | Internal IRI (migration-only, one-time admin) | N/A | Query migration uses IRIs from SQL tables (pre-existing data). Admin-only, not ongoing exposure. |
| 30 | `api/ai.py` | **likely-exploitable** | ~32 | HTTP direct (`body.url`, `body.title`, `body.claims`) | `_sparql_escape_str` for URL string; FTS for text | `body.url` in suggest-relationships and context-query uses `_sparql_escape_str` in FILTER(STR(?val) = "...") — adequate for string literal context. Claim IRIs in VALUES clauses come from FTS/triplestore results (safe). LLM-generated SPARQL in copilot not directly executed by ai.py. |
| 31 | `api/router.py` | **likely-exploitable** | ~5 | HTTP direct (`body.url`, `body.title`, `body.keywords`) | `_sparql_escape_str` for URL | Same pattern as ai.py: URL goes into FILTER string literal with escape. `_sparql_escape_str` missing `\r`/`\t` but not exploitable in FILTER(STR()="") context. |
| 32 | `task_templates/service.py` | **safe** | ~12 | Internal IRI (template IRIs from triplestore) | N/A | Task template service uses `urn:sempkm:task:*` IRIs from triplestore. |
| 33 | `sparql/client.py` | **safe** | ~5 | Internal (graph scoping constants) | N/A | `scope_to_current_graph` injects hardcoded graph IRIs (`urn:sempkm:current`, etc.). |

---

## Detailed Findings

### F-A03-01: SPARQL Injection via `type` Query Parameter in Views

**Severity:** High
**OWASP:** A03:2021 — Injection
**Classification:** confirmed-exploitable
**Affected Files:** `backend/app/views/router.py`, `backend/app/views/service.py`

**Data Flow:**
```
HTTP GET /browser/views/generic/table?type=PAYLOAD
  → views/router.py generic_view() → type_iri = type (no validation)
  → views/service.py build_dynamic_query(type_iri, ...)
  → _build_default_select() → f"  ?s rdf:type <{type_iri}> .\n"
  → scope_to_current_graph() → triplestore.query()
```

**Exploit Scenario:**
A user crafts the `type` parameter to break out of the angle-bracket IRI and inject additional SPARQL:
```
GET /browser/views/generic/table?type=x>%20.%20%3Fs%20%3Fp%20%3Fo%20}%20%23
```
Decoded: `type=x> . ?s ?p ?o } #`

The injected payload becomes:
```sparql
?s rdf:type <x> . ?s ?p ?o } #> .
```
This closes the WHERE block and comments out the rest, potentially extracting all triples. The `scope_to_current_graph` defense injects `FROM <urn:sempkm:current>` which limits exposure to the current graph, but an attacker can still read all data within that graph.

More severe: an attacker could potentially use CONSTRUCT or sub-SELECT patterns if the query structure allows it.

**Remediation:**
Add `_validate_iri(type_iri)` check in `generic_view()` and all view endpoints that accept a `type` query parameter, before passing to `build_dynamic_query()`. Approximately 10-15 endpoints in views/router.py need this guard.

---

### F-A03-02: SPARQL Injection via `iri` Query Parameter in Apps

**Severity:** High
**OWASP:** A03:2021 — Injection
**Classification:** confirmed-exploitable
**Affected Files:** `backend/app/browser/apps.py`

**Data Flow:**
```
HTTP GET /browser/apps/right-pane-sections?iri=PAYLOAD
  → apps.py right_pane_sections() → iri (no validation)
  → f"SELECT ?type WHERE {{ <{iri}> a ?type }}"
  → triplestore.query()
```

**Exploit Scenario:**
```
GET /browser/apps/right-pane-sections?iri=x>%20.%20%3Fs%20%3Fp%20%3Fo%20}%20%23
```
Identical breakout pattern as F-A03-01. The query has no `FROM` scoping, so depending on triplestore configuration, may access all graphs.

**Remediation:**
Add `_validate_iri(iri)` check before SPARQL construction. The query should also be scoped via `scope_to_current_graph()`.

---

### F-A03-03: SPARQL Injection via VFS Mount IRI Fields

**Severity:** High
**OWASP:** A03:2021 — Injection
**Classification:** confirmed-exploitable
**Affected Files:** `backend/app/vfs/mount_router.py`

**Data Flow:**
```
HTTP POST /browser/vfs/mounts (JSON body)
  → body.group_by_property, body.date_property, body.scope_query, body.type_filter[]
  → f'<{mount_iri}> <{GROUP_BY_PROPERTY}> <{body.group_by_property}>'
  → INSERT DATA { GRAPH <...> { ... } }
  → triplestore.update()
```

**Exploit Scenario:**
A user creates a mount with a crafted `group_by_property`:
```json
{
  "name": "test",
  "path": "/test",
  "strategy": "flat",
  "group_by_property": "x> . } } ; INSERT DATA { GRAPH <urn:sempkm:current> { <urn:evil> <urn:p> <urn:o> } } #"
}
```
This breaks out of the INSERT DATA triple and injects arbitrary triples into any graph. This is a **write** injection — the attacker can modify the knowledge graph.

**Remediation:**
Apply `_validate_iri()` to all IRI-typed fields in the mount creation/update body: `group_by_property`, `date_property`, `scope_query`, `type_filter[]`.

---

### F-A03-04: Stored SPARQL Injection via Favorites

**Severity:** Medium
**OWASP:** A03:2021 — Injection
**Classification:** likely-exploitable
**Affected Files:** `backend/app/browser/favorites.py`

**Data Flow:**
```
HTTP POST /browser/favorites (Form: object_iri=PAYLOAD)
  → favorites.py toggle_favorite() → stored in SQL UserFavorite table (no validation)

Later:
HTTP GET /browser/ (workspace load)
  → favorites.py favorites_section()
  → object_iris = [f.object_iri for f in favorites]
  → values_clause = " ".join(f"(<{iri}>)" for iri in object_iris)
  → SPARQL SELECT with VALUES clause
```

**Exploit Scenario:**
An attacker stores a malicious IRI via the favorites form, then the workspace page load triggers the injection every time. The VALUES clause injection:
```
object_iri = x>) } . ?s ?p ?o } #
```
would break the SPARQL VALUES block.

**Remediation:**
Add `_validate_iri(object_iri)` in `toggle_favorite()` before SQL storage.

---

### F-A03-05: Incomplete Query Parameter Escaping in Events Browser

**Severity:** Low
**OWASP:** A03:2021 — Injection
**Classification:** likely-exploitable
**Affected Files:** `backend/app/browser/events.py`

**Data Flow:**
```
HTTP GET /browser/events/object-browser?q=PAYLOAD
  → q_escaped = q.strip().replace('"', '\\"')
  → f'FILTER(CONTAINS(LCASE(STR(?iri)), LCASE("{q_escaped}")))'
```

**Exploit Scenario:**
The escape only handles `"` — a `\` character is not escaped, allowing:
```
q = \" )) . ?s ?p ?o } #
```
The `\"` becomes `\\"` after escape (backslash + escaped quote), which in SPARQL means literal backslash followed by end-of-string, breaking out of the string context.

Practical impact is low: this is a read-only SELECT on event IRIs.

**Remediation:**
Replace the inline escape with `_sparql_escape()` which handles `\`, `"`, and `\n`.

---

### F-A03-06: Incomplete SPARQL String Escaping Across Multiple Modules

**Severity:** Low
**OWASP:** A03:2021 — Injection
**Classification:** likely-exploitable
**Affected Files:** `backend/app/browser/search.py`, `backend/app/api/router.py`, `backend/app/api/ai.py`

**Description:**
Three different `_sparql_escape` / `_sparql_escape_str` functions exist across the codebase, with inconsistent escape coverage:

| Function | `\` | `"` | `\n` | `\r` | `\t` |
|---|---|---|---|---|---|
| `_sparql_escape` (search.py, workspace.py) | ✓ | ✓ | ✓ | ✗ | ✗ |
| `_sparql_escape_str` (api/router.py, api/ai.py) | ✓ | ✓ | ✓ | ✗ | ✗ |
| `_escape_sparql` (vfs/mount_service.py) | ✓ | ✓ | ✓ | ✓ | ✗ |

None escape SPARQL-specific characters like `'` (single quote, used in SPARQL string literals with `'...'` syntax) or Unicode escapes.

In practice, the missing `\r`/`\t` escapes have minimal exploit potential since these values go into FILTER string comparisons. However, inconsistency suggests no centralized sanitization strategy.

**Remediation:**
Consolidate all escape functions into a single `sparql_escape_string()` in `sparql/client.py` that handles `\`, `"`, `'`, `\n`, `\r`, `\t`. Import it everywhere.

---

### F-A03-07: User-Submitted SPARQL via `/api/sparql` (By Design)

**Severity:** Medium (for member role), Info (for owner role)
**OWASP:** A03:2021 — Injection
**Classification:** confirmed-exploitable (by design)
**Affected Files:** `backend/app/sparql/router.py`, `backend/app/sparql/client.py`

**Description:**
The `/api/sparql` endpoint is intentionally a SPARQL query interface — users submit arbitrary SPARQL. This is by design for the SPARQL console feature. Defenses:

1. **Role gating:** Guests blocked. Members restricted (no FROM/GRAPH/SERVICE). Owners unrestricted.
2. **Graph scoping:** `scope_to_current_graph()` injects `FROM <urn:sempkm:current>` before the outer WHERE.
3. **Keyword blocking:** `check_member_query_safety()` rejects FROM, GRAPH, SERVICE keywords (case-insensitive, comment-aware, string-literal-aware).

**Risk:** The endpoint only supports read queries (SELECT, CONSTRUCT, DESCRIBE, ASK) — not SPARQL UPDATE (INSERT, DELETE). This is enforced at the triplestore level (RDF4J query endpoint vs update endpoint). Even an owner-role user cannot write data through this endpoint.

**Potential Concerns:**
- Owners can query ALL graphs including event graphs, federation graphs, etc.
- No query complexity limits (expensive CARTESIAN JOINs could cause DoS)
- No result size limits (could exfiltrate large datasets)

**Remediation:**
- Add query timeout at triplestore level
- Consider result size pagination
- Document the intentional exposure in security policy

---

## `scope_to_current_graph` Defense Analysis

### How It Works
`scope_to_current_graph()` finds the outer WHERE keyword (at brace depth 0) and injects `FROM <urn:sempkm:current>` before it. The brace-depth algorithm handles nested SERVICE, OPTIONAL, and sub-select blocks correctly.

### Bypass Vectors Analyzed

| Vector | Status | Detail |
|---|---|---|
| Crafted FROM clause | **Defended** | Checks for existing FROM/GRAPH → skips injection → but user gets their FROM instead of the safe one. For user-submitted SPARQL, `check_member_query_safety` blocks this for members. For f-string injection, FROM in the type_iri would need `>` which `_validate_iri` blocks (where applied). |
| No WHERE keyword | **Partial gap** | DESCRIBE/ASK queries without WHERE fall through unchanged. Comment at line 230: "return as-is". These queries may access all graphs. |
| Unicode/encoding tricks | **Defended** | The function operates on the Python string directly. SPARQL doesn't have C-style unicode escapes outside strings. |
| String literal hiding | **Defended** | `_strip_sparql_strings()` blanks string interiors and comments before keyword detection. |
| Nested WHERE | **Defended** | Brace-depth counting only injects at depth 0. |

### `check_member_query_safety` Evasion Analysis

| Vector | Status | Detail |
|---|---|---|
| Mixed case (fRoM) | **Defended** | `.upper()` normalization applied |
| Inside string literal | **Defended** | `_strip_sparql_strings()` blanks strings first |
| Inside comment | **Defended** | `_strip_sparql_strings()` blanks comments |
| Unicode normalization | **Defended** | SPARQL keywords must be ASCII; `.upper()` is ASCII-safe |
| `LOAD` SPARQL command | **Not checked** | LOAD is a SPARQL UPDATE command not checked by the safety function. Not exploitable because the `/api/sparql` endpoint uses the query (not update) triplestore endpoint. |
| `CLEAR`/`DROP` commands | **Not checked** | Same as LOAD — not exploitable because query endpoint. |
| `VALUES` with external IRI | **Allowed** | Members can use `VALUES ?g { <urn:sempkm:event:xyz> }` but this doesn't bypass FROM scoping. |
| Property path `^` to traverse | **Allowed** | Members can use property paths, but FROM scoping limits the traversal graph. |

**Overall Assessment:** The member safety check is sound against its design goal (preventing graph escape). The main gap is that it doesn't apply to f-string-injected SPARQL — only to user-submitted SPARQL at the `/api/sparql` endpoint.

---

## Non-SPARQL Injection Assessment

### Jinja2 Template Injection

**Classification:** safe
**Affected Files:** `backend/app/main.py` (Jinja2Blocks setup)

**Analysis:**
- Jinja2Blocks extends Starlette's `Jinja2Templates` which defaults `autoescape=True`
- No `|safe` filter usage found in any template (`rg -rn '\|safe' backend/app/templates/` — zero results)
- No `Markup()` calls found in Python code (`rg -n 'Markup\(' backend/app/` — zero results)
- Templates use `{{ variable }}` syntax which is auto-escaped

**Result:** XSS via template injection is not a current risk.

### SQLAlchemy Injection

**Classification:** safe
**Affected Files:** All SQLAlchemy models and queries

**Analysis:**
- No raw SQL `text()` queries with user input found
- No `execute(f"...")` patterns found
- All database queries use SQLAlchemy ORM (`.where()`, `.filter()`, `.select()`)
- `sa.text()` usage limited to column defaults (e.g., `server_default=sa.text("0")`) — not user input
- The one use of `select(User).where(User.role != "guest")` is parameterized by ORM

**Result:** SQL injection is not a current risk.

### Command Injection

**Classification:** safe
**Affected Files:** `backend/app/apps/manager.py`

**Analysis:**
- `subprocess` usage found only in `AppManager` which uses `create_subprocess_exec()` with argument list (not `shell=True`)
- No `os.system()`, `os.popen()` found
- No `eval()` or `exec()` with user input found
- App subprocess arguments (`app_dir`, `socket_path`, `platform_url`, `token`) come from server-side config and generated values, not HTTP input

**Result:** Command injection is not a current risk.

---

## Summary

| Classification | Count | Modules |
|---|---|---|
| **confirmed-exploitable** | 4 | `sparql/router.py` (by design), `views/service.py`, `views/router.py`, `vfs/mount_router.py`, `browser/apps.py` |
| **likely-exploitable** | 4 | `browser/events.py`, `browser/favorites.py`, `api/ai.py`, `api/router.py` |
| **safe** | 25 | `browser/objects.py`, `browser/comments.py`, `browser/search.py`, `browser/workspace.py`, `admin/router.py`, `ontology/service.py`, `services/models.py`, `services/ops_log.py`, `services/validation.py`, `services/shapes.py`, `services/webhooks.py`, `services/icons.py`, `models/registry.py`, `events/store.py`, `events/query.py`, `inference/service.py`, `rdf_import/executor.py`, `vfs/strategies.py`, `vfs/mount_collections.py`, `sparql/mirror.py`, `sparql/query_service.py`, `sparql/migrate_queries.py`, `sparql/client.py`, `task_templates/service.py`, `browser/search.py` |

### Top Remediation Priorities

1. **Add `_validate_iri()` to views/router.py `type` parameter** — Highest impact, broadest attack surface (~10 endpoints)
2. **Add `_validate_iri()` to browser/apps.py `iri` parameter** — Direct injection, no graph scoping
3. **Add `_validate_iri()` to VFS mount IRI fields** — Write injection (can modify knowledge graph)
4. **Add `_validate_iri()` to favorites `object_iri`** — Stored injection
5. **Consolidate escape functions** — Eliminate inconsistency, ensure complete coverage
6. **Add `_validate_iri()` or escape to events.py `q` parameter** — Incomplete escaping
