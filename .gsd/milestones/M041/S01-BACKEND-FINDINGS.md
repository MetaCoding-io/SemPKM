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
