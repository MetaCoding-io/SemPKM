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

---

## Type Safety

### Finding TS-01: 74% return type annotation coverage overall — routers are the weakest layer (15% average)

**Severity:** High
**Effort:** Medium (incremental, file-by-file)
**Location:** 35 router modules, 20 service modules, 30+ utility modules
**Detection:** `rg "^\s*def " backend/app/ -n | wc -l` → 669 total; `rg "^\s*def " backend/app/ -n | rg -v "\->" | wc -l` → 173 without return annotations; coverage = 496/669 = 74%

| Layer | Annotated / Total | Coverage |
|-------|-------------------|----------|
| Routers (35 files) | 62 / 368 | **17%** |
| Services (20 files) | 223 / 332 | **67%** |
| Utilities / other (30+ files) | 211 / ~300 | ~70% |

Routers are the weakest layer at ~17% annotation coverage. Zero-coverage routers include `lint/router.py` (0/18), `models/router.py` (0/3), `health/router.py` (0/1), `debug/router.py` (0/2), `rdf_import/router.py` (0/8), `sparql/mirror_router.py` (0/6), `validation/router.py` (0/2), `apps/router.py` (0/2), `context/router.py` (0/4).

The worst service-layer offenders: `views/service.py` (21/56 = 37%), `canvas/service.py` (2/11 = 18%), `copilot/service.py` (4/9 = 44%), `context/notification_service.py` (5/11 = 45%).

The worst utility-layer offenders: `browser/events.py` (0/7), `browser/objects.py` (0/12), `browser/pages.py` (0/5), `browser/settings.py` (0/12), `copilot/conversation.py` (0/6), `copilot/personas.py` (0/9).

**Recommendation:** Prioritize router annotations — FastAPI uses return type annotations for `response_model` inference when no explicit `response_model=` is given. Without annotations, OpenAPI docs show no response schema for 83% of routes, and FastAPI skips response validation entirely.

### Finding TS-02: Only 45 of ~260 route decorators specify `response_model` (17%)

**Severity:** Medium
**Effort:** Medium
**Location:** 35 router modules
**Detection:** `rg "response_model=" backend/app/ -n | wc -l` → 45; total route decorators → ~260

215 route handlers return untyped responses. FastAPI can infer response_model from the return type annotation, but per TS-01 most routers lack annotations too, so there's no response validation at all on those endpoints.

The modules with best `response_model` coverage are `federation/router.py` (6/21 routes), `webid/router.py` (5/8), `models/router.py` (3/3), and `api/router.py` (3/6). The entire `browser/` module tree (objects.py, workspace.py, events.py, settings.py, search.py, apps.py, pages.py, comments.py) has zero `response_model` declarations — understandable since they return HTML via `TemplateResponse`, but JSON endpoints mixed in (e.g., `objects.py` autocomplete, events list) could benefit from response schemas.

**Recommendation:** Add `response_model` to all JSON-returning endpoints first. HTML-returning routes should use `response_class=HTMLResponse` for accurate OpenAPI docs.

### Finding TS-03: 158 Pydantic models — zero use of deprecated `.dict()` (positive finding)

**Severity:** None (positive finding)
**Detection:** `rg "class\s+\w+.*\(.*BaseModel" backend/app/ | wc -l` → 158; `rg "\.dict\(\)" backend/app/` → 0; `rg "\.model_dump\(\)" backend/app/ | wc -l` → 18

All Pydantic serialization uses the v2 `model_dump()` API. Zero instances of the deprecated v1 `.dict()` method. The 18 `model_dump()` calls are in the correct locations (API endpoints, serialization boundaries).

---

## SPARQL Construction

### Finding SQ-01: 131 f-string SPARQL construction sites across 25 files — no parameterized query builder

**Severity:** High
**Effort:** High (architectural — requires building SPARQL builder utility)
**Location:** 25 files (see table below)
**Detection:** `{ rg -n 'f"[^"]*(?:SELECT|INSERT|DELETE|CONSTRUCT|ASK)' backend/app/ --no-heading; rg -n "f'[^']*(?:SELECT|INSERT|DELETE|CONSTRUCT|ASK)" backend/app/ --no-heading; rg -n 'f"""[^"]*(?:SELECT|INSERT|DELETE|CONSTRUCT|ASK)' backend/app/ --no-heading; } | sort -u | wc -l`

| File | f-string SPARQL sites |
|------|-----------------------|
| `views/service.py` | ~30 (largest) |
| `sparql/query_service.py` | ~12 |
| `services/models.py` | ~15 |
| `ontology/service.py` | ~14 |
| `services/webhooks.py` | ~8 |
| `admin/router.py` | ~6 |
| `events/store.py` | ~5 |
| `models/registry.py` | ~6 |
| `services/validation.py` | ~5 |
| `sparql/mirror.py` | ~3 |
| `sparql/migrate_queries.py` | ~6 |
| Other (14 files) | 1–3 each |

Every SPARQL query in the codebase is constructed via Python f-strings. There is no parameterized query builder, no template engine, and no central utility for safe IRI insertion. The sole escaping function is `escape_sparql_regex()` in `sparql/utils.py`, which only handles REGEX metacharacters — it does not escape IRIs, literals, or prevent SPARQL injection.

### Finding SQ-02: `scope_filter` is inserted raw into SPARQL WHERE clauses — injection via saved queries

**Severity:** High
**Effort:** Medium
**Location:** `backend/app/views/service.py:346,380,409,1320,1708,1881,2140,2399,2615,2873,3063`
**Detection:** `rg "scope_filter" backend/app/views/service.py -n | head -10`

The `scope_filter` parameter (a raw SPARQL WHERE clause body from a saved query) is interpolated directly into f-string queries at 11 sites in `views/service.py`:

```python
scope_clause = f"  {{ SELECT ?s WHERE {{ {scope_filter} }} }}\n"
```

If a saved query's WHERE body contains SPARQL injection (e.g., `} } ; DROP ALL ; #`), it could modify the outer query structure. The risk is mitigated by the fact that saved queries are authored by authenticated users who already have full SPARQL access via `/api/sparql`, but this pattern is still fragile:
1. Future multi-user scenarios where query sharing is enabled could expose this
2. The `vfs/strategies.py` (L94, L96) similarly injects `resolved_query_text` and `mount.sparql_scope` raw into subqueries

**Recommendation:** Validate that `scope_filter` contains only WHERE body patterns (no closing braces that escape the subquery) before interpolation. A simple check: count `{` vs `}` and reject if unbalanced.

### Finding SQ-03: IRI validation is duplicated across 3 independent implementations

**Severity:** Medium
**Effort:** Low
**Location:** `backend/app/browser/_helpers.py:13`, `backend/app/canvas/router.py:40`, `backend/app/models/validator.py:55`
**Detection:** `rg "def.*iri.*valid|def.*valid.*iri|def.*is_valid_iri" backend/app/ -n -i`

Three separate functions validate IRIs:
- `_validate_iri()` in `browser/_helpers.py` — used by browser routes
- `_is_valid_iri()` in `canvas/router.py` — used by canvas routes
- `validate_iri_namespacing()` in `models/validator.py` — validates namespace conventions

These likely have subtly different validation rules. A single shared `validate_iri()` utility in `sparql/utils.py` or a common module would prevent drift and ensure consistent IRI handling.

### Finding SQ-04: Only regex escaping exists — no IRI or literal escaping for SPARQL construction

**Severity:** Medium
**Effort:** Medium
**Location:** `backend/app/sparql/utils.py`
**Detection:** `rg "def " backend/app/sparql/utils.py -n` → single function: `escape_sparql_regex()`

The `sparql/utils.py` module contains only one function — `escape_sparql_regex()` — which escapes REGEX metacharacters for SPARQL `REGEX()` filters. There are no utilities for:
- **IRI escaping** — IRIs from user input or external sources are wrapped in `<{iri}>` with no validation that the string is a valid IRI (no `<`, `>`, or space characters)
- **Literal escaping** — String literals from user input are quoted with no escaping of `"` or `\` characters
- **Parameterized query construction** — No builder pattern, no template substitution with proper escaping

This means all 131 f-string SPARQL sites trust their input. For graph IRIs (controlled by the system) this is acceptable. For user-supplied labels, descriptions, or search terms used in SPARQL string comparisons, this is a correctness risk (a description containing `"` would produce malformed SPARQL).

---

## Async Patterns

### Finding AP-01: 6 blocking `open()` calls in async router modules

**Severity:** Medium
**Effort:** Low
**Location:** 6 files (see table)
**Detection:** `for f in $(fd -e py . backend/app/ --exclude tests); do has_async=$(rg "^async def " "$f" | wc -l); has_open=$(rg "\bopen\(" "$f" | rg -v "^\s*#" | wc -l); if [ "$has_async" -gt 0 ] && [ "$has_open" -gt 0 ]; then echo "$f"; fi; done`

| File | Line | Context |
|------|------|---------|
| `admin/router.py` | 917 | `with open(manifest_path) as f:` — reads manifest JSON synchronously in async handler |
| `apps/admin_router.py` | 110 | `with open(manifest_path) as f:` — reads manifest JSON |
| `browser/apps.py` | 356 | `with open(manifest_path) as f:` — reads manifest JSON |
| `notion/router.py` | 145 | `with open(zip_path, "wb") as f:` — writes uploaded zip |
| `obsidian/router.py` | 117 | `with open(zip_path, "wb") as f:` — writes uploaded zip |
| `services/icons.py` | 72 | `with open(manifest_path) as f:` — reads manifest JSON |

These are synchronous filesystem I/O operations inside `async def` route handlers. While the impact is minimal for small files (manifest JSONs are <10KB), the `notion/router.py` and `obsidian/router.py` zip writes could block the event loop for large uploads.

**Recommendation:** Replace with `aiofiles.open()` for write operations on uploaded files. The manifest reads are low-risk (small files, infrequent access) but should still use `asyncio.to_thread(json.load, f)` or `aiofiles` for consistency.

### Finding AP-02: Zero `time.sleep()` calls (positive finding)

**Severity:** None (positive finding)
**Detection:** `rg "time\.sleep\(" backend/app/ -n` → 0 results

No blocking `time.sleep()` calls exist anywhere in the backend application code. All delays use `asyncio.sleep()` or no delay at all.

### Finding AP-03: 3 sync helper functions in async router modules — low risk

**Severity:** Low
**Effort:** Trivial
**Location:** `backend/app/admin/router.py:1395`, `backend/app/canvas/router.py:56,175`
**Detection:** `rg "^def [a-z]" backend/app/admin/router.py backend/app/canvas/router.py -n`

| Function | File | Analysis |
|----------|------|----------|
| `templates_response()` | `admin/router.py:1395` | Pure template rendering helper — CPU-bound, fast, no I/O. Sync is correct. |
| `get_canvas_service()` | `canvas/router.py:56` | FastAPI `Depends()` factory — sync factories are standard FastAPI practice. |
| `build_property_list()` | `canvas/router.py:175` | Pure data transformation — no I/O, sync is correct. |

These are all appropriate uses of sync functions in async modules. FastAPI handles sync `Depends()` factories correctly by running them in a thread pool.

### Finding AP-04: 254 `request.app.state` accesses — mixed DI pattern

**Severity:** Medium
**Effort:** High (widespread refactor)
**Location:** 35+ router and utility modules
**Detection:** `rg "request\.app\.state\." backend/app/ -n | wc -l` → 254

The codebase uses two parallel dependency injection patterns:
1. **`Depends()` functions** in `dependencies.py` — 9 factory functions wrapping `request.app.state` access
2. **Direct `request.app.state.X`** — 254 inline accesses scattered across routers

Many routes use both patterns simultaneously: `Depends(get_triplestore_client)` for the triplestore but `request.app.state.templates` directly for Jinja2. This inconsistency means:
- Some dependencies are testable via `app.dependency_overrides` (Depends-based)
- Others require patching `app.state` directly (hard to mock in tests)
- No single place shows all dependencies a route handler needs

The `dependencies.py` module has factories for only 9 of the ~20+ services attached to `app.state`. Notable missing factories: `templates`, `template_service`, `view_spec_service`, `shapes_service` (exists but not used consistently), `validation_queue`, `workflow_service`.

**Recommendation:** Create `Depends()` factories for all services and eliminate direct `request.app.state` access in route handlers. This is a large refactor but dramatically improves testability.

---

## FastAPI Patterns

### Finding FP-01: Router prefix conventions are inconsistent — some have prefix, some rely on `include_router`

**Severity:** Low
**Effort:** Low
**Location:** 30+ router definitions in `main.py`
**Detection:** `rg "APIRouter\(" backend/app/ -n | head -30`

| Pattern | Count | Example |
|---------|-------|---------|
| `APIRouter(prefix="/api/...", tags=[...])` | 18 | `federation/router.py` |
| `APIRouter(tags=[...])` (no prefix) | 12 | `shell/router.py`, `federation/inbox.py`, `apps/router.py` |
| Dual router (browser + api) | 4 | `workflow/router.py`, `persona/router.py`, `dashboard/router.py` |

Routers without prefixes have their paths defined in `main.py` via `include_router(prefix=...)`. This splits route definition across two files, making it harder to determine a route's full path from the router file alone.

All routers have `tags=` — no untagged routers exist (positive).

### Finding FP-02: 45 of ~260 routes specify `response_model` — 83% lack response schema

**Severity:** Medium
**Effort:** Medium
**Location:** All router modules
**Detection:** `rg "response_model=" backend/app/ | wc -l` → 45; total routes → ~260

(Cross-reference with TS-02.) The 215 routes without `response_model` produce untyped OpenAPI documentation. For JSON API endpoints this means:
1. No automatic response serialization/filtering (fields not in the model leak through)
2. No response validation in debug mode
3. OpenAPI clients (code generators, Swagger UI) show empty response schemas

The `browser/` module tree (HTML-returning routes) accounts for ~80 routes that legitimately don't need `response_model` — they should instead use `response_class=HTMLResponse`. The remaining ~135 JSON-returning routes without `response_model` are the actionable gap.

### Finding FP-03: `dependencies.py` covers only 9 of ~20+ `app.state` services

**Severity:** Medium
**Effort:** Low (add missing factories)
**Location:** `backend/app/dependencies.py`
**Detection:** `rg "def get_" backend/app/dependencies.py -n`

Current `Depends()` factories in `dependencies.py`:
1. `get_triplestore_client()`
2. `get_prefix_registry()`
3. `get_label_service()`
4. `get_validation_queue()`
5. `get_validation_service()`
6. `get_model_service()`
7. `get_shapes_service()`
8. `get_webhook_service()`
9. `get_auth_service()`

Missing factories for services accessed via `request.app.state` directly:
- `templates` (Jinja2Templates) — accessed in 15+ routers
- `template_service` — accessed in `task_templates/router.py`
- `view_spec_service` — accessed in `models/router.py`, `browser/workspace.py`
- `workflow_service` — accessed in `workflow/router.py`
- `event_store` — accessed in some routers directly
- `ops_log_service` — defined as `Depends` in `inference/router.py` but not in `dependencies.py`
- `icon_service` — accessed in `browser/_helpers.py`
- `settings_service` — accessed in `browser/_helpers.py`

**Recommendation:** Add the missing factories to `dependencies.py` and migrate direct `request.app.state` accesses. This is the prerequisite for AP-04's consistency improvement.

### Finding FP-04: No middleware ordering documentation — 5 middleware layers with implicit ordering

**Severity:** Low
**Effort:** Trivial (documentation task)
**Location:** `backend/app/main.py`
**Detection:** `rg "add_middleware\|\.middleware" backend/app/main.py -n`

The app registers 5 middleware layers in `main.py`. FastAPI/Starlette processes middleware in reverse registration order (last registered = outermost). The current order and its implications aren't documented:

1. CORS middleware
2. Session middleware
3. Timing middleware
4. Rate limiting middleware
5. Error handling middleware (exception handlers)

The timing middleware wraps inside CORS but outside session — this means CORS preflight timing is captured but session resolution isn't included in the timing measurement. Whether this is intentional isn't documented.
