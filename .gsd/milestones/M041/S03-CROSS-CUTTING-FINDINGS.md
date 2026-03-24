# S03 Cross-Cutting Findings: Dead Code, Duplication, Test Gaps, Tech Debt

Working data collected by T01 for T02 assembly.

---

## 1. Dead Code & Markers

### 1.1 TODO/FIXME/HACK/XXX Markers

**Finding:** Zero formal debt markers (`# TODO`, `# FIXME`, `# HACK`, `# XXX`) exist anywhere in backend Python, frontend JS, or CSS files. Case-insensitive search also returns zero hits.

- Severity: Low (informational)
- Impact: Either debt markers are cleared on commit, or developers don't use them. This is good hygiene but means accumulated debt is undocumented inline — it lives only in KNOWLEDGE.md.

### 1.2 Commented-Out Code Blocks

**Finding:** No genuine commented-out code blocks found. All 3+ consecutive comment runs are documentation comments (docstrings, section dividers, explanatory notes). Examples:
- `backend/app/notion/scanner.py:180-182` — Phase 2 explanation (documentation)
- `backend/app/ontology/service.py:314-316` — OWL hierarchy explanation (documentation)
- `frontend/static/js/copilot.js` — Section divider comments throughout (style, not dead code)
- `frontend/static/js/canvas.js:240-242` — Fallback behavior explanation (documentation)

- Severity: Low
- Effort: N/A — no action needed

### 1.3 Unused Imports (10-Module Sample)

**Finding:** 3 unused imports found across 10 sampled modules:

| File | Line | Import | Severity |
|------|------|--------|----------|
| `backend/app/main.py` | L562 | `init_template_helpers` | Low — may be side-effect import (noqa: E402 present) |
| `backend/app/browser/workspace.py` | L1333 | `AsyncSession` | Medium — dead type import |
| `backend/app/services/validation.py` | L15 | `XSD` | Low — namespace constant unused in this file |

- Severity: Low-Medium
- Effort: Small (5 min per fix)
- Note: A full `ruff` or `pyflakes` run would surface all unused imports across 193 modules.

### 1.4 Dead Functions

| Function | File | Evidence |
|----------|------|----------|
| `register_renderer()` | `backend/app/views/registry.py:55` | Defined but never called anywhere in codebase. The module docstring says renderers should use it "at installation time" but all renderers are manually wired in router.py and service.py. |

- Severity: Medium — dead infrastructure creates confusion about the intended extension pattern
- Effort: Small (remove function + update module docstring)

---

## 2. Code Duplication

### 2.1 PersonMatcher Across 9 Sync Apps

**Files:** `apps/{asana,caldav-calendar,github,google-calendar,jira,linear,monday,outlook-calendar,todoist}-sync/services/person_matcher.py`

Each of the 9 sync apps has its own `person_matcher.py` with near-identical logic for matching external user identities to RDF person IRIs. This is the single largest duplication instance in the codebase.

- Severity: Medium
- Effort: Large (extract to SDK shared module, update all 9 apps)
- Note: Documented as out-of-scope for fixing in this audit, but should be addressed in a sync-platform consolidation milestone.

### 2.2 ISO 8601 Z-Replacement Pattern (8 Instances)

**Pattern:** `.replace("Z", "+00:00")` before `fromisoformat()` — repeated in 4 files, 8 call sites.

| File | Lines |
|------|-------|
| `backend/app/federation/router.py` | 699, 728 |
| `backend/app/admin/router.py` | 140, 141, 161 |
| `backend/app/views/service.py` | 1440, 1469 |
| `backend/app/services/models.py` | 125 |

- Severity: Medium — Python 3.11+ `fromisoformat` handles "Z" natively, but the project targets 3.10+
- Effort: Small (extract `parse_iso_datetime(s: str) -> datetime` utility, 30 min)

### 2.3 datetime.now(timezone.utc).isoformat() Pattern (46 Instances)

**Pattern:** `datetime.now(timezone.utc).isoformat()` or `.strftime(...)` repeated across 46 call sites in 15+ modules (federation, inference, copilot, apps, sparql).

- Severity: Low — correct but verbose
- Effort: Small (extract `utc_now_iso() -> str` utility)

### 2.4 Label Resolution SPARQL Pattern (4+ Instances)

**Pattern:** The same OPTIONAL chain for label resolution (dcterms:title → rdfs:label → skos:prefLabel with COALESCE) appears in:
- `backend/app/services/labels.py:85-87` (canonical implementation)
- `backend/app/vfs/collections.py:248-250`
- `backend/app/vfs/router.py:132-134, 222-224`
- `backend/app/events/query.py:138, 184`

The `labels.py` LabelService is the intended canonical source, but VFS and events modules inline their own SPARQL fragments instead of delegating.

- Severity: Medium — divergence risk when label precedence rules change
- Effort: Medium (refactor VFS/events to use LabelService, verify query performance)

### 2.5 FROM `<urn:sempkm:current>` Hard-Coded Graph URIs (20+ Instances)

**Pattern:** `FROM <urn:sempkm:current>` appears as a hard-coded string in 20+ locations across `vfs/strategies.py`, `vfs/mount_router.py`, `vfs/mount_resource.py`, `inference/service.py`, and others — instead of using `scope_to_current_graph()` from `sparql/client.py`.

| File | Instances |
|------|-----------|
| `backend/app/vfs/strategies.py` | 12 |
| `backend/app/vfs/mount_router.py` | 2 |
| `backend/app/vfs/mount_resource.py` | 2 |
| `backend/app/inference/service.py` | 5+ |

- Severity: Medium — if the current graph URI ever changes, these would all need manual updates
- Effort: Medium (centralize as constant + use scope_to_current_graph where applicable)

### 2.6 IRI Pill Rendering (Frontend, 3 Implementations)

**Pattern:** IRI-to-pill HTML rendering exists in three separate JS files:
- `frontend/static/js/sparql-console.js:1013-1044` — SPARQL result pills
- `frontend/static/js/copilot.js:749-758` — Copilot chat pills
- `frontend/static/js/copilot.js:1706` — Create-object confirmation pills

Each generates slightly different HTML with different CSS classes (`sparql-iri-pill`, `copilot-iri-pill`) but identical logic (resolve label, build anchor tag with data-iri).

- Severity: Low-Medium
- Effort: Small (extract shared `renderIriPill(iri, label, cssClass)` utility)

### 2.7 escapeHtml Function (Frontend, 2+ Definitions)

**Pattern:** `escapeHtml()` is defined independently in:
- `frontend/static/js/workspace.js:2269`
- `frontend/static/js/context-indicator.js:72` (as `_esc()`)

Both do the same `&`, `<`, `>`, `"`, `'` entity encoding.

- Severity: Low
- Effort: Small (extract to shared utility or use a single global)

---

## 3. Test Coverage Gaps

### 3.1 Overview

| Metric | Count |
|--------|-------|
| Total backend modules (non-`__init__`) | 193 |
| Total test files | 159 |
| Modules with zero matching test file | 165 |
| **Effective coverage gap** | **85.5%** of modules have no dedicated test file |

Note: Many test files test multiple modules or test integration scenarios, so the actual code coverage is higher than 14.5%. But 165 modules have no test file that directly targets them.

### 3.2 Critical Untested Modules

#### Authentication (7/7 modules untested)

| Module | Risk |
|--------|------|
| `auth/dependencies.py` | **Critical** — session token extraction, user injection |
| `auth/service.py` | **Critical** — login, registration, password hashing |
| `auth/router.py` | **Critical** — login/logout/register HTTP endpoints |
| `auth/tokens.py` | **High** — JWT creation and validation |
| `auth/rate_limit.py` | **High** — rate limiting logic |
| `auth/models.py` | Medium — SQLAlchemy User model |
| `auth/schemas.py` | Low — Pydantic schemas |

Note: `test_auth_tokens.py` exists but tests the app-platform token system, not the core auth module.

#### Commands (9/10 modules untested)

| Module | Risk |
|--------|------|
| `commands/router.py` | **Critical** — batch command endpoint, slot resolution |
| `commands/handlers/object_create.py` | **Critical** — IRI minting, RDF object creation |
| `commands/handlers/edge_create.py` | **High** — relationship creation |
| `commands/handlers/object_patch.py` | **High** — property updates |
| `commands/handlers/edge_patch.py` | **High** — relationship updates |
| `commands/handlers/body_set.py` | **High** — body content persistence |
| `commands/dispatcher.py` | **High** — command type dispatch |
| `commands/schemas.py` | Low — Pydantic schemas |
| `commands/exceptions.py` | Low — exception classes |

Only `body_diff` has a test file.

#### Triplestore (3/3 untested)

| Module | Risk |
|--------|------|
| `triplestore/client.py` | **Critical** — all RDF4J HTTP communication |
| `triplestore/sync_client.py` | **High** — synchronous triplestore operations |
| `triplestore/setup.py` | **High** — repository initialization |

Note: `test_sparql_client.py` exists but tests the SPARQL query layer, not the triplestore HTTP client.

#### Views (3/3 untested)

| Module | Risk |
|--------|------|
| `views/service.py` | **Critical** — all ViewSpec resolution, SPARQL generation for 11 renderers |
| `views/router.py` | **Critical** — all view HTTP endpoints |
| `views/registry.py` | Low — mostly dead code |

Note: Individual renderer tests exist (`test_kanban.py`, `test_calendar.py`, `test_map.py`, `test_timeline.py`, etc.) but they test specific renderers, not the core service/router.

#### Copilot (6/7 untested)

| Module | Risk |
|--------|------|
| `copilot/service.py` | **High** — LLM interaction, SPARQL extraction |
| `copilot/personas.py` | **High** — persona management |
| `copilot/conversation.py` | Medium — conversation CRUD |
| `copilot/context.py` | Medium — context building for LLM |
| `copilot/models.py` | Low — SQLAlchemy models |
| `copilot/schemas.py` | Low — Pydantic schemas |

Note: `test_copilot_service.py` and `test_conversation_service.py` exist but are targeted at specific test scenarios.

#### Other Notable Gaps

| Module | Risk | Notes |
|--------|------|-------|
| `main.py` | **High** | Lifespan, middleware, 600+ lines of wiring |
| `config.py` | **High** | All Pydantic settings validation |
| `browser/workspace.py` | **High** | Primary workspace page, 1300+ lines |
| `browser/objects.py` | **High** | Object CRUD HTTP layer |
| `sparql/router.py` | **High** | SPARQL query endpoint |
| `federation/service.py` | **High** | ActivityPub federation |
| `inference/service.py` | **High** | OWL/RDFS inference engine |
| `vfs/*` (13 modules) | **High** | Entire VFS subsystem has only 2 test files |

---

## 4. Tech Debt Cross-Reference

### Items from KNOWLEDGE.md — Still Present

| ID | Description | Status | Evidence |
|----|-------------|--------|----------|
| K001 | rdflib `xsd:dayTimeDuration` workaround | **Still present** | `models/crm/rules/crm.ttl` still contains the workaround comment |
| K002 | Seed data dateTime vs date mismatch | **Still present** | `models/basic-pkm/seed/basic-pkm.jsonld` uses `xsd:dateTime` for `dcterms:created` |
| Knowledge entry | `extract_scope_where_body()` LIMIT bug | **Still present** | `backend/app/views/service.py:3505` — regex `\}\s*$` fails on queries with trailing LIMIT/ORDER BY |
| Knowledge entry | `register_renderer()` dead code | **Still present** | `backend/app/views/registry.py:55` — defined but never called |
| Knowledge entry | SPARQL API lacks UPDATE endpoint | **Still present** | No update route in `backend/app/sparql/router.py` |
| Knowledge entry | PersonMatcher duplication in apps/ | **Still present** | 9 identical `person_matcher.py` files across sync apps |
| Knowledge entry | Z-replacement without utility | **Still present** | 8 instances across 4 files |

### Items from KNOWLEDGE.md — Resolved

| ID | Description | Status | Evidence |
|----|-------------|--------|----------|
| K003 | Worktree isolation mode | **Resolved** | `.gsd/preferences.md` now uses `isolation: "none"` |
| Knowledge entry | nginx `/static/` path issue | **Resolved** | No `src="/static/"` references found in templates |

### Accumulated Debt Not in KNOWLEDGE.md

| Item | Description | Severity |
|------|-------------|----------|
| Auth module zero test coverage | 7 critical auth modules with no tests | **Critical** |
| Commands module zero test coverage | 9 command handler modules with no tests | **Critical** |
| Triplestore client zero test coverage | All RDF4J communication untested | **Critical** |
| `datetime.now(timezone.utc)` proliferation | 46 call sites with no central utility | Medium |
| `FROM <urn:sempkm:current>` hard-coding | 20+ hard-coded graph URIs | Medium |
| Frontend escapeHtml duplication | 2+ independent implementations | Low |

---

## Detection Commands (Reproducible)

```bash
# Dead code markers
rg -i "todo|fixme|hack\b|xxx\b" backend/app/ frontend/static/ --type py --type js --type css

# Commented-out code (3+ consecutive comment lines with code patterns)
fd -e py . backend/app/ -x awk '/^[[:space:]]*#.*[=(:]/{c++;l[c]=NR": "$0;next}{if(c>=3)for(i=1;i<=c;i++)print FILENAME":"l[i];c=0;delete l}' {}

# Unused imports (per-file)
rg "^from .* import|^import " backend/app/main.py -n

# Test coverage gaps
comm -23 <(fd -e py . backend/app/ --exclude '__pycache__' -x basename {} .py | sort -u) <(fd -e py . backend/tests/ --exclude '__pycache__' -x basename {} .py | sed 's/^test_//' | sort -u)

# Z-replacement duplication
rg '\.replace\("Z", "\+00:00"\)' backend/app/ -n

# datetime.now proliferation
rg 'datetime\.now\(timezone\.utc\)' backend/app/ -c

# FROM graph hard-coding
rg 'FROM <urn:sempkm:current>' backend/app/ -c

# PersonMatcher duplication
fd "person_matcher" apps/

# register_renderer dead code
rg "register_renderer" backend/app/views/ -n

# Label resolution SPARQL duplication
rg "dcterms:title.*rdfs:label\|OPTIONAL.*dcterms:title" backend/app/ -n
```
