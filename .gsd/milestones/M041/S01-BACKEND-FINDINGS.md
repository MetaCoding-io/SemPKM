# S01: Backend Code Quality Audit — Findings

**Scope:** `backend/app/` — 233 Python files, 60,069 LOC
**Date:** 2026-03-23

---

## Summary Statistics

| Metric | Count |
|--------|-------|
| Total files | 233 |
| Total LOC | 60,069 |
| Modules >300 LOC | 63 (27%) |
| Modules >500 LOC | 30 (13%) |
| Modules >1000 LOC | 9 (4%) |
| Functions >50 lines | 280 |
| Functions >100 lines | 63 |
| Functions >200 lines | 13 |
| Functions >500 lines | 1 |

---

## Module Structure

### Finding MS-01: `views/service.py` is the #1 god module (3,663 LOC, 56 functions, 2 classes)

**Severity:** Critical
**Effort:** High (multi-session refactor)
**Location:** `backend/app/views/service.py:91-3495`
**Detection:** `wc -l backend/app/views/service.py` → 3663; `python3 -c "import ast; tree=ast.parse(open('backend/app/views/service.py').read()); print(sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))))"` → 56

`ViewSpecService` is a single class spanning 3,400+ lines with 46 methods. It handles 12 distinct renderer types (table, cards, graph, calendar, map, kanban, quadrant, BMC, OKR, decision-matrix, timeline, plus generic), each with `_build_*_select()`, `execute_*_query()`, and `_detect_*()` method groups. Every new renderer adds ~200 lines to this already-massive class.

**Decomposition recommendation:** Extract each renderer into a dedicated module under `views/renderers/`:
- `views/renderers/table.py` — `_build_default_select`, `_build_shacl_select`, `execute_table_query`
- `views/renderers/cards.py` — `execute_cards_query` (342 lines alone)
- `views/renderers/calendar.py` — `_detect_date_fields`, `_build_calendar_select`, `execute_calendar_query`, `execute_merged_calendar_query`, `_expand_rrule`
- `views/renderers/graph.py` — `_build_graph_query`, `execute_graph_query`, `expand_neighbors`, `_parse_graph_results`, `_get_model_node_colors`
- `views/renderers/kanban.py` — `_detect_status_field`, `_build_kanban_select`, `execute_kanban_query`
- `views/renderers/map.py` — `_detect_geo_fields`, `_build_map_select`, `execute_map_query`
- `views/renderers/quadrant.py` — `_detect_quadrant_axes`, `_build_quadrant_select`, `execute_quadrant_query`, `_quadrant_label`
- `views/renderers/bmc.py` — `_detect_bmc_sections`, `_build_bmc_select`, `execute_bmc_query`
- `views/renderers/okr.py` — `_detect_okr_structure`, `_build_okr_select`, `execute_okr_query`
- `views/renderers/decision_matrix.py` — `_detect_decision_matrix_structure`, `_build_decision_matrix_select`, `execute_decision_matrix_query`
- `views/renderers/timeline.py` — `_build_timeline_select`, `execute_timeline_query`

This reduces `ViewSpecService` to a dispatcher (~300 LOC) that delegates to renderer modules. The `register_renderer()` infrastructure already exists (see KNOWLEDGE.md Pattern #6) but is dead code — activating it would formalize this split.

### Finding MS-02: `ontology/service.py` is a god module (2,181 LOC, 42 functions)

**Severity:** High
**Effort:** Medium
**Location:** `backend/app/ontology/service.py:184-2181`
**Detection:** `wc -l backend/app/ontology/service.py` → 2181; `python3 -c "import ast; tree=ast.parse(open('backend/app/ontology/service.py').read()); print(sum(1 for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))))"` → 42

`OntologyService` handles three distinct responsibility clusters:
1. **gist ontology management** — `ensure_gist_loaded()`, `_load_ttl_into_gist_graph()`, `get_gist_summary()`, etc.
2. **Read queries** — `get_root_classes()`, `get_class_detail()` (234 lines), `search_classes()`, `get_type_counts()`, `get_instances()`, `get_properties()`
3. **CRUD mutations** — `create_class()`, `delete_class()`, `create_property()`, `delete_property()`, `edit_class()`, `edit_property()`

**Decomposition recommendation:** Split into `OntologyQueryService` (read), `OntologyMutationService` (CRUD), and `GistService` (gist management). The mutation methods already cluster naturally around class vs property operations.

### Finding MS-03: `views/router.py` contains a 1,020-line function (1,930 LOC total)

**Severity:** Critical
**Effort:** High
**Location:** `backend/app/views/router.py:212` — `generic_view()` is 1,020 lines
**Detection:** `python3 -c "import ast; t=ast.parse(open('backend/app/views/router.py').read()); [print(f'{n.name} L{n.lineno}: {n.end_lineno-n.lineno+1} lines') for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.end_lineno-n.lineno>100]"`

`generic_view()` is a massive if/elif chain dispatching to different renderer-specific code paths. Each branch (~80-120 lines) builds context, calls the appropriate `ViewSpecService.execute_*_query()` method, and renders a template. This function single-handedly accounts for 53% of the file's LOC.

**Decomposition recommendation:** Each renderer branch should be a separate handler function. The dispatcher remains as a thin routing function that resolves renderer type → calls `_render_table()`, `_render_calendar()`, etc. This pairs naturally with the MS-01 renderer extraction.

### Finding MS-04: `admin/router.py` is monolithic (1,400 LOC, 31 functions)

**Severity:** Medium
**Effort:** Medium
**Location:** `backend/app/admin/router.py`
**Detection:** `wc -l backend/app/admin/router.py` → 1400

A single flat router file with 31 route handlers covering: models CRUD, API keys, webhooks, federation peers, SPARQL console, ops log, and entailment config. `_query_entailment_examples()` alone is 168 lines.

**Decomposition recommendation:** Split into sub-routers by admin section:
- `admin/models_router.py` — model install/uninstall/detail/entailment (~700 LOC)
- `admin/keys_router.py` — API keys CRUD (~70 LOC)
- `admin/webhooks_router.py` — webhook management (~120 LOC)
- `admin/federation_router.py` — federation peers (~100 LOC)

### Finding MS-05: `browser/objects.py` and `browser/workspace.py` are oversized (1,349 and 1,344 LOC)

**Severity:** Medium
**Effort:** Medium
**Location:** `backend/app/browser/objects.py`, `backend/app/browser/workspace.py`
**Detection:** `wc -l backend/app/browser/objects.py backend/app/browser/workspace.py`

`objects.py` (12 functions) is driven by a few very large route handlers: `get_object()` (286 lines), `get_relations()` (168 lines), `save_object()` (130 lines). `workspace.py` (22 functions) has `mount_children()` (221 lines) and `_handle_mount()` (178 lines).

These files are large but less urgently problematic than MS-01–MS-03 because they have fewer functions with clearer single-entity responsibility.

### Finding MS-06: 9 modules exceed 1,000 LOC

**Severity:** High
**Effort:** High (aggregate)
**Location:** Multiple files
**Detection:** `fd -e py . backend/app/ | xargs wc -l | sort -rn | awk '$1 > 1000 && $2 != "total"'`

| Module | LOC | Functions | God Module? |
|--------|-----|-----------|-------------|
| `views/service.py` | 3,663 | 56 | Yes — 12 renderer types in one class |
| `ontology/service.py` | 2,181 | 42 | Yes — gist + query + mutation |
| `views/router.py` | 1,930 | 18 | Yes — 1,020-line function |
| `admin/router.py` | 1,400 | 31 | Yes — 5 admin sections in one file |
| `browser/objects.py` | 1,349 | 12 | No — large handlers, single entity focus |
| `browser/workspace.py` | 1,344 | 22 | Yes — htmx fragments + tree rendering |
| `services/models.py` | 1,256 | 25 | Yes — install/analytics/manifest mixed |
| `api/ai.py` | 1,119 | 15 | No — many Pydantic schemas (15 classes) |
| `federation/service.py` | 1,090 | 25 | Yes — discovery + sync + signature mixed |

### Finding MS-07: `main.py` `lifespan()` is 415 lines

**Severity:** Medium
**Effort:** Low
**Location:** `backend/app/main.py:102`
**Detection:** `python3 -c "import ast; t=ast.parse(open('backend/app/main.py').read()); [print(f'{n.name}: {n.end_lineno-n.lineno+1} lines') for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name=='lifespan']"`

The `lifespan()` async context manager initializes all services, database connections, background tasks, and cleanup. This is a common pattern in FastAPI apps but at 415 lines it makes service initialization order hard to trace.

**Decomposition recommendation:** Extract initialization blocks into per-subsystem functions: `_init_database()`, `_init_triplestore()`, `_init_services()`, `_init_background_tasks()`. The lifespan function becomes a coordinator calling these in order.

### Finding MS-08: 280 functions exceed 50 lines, 63 exceed 100 lines

**Severity:** High
**Effort:** High (aggregate)
**Location:** Spread across 63 modules
**Detection:** `python3 -c "import ast,os; [print(f'{n.end_lineno-n.lineno+1:4d} lines  {fp}:{n.lineno}  {n.name}') for fp in (os.path.join(r,f) for r,_,fs in os.walk('backend/app') for f in fs if f.endswith('.py')) for n in ast.walk(ast.parse(open(fp).read())) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and getattr(n,'end_lineno',0)-n.lineno>49]" 2>/dev/null | sort -rn | head -20`

**Top offenders (>200 lines):**

| Function | File | Lines |
|----------|------|-------|
| `generic_view()` | `views/router.py:212` | 1,020 |
| `lifespan()` | `main.py:102` | 415 |
| `copilot_chat()` | `api/copilot.py:314` | 399 |
| `execute_cards_query()` | `views/service.py:676` | 342 |
| `execute()` | `notion/executor.py:68` | 323 |
| `get_object()` | `browser/objects.py:56` | 286 |
| `_do_scan()` | `obsidian/scanner.py:72` | 277 |
| `execute()` | `obsidian/executor.py:75` | 267 |
| `get_class_detail()` | `ontology/service.py:696` | 234 |
| `get_results()` | `lint/service.py:153` | 228 |
| `preview_mount()` | `vfs/mount_router.py:665` | 222 |
| `mount_children()` | `browser/workspace.py:967` | 221 |
| `get_type_analytics()` | `services/models.py:906` | 208 |

These functions typically mix data fetching, business logic, response formatting, and error handling in a single scope. Breaking them into a prepare → execute → format pipeline would improve testability and readability.

---

## Readability & Naming

### Finding RN-01: Naming conventions are consistently followed

**Severity:** None (positive finding)
**Detection:** `rg "^def [A-Z]" backend/app/` → 0 results; `rg "^class [a-z]" backend/app/` → 0 results (all matches were false positives from docstrings/comments)

All public functions use `snake_case`. All classes use `PascalCase`. Private methods consistently use `_` prefix. This is well-maintained across the entire codebase.

### Finding RN-02: Docstring coverage is excellent for public APIs (98%+)

**Severity:** None (positive finding)
**Detection:** Sampled 10 representative modules via AST analysis of public function docstrings.

| Module | Documented / Total | Coverage |
|--------|-------------------|----------|
| `views/service.py` | 25/25 | 100% |
| `ontology/service.py` | 22/22 | 100% |
| `admin/router.py` | 22/22 | 100% |
| `browser/objects.py` | 12/12 | 100% |
| `services/models.py` | 9/9 | 100% |
| `sparql/router.py` | 18/18 | 100% |
| `federation/service.py` | 13/13 | 100% |
| `main.py` | 2/4 | 50% |
| `apps/manager.py` | 11/11 | 100% |
| `copilot/service.py` | 4/4 | 100% |

### Finding RN-03: `main.py` is missing docstrings on 2 public functions

**Severity:** Low
**Effort:** Trivial
**Location:** `backend/app/main.py:225` (`shapes_loader`), `backend/app/main.py:237` (`on_validation_complete`)
**Detection:** `python3 -c "import ast; t=ast.parse(open('backend/app/main.py').read()); [print(f'L{n.lineno}: {n.name}') for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and not n.name.startswith('_') and not(n.body and isinstance(n.body[0],ast.Expr) and isinstance(n.body[0].value,ast.Constant))]"`

Two callback functions passed to service constructors lack docstrings. Minor, but these are integration points that benefit from describing their role.

### Finding RN-04: `api/copilot.py` `copilot_chat()` mixes SSE formatting, SPARQL extraction, and streaming in one 399-line function

**Severity:** High
**Effort:** Medium
**Location:** `backend/app/api/copilot.py:314`
**Detection:** `python3 -c "import ast; t=ast.parse(open('backend/app/api/copilot.py').read()); [print(f'{n.name}: {n.end_lineno-n.lineno+1} lines') for n in ast.walk(t) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.end_lineno-n.lineno>100]"`

This function handles: (1) message validation, (2) LLM provider selection, (3) SSE event stream generation, (4) inline SPARQL detection and extraction, (5) error formatting, and (6) conversation persistence. Each of these is a testable unit that's currently interleaved.

### Finding RN-05: `notion/executor.py` and `obsidian/executor.py` have monolithic `execute()` functions (323 and 267 lines)

**Severity:** Medium
**Effort:** Medium
**Location:** `backend/app/notion/executor.py:68`, `backend/app/obsidian/executor.py:75`
**Detection:** `python3 -c "import ast; [print(f'{fp}: {n.end_lineno-n.lineno+1} lines') for fp in ['backend/app/notion/executor.py','backend/app/obsidian/executor.py'] for n in ast.walk(ast.parse(open(fp).read())) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and n.name=='execute']"`

Both executors implement the full sync pipeline (connect → scan → diff → apply → report) in a single method. The pipeline stages are identifiable by inline comments but not extractable for testing or reuse.

---

## Error Handling

### Finding EH-01: 312 `except Exception` handlers — 70% catch-and-degrade, 8% silent

**Severity:** High
**Effort:** High (aggregate — many low-effort individual fixes)
**Location:** Across 50+ modules
**Detection:** `python3 -c "import ast,os; total=0; [total:=total+1 for r,_,fs in os.walk('backend/app') for f in fs if f.endswith('.py') for n in ast.walk(ast.parse(open(os.path.join(r,f)).read())) if isinstance(n,ast.ExceptHandler) and n.type and isinstance(n.type,ast.Name) and n.type.id=='Exception']; print(total)"`

| Category | Count | % | Risk |
|----------|-------|---|------|
| Logs + returns default value (graceful degradation) | 218 | 70% | Medium — hides root cause behind empty results |
| Silent `pass` (no log, no re-raise) | 24 | 8% | **High** — errors vanish completely |
| Silent `return` (no log, returns default) | 19 | 6% | **High** — errors vanish with misleading "empty" response |
| Logs + re-raises | 15 | 5% | Low — proper pattern |
| Other (mixed patterns) | 36 | 11% | Varies |

The dominant pattern is catch-and-degrade: catch `Exception`, log a warning with `exc_info=True`, and return an empty list/dict/zero. This is intentional for SPARQL query failures in view renderers (views/service.py has 37 of these) but problematic when it masks real bugs — a typo in a SPARQL template produces the same empty result as an actual empty dataset.

### Finding EH-02: 26 `except Exception: pass` blocks — completely silent failure

**Severity:** Critical
**Effort:** Low (add `logger.debug(..., exc_info=True)` to each)
**Location:** Multiple files (see table)
**Detection:** `python3 -c "import ast,os; [(print(f'{os.path.join(r,f)}:{n.lineno}')) for r,_,fs in os.walk('backend/app') for f in fs if f.endswith('.py') for n in ast.walk(ast.parse(open(os.path.join(r,f)).read())) if isinstance(n,ast.ExceptHandler) and n.type and isinstance(n.type,ast.Name) and n.type.id=='Exception' and len(n.body)==1 and isinstance(n.body[0],ast.Pass)]"`

| Module | Lines | Context |
|--------|-------|---------|
| `admin/router.py` | 770, 796, 822, 843, 882, 900, 923 | 7 entailment example SPARQL queries in `_query_entailment_examples()` — all silent |
| `services/models.py` | 406, 564, 944, 971 | Rollback, manifest scan, analytics queries |
| `events/query.py` | 444, 498 | Undo materialization queries |
| `events/store.py` | 225, 327 | Transaction rollback (best-effort — re-raises outer) |
| `canvas/router.py` | 478, 561 | Wikilink resolve, batch edges |
| `canvas/service.py` | 64, 72 | JSON parse of stored canvas data |
| `inference/service.py` | 668 | User override loading |
| `models/registry.py` | 285 | Model registry scan |
| `monitoring/middleware.py` | 39 | Session token extraction in error handler |
| `ontology/service.py` | 100 | Namespace prefix parsing |
| `services/icons.py` | 108 | Icon loading |
| `services/settings.py` | 93 | Settings iteration |
| `task_templates/router.py` | 162 | JSON body parsing |

**Risk classification:**
- **Acceptable (4):** `events/store.py` (225, 327) — rollback-then-reraise pattern; outer exception propagates.
- **Should add logging (15):** `admin/router.py` (7), `canvas/router.py` (2), `canvas/service.py` (2), `ontology/service.py` (1), `monitoring/middleware.py` (1), `task_templates/router.py` (1) — UI enrichment or parsing failures that are low-risk but invisible to debugging.
- **Dangerous (7):** `services/models.py` (4), `inference/service.py` (1), `models/registry.py` (1), `services/settings.py` (1) — silenced errors in core model installation, inference configuration, and settings loading can mask real failures.

### Finding EH-03: 19 `except Exception: return <default>` with no logging

**Severity:** High
**Effort:** Low
**Location:** Multiple files including `views/service.py:3211,3236,3464,3489`
**Detection:** `python3 -c "import ast,os; [(print(f'{os.path.join(r,f)}:{n.lineno}')) for r,_,fs in os.walk('backend/app') for f in fs if f.endswith('.py') for n in ast.walk(ast.parse(open(os.path.join(r,f)).read())) if isinstance(n,ast.ExceptHandler) and n.type and isinstance(n.type,ast.Name) and n.type.id=='Exception' and len(n.body)==1 and isinstance(n.body[0],ast.Return)]"`

These return empty defaults (`[]`, `{}`, `None`, `0`) without any trace that an error occurred. The caller sees an empty result indistinguishable from a genuine empty dataset. At minimum, add `logger.debug(..., exc_info=True)` so that enabling debug logging reveals the real error.

Notable locations in `views/service.py`:
- **L3211, L3236** — `_get_model_node_colors()` and layout queries silently return `[]` on any SPARQL failure, making graph views render with default colors instead of model-declared ones. No signal that the query failed.
- **L3464, L3489** — Color queries silently return `{}`, same issue.

### Finding EH-04: `views/service.py` has 37 broad `except Exception` handlers — most are catch-and-degrade

**Severity:** Medium
**Effort:** Medium
**Location:** `backend/app/views/service.py` (37 handlers, 33 logged, 4 silent)
**Detection:** `rg "except Exception" -c backend/app/views/service.py`

33 of 37 handlers follow a consistent pattern: catch Exception, `logger.warning("... failed for %s", iri, exc_info=True)`, return empty default. This is a deliberate "graceful degradation" strategy — a failed graph query returns an empty graph instead of a 500 error. The 4 unlogged handlers (EH-03) should match the same pattern for consistency.

**Recommendation:** The pattern itself is reasonable for a UI service where partial results are better than errors. However, none of these failures are visible to the user or admin. Consider: (1) incrementing a failure counter per renderer type for health monitoring, (2) returning a `warnings` field alongside data so the UI can show "some data may be missing."

### Finding EH-05: `admin/router.py` `_query_entailment_examples()` has 7 sequential silent catches

**Severity:** Medium
**Effort:** Trivial
**Location:** `backend/app/admin/router.py:770-923`
**Detection:** `rg "except Exception" -n backend/app/admin/router.py | grep -c "pass"`

Seven consecutive try/except blocks, each querying a different entailment type (owl:inverseOf, rdfs:subClassOf, rdfs:subPropertyOf, owl:TransitiveProperty, rdfs:domain/range, sh:rule, manifest defaults). Every one silently swallows `Exception` with `pass`. If the triplestore is down or a query is malformed, the admin page renders with zero entailment examples and no indication of why.

**Fix:** Add `logger.debug("entailment example query failed for %s: %s", entailment_type, e)` to each catch. Alternatively, refactor into a loop over entailment query specs with a single try/except wrapping each iteration.

### Finding EH-06: `inference/service.py` logs triplestore errors at `debug` level

**Severity:** Medium
**Effort:** Trivial
**Location:** `backend/app/inference/service.py:485,585`
**Detection:** `rg "logger\.debug.*error\|logger\.debug.*fail" -i -n backend/app/inference/service.py`

Two exception handlers catch triplestore failures (clearing inferred graphs, removing triples) and log them at `logger.debug()`. These are real operational errors — if the triplestore rejects a CLEAR GRAPH or DELETE, the inference state becomes inconsistent. At minimum these should be `logger.warning()`.

```python
# Line 485: "Clear inferred graph: %s" at debug — should be warning
except Exception as e:
    logger.debug("Clear inferred graph: %s", e)  # Should be warning

# Line 585: "Remove triple from inferred: %s" at debug — should be warning
except Exception as e:
    logger.debug("Remove triple from inferred: %s", e)  # Should be warning
```

---

## Logging

### Finding LG-01: 115 of 233 modules (49%) have loggers — substantial modules missing coverage

**Severity:** High
**Effort:** Medium
**Location:** See table below
**Detection:** `comm -23 <(fd -e py . backend/app/ | sort) <(rg "logger\s*=\s*|logging\.getLogger" -l backend/app/ 2>/dev/null | sort) | grep -v "__init__\.py" | grep -v "models\.py" | grep -v "schemas\.py" | xargs -I{} sh -c 'lines=$(wc -l < "{}"); [ "$lines" -gt 100 ] && echo "$lines {}"' | sort -rn`

118 modules (51%) have no logger. After filtering out `__init__.py`, models, and schemas (which typically don't need logging), 26 substantial modules (>100 LOC) lack logging:

| Module | LOC | Has except blocks? | Risk |
|--------|-----|---------------------|------|
| `vfs/mount_service.py` | 597 | No | **High** — largest unlogged module, handles mount CRUD |
| `lint/router.py` | 378 | 4 | **High** — validation results router with no error tracing |
| `vfs/collections.py` | 334 | No | Medium — collection SPARQL queries |
| `auth/service.py` | 333 | No | **Critical** — authentication logic with zero logging |
| `models/registry.py` | 326 | 1 (silent!) | **High** — model registration with a silent exception |
| `validation/report.py` | 308 | No | Medium — SHACL report parsing |
| `apps/manifest.py` | 298 | 2 | Medium |
| `vfs/write.py` | 253 | No | **High** — VFS write operations |
| `models/validator.py` | 251 | No | Medium |
| `canvas/service.py` | 250 | 4 (silent!) | **High** — silent exceptions with no logger to add to |
| `dependencies.py` | 249 | No | Medium — DI factory |
| `sparql/client.py` | 242 | No | **High** — SPARQL client with no error tracing |
| `federation/patch.py` | 183 | No | Medium |
| `models/router.py` | 181 | No | Medium |
| `models/loader.py` | 179 | No | Medium |
| `webid/service.py` | 160 | 1 | Medium |
| `auth/tokens.py` | 154 | 2 | Medium |
| `triplestore/client.py` | 151 | 1 | **High** — triplestore client wrapper |
| `services/settings.py` | 150 | 2 (silent!) | **High** — silent exceptions with no logger |
| `browser/pages.py` | 150 | No | Low |
| `inference/entailments.py` | 143 | No | Medium |
| `models/manifest.py` | 140 | 1 | Low |
| `services/llm.py` | 124 | 1 | Medium — LLM service selection |
| `commands/handlers/object_create.py` | 121 | No | Medium |
| `browser/tag_tree.py` | 121 | No | Low |
| `shell/router.py` | 116 | No | Medium |

The most critical gaps are `auth/service.py` (authentication with zero logging), `sparql/client.py` (SPARQL communication with no error tracing), `triplestore/client.py` (triplestore wrapper), and `vfs/mount_service.py` (597-line module with no logging).

### Finding LG-02: Zero f-string logging — %-style used consistently (positive finding)

**Severity:** None (positive finding)
**Detection:** `rg "logger\.\w+\(f\"" -c backend/app/ 2>/dev/null | awk -F: '{s+=$2} END {print s}'` → 0

All 743 logger calls use %-style format strings (`logger.warning("Failed for %s", var)`) rather than f-strings (`logger.warning(f"Failed for {var}")`). This is the correct pattern — %-style defers string formatting until the log message is actually emitted, avoiding computation when the log level is disabled.

### Finding LG-03: Zero `extra={}` structured logging — all log messages are unstructured strings

**Severity:** Medium
**Effort:** Medium (incremental adoption)
**Location:** All 743 logger calls across the codebase
**Detection:** `rg "extra\s*=" backend/app/ 2>/dev/null | grep "logger\."` → 0 results

No logger call in the codebase uses the `extra={}` parameter for structured logging. All error context is embedded in the format string: `logger.warning("Failed to query %s for %s", thing, iri)`. This makes log aggregation and filtering harder — you can't search for `{"object_iri": "urn:...", "operation": "delete"}` in a log management tool.

**Recommendation:** Prioritize structured logging for:
1. Error paths in API endpoints (include request method, path, user_id)
2. Triplestore operations (include query type, graph IRI, duration)
3. Federation operations (include peer URL, operation, status code)

### Finding LG-04: 105 `exc_info=True` usages — good exception chain preservation

**Severity:** None (positive finding)
**Detection:** `rg "exc_info=True" -c backend/app/ 2>/dev/null | awk -F: '{s+=$2} END {print s}'` → 105

About 14% of logger calls include `exc_info=True`, ensuring stack traces are captured for exception handlers. This is well-applied in the catch-and-degrade pattern across views, browser, and federation modules.

### Finding LG-05: `federation/signatures.py` logs signature verification failure at `info` level

**Severity:** Low
**Effort:** Trivial
**Location:** `backend/app/federation/signatures.py:260`
**Detection:** `rg "logger\.info.*fail" -i -n backend/app/federation/signatures.py`

```
logger.info("Signature verification failed for %s, retrying with fresh key", key_id)
```

A signature verification failure is a security-relevant event — it could indicate a compromised key, a replay attack, or a misconfigured peer. This should be `logger.warning()` at minimum, or possibly a dedicated security audit log entry.

### Finding LG-06: `indieauth/service.py` logs client fetch failure at `debug` level

**Severity:** Low
**Effort:** Trivial
**Location:** `backend/app/indieauth/service.py:142`
**Detection:** `rg "logger\.debug.*fail" -i -n backend/app/indieauth/service.py`

```
logger.debug("Failed to fetch client info for %s", client_id, exc_info=True)
```

This is an OAuth client metadata fetch — failure means the authorization flow can't display client information. While not critical, `debug` means it's invisible in production logs. Should be `logger.info()` or `logger.warning()`.
