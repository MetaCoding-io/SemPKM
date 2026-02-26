# Coding Conventions

**Analysis Date:** 2026-02-25

## Naming Patterns

**Python Files:**
- Modules use `snake_case`: `router.py`, `service.py`, `dependencies.py`, `schemas.py`
- Private helper functions are prefixed with `_`: `_build_insert_data_sparql()`, `_parse_commands()`, `_is_htmx_request()`
- Module-level constants use `UPPER_SNAKE_CASE`: `WEBHOOK_EVENT_TYPES`, `CURRENT_GRAPH_IRI`, `MODELS_GRAPH`
- Logger always named `logger`: `logger = logging.getLogger(__name__)`

**Python Classes:**
- Services use `PascalCase` with `Service` suffix: `ModelService`, `WebhookService`, `ShapesService`, `LabelService`
- Pydantic models use `PascalCase` with semantic suffix: `ObjectCreateParams`, `CommandResponse`, `WebhookConfig`
- Dataclasses use `PascalCase` with semantic suffix: `InstallResult`, `RemoveResult`, `Operation`, `EventResult`
- Exception classes end in `Error`: `CommandError`, `ObjectNotFoundError`, `InvalidCommandError`, `ConflictError`

**Python Functions:**
- All `snake_case`, including async functions: `get_current_user()`, `dispatch()`, `mint_object_iri()`
- Factory/builder helpers prefixed with `_build_`: `_build_insert_data_sparql()`, `_build_register_sparql()`
- Predicate/check functions match what they test: `is_model_installed()`, `check_user_data_exists()`

**TypeScript (E2E):**
- Files use `kebab-case`: `api-client.ts`, `seed-data.ts`, `wait-for.ts`
- Test files use `kebab-case.spec.ts`: `create-object.spec.ts`, `nav-tree.spec.ts`
- Functions use `camelCase`: `loginViaApi()`, `authenticatedContext()`, `waitForWorkspace()`
- Constants use `UPPER_SNAKE_CASE` or `PascalCase` for exported objects: `SEED`, `TYPES`, `SEL`
- Type aliases use `PascalCase`: `AuthFixtures`
- Classes use `PascalCase`: `ApiClient`

**Template Files (Jinja2/HTML):**
- Template files use `snake_case.html`: `nav_tree.html`, `object_tab.html`, `type_picker.html`
- Template directory names match module names: `browser/`, `admin/`, `forms/`, `components/`
- CSS classes use `kebab-case`: `card-grid`, `workspace-layout`, `event-log-header`
- Data attributes follow htmx conventions: `data-testid`, `hx-get`, `hx-target`

## Code Style

**Formatting:**
- No formatter config file detected (no ruff, black, or isort config in `backend/pyproject.toml`)
- Code follows PEP 8 conventions by observation: 4-space indent, blank lines between methods
- Type hints used consistently throughout backend

**Linting:**
- No linter configured in pyproject.toml (no ruff/flake8/mypy entries)
- TypeScript uses `strict: true` in `e2e/tsconfig.json`, with `forceConsistentCasingInFileNames: true`

## Import Organization

**Python Order (observed):**
1. Standard library: `import logging`, `from datetime import ...`, `from pathlib import Path`
2. Third-party: `from fastapi import ...`, `from pydantic import ...`, `from rdflib import ...`
3. Local application: `from app.config import settings`, `from app.events.store import EventStore`

**TypeScript Order (observed):**
1. External packages: `import { test, expect } from '@playwright/test'`
2. Local fixtures: `import { ... } from '../../fixtures/auth'`
3. Local helpers: `import { SEL } from '../../helpers/selectors'`, `import { waitForIdle } from '../../helpers/wait-for'`

**Path Aliases (TypeScript):**
- `@fixtures/*` → `./fixtures/*`
- `@helpers/*` → `./helpers/*`
- Defined in `e2e/tsconfig.json`

## Module Structure Pattern

Every FastAPI module follows the same layout:
```
backend/app/{module}/
  __init__.py      # Module docstring only (or empty)
  router.py        # FastAPI router, Jinja2 templates, htmx endpoints
  models.py        # SQLAlchemy ORM models (auth) or RDF constants (events)
  schemas.py       # Pydantic request/response models
  service.py       # Business logic class
  dependencies.py  # FastAPI dependency injection functions
```

**Module `__init__.py` convention:** Either empty or contains a single docstring describing the module purpose. Example from `backend/app/commands/__init__.py`:
```python
"""Command API: Pydantic schemas, dispatcher, and handlers for SemPKM writes."""
```

## Error Handling

**FastAPI HTTP Errors:**
- Raise `HTTPException(status_code=..., detail=...)` for API errors
- Command errors use a hierarchy: `CommandError` (base, 400) → `ObjectNotFoundError` (404) → `InvalidCommandError` (400) → `ConflictError` (409)
- Custom exception handler in `backend/app/main.py` routes auth errors to appropriate format (JSON for API routes, redirect or template for HTML routes)

**Service/Domain Errors:**
- Services return result dataclasses (`InstallResult`, `RemoveResult`) rather than raising exceptions for expected failure cases
- Unexpected failures (triplestore errors) propagate as exceptions with rollback in `finally` blocks
- Fire-and-forget operations (webhooks, validation) catch and log warnings; never raise

**Rollback Pattern:**
```python
txn_url: str | None = None
try:
    txn_url = await self._client.begin_transaction()
    # ... operations ...
    txn_url = None  # Prevent rollback in finally
finally:
    if txn_url:
        try:
            await self._client.rollback_transaction(txn_url)
        except Exception:
            pass  # Best-effort rollback
```

**SPARQL Error Handling:**
- Operations that may fail silently are documented as warnings: `# Seed materialization failure is a warning, not a full failure`

## Logging

**Framework:** Python standard library `logging`

**Module-level setup:**
```python
logger = logging.getLogger(__name__)
```

**Patterns:**
- `logger.info(...)` for startup, service initialization, successful operations
- `logger.warning(...)` for non-fatal failures (webhook dispatch failures, best-effort rollback failures)
- `logger.error(...)` for unexpected errors (not observed to be common — exceptions propagate instead)
- Log level determined by `DEBUG` environment variable via `backend/app/config.py`

## Comments

**Module Docstrings:**
- Every module begins with a multi-line docstring explaining purpose, key patterns, and design decisions. Example from `backend/app/events/store.py`:
```python
"""Event store: immutable event graph creation and current state materialization.

Every write to SemPKM flows through EventStore.commit(), which atomically:
1. Creates an immutable event named graph with metadata + data triples
2. Materializes changes into the current state graph (inserts and deletes)
...
"""
```

**Function Docstrings:**
- All public functions and methods have docstrings using Google-style format (Args/Returns/Raises sections)
- Private helper functions (`_prefixed`) have briefer docstrings

**Inline Comments:**
- Step-numbered comments in complex multi-step operations: `# 1. Parse manifest`, `# 2. Check duplicate`
- Research references: `# per Research Pitfall 2`, `# per user decision`
- TODO comments: `# TODO: make configurable for production`, `# TODO: send email with token via SMTP`
- Type annotations on inline variable declarations: `operations: list[Operation] = []`

**TypeScript Comments:**
- File-level JSDoc block describing purpose, fixtures provided, and usage notes
- Inline comments explaining htmx-specific behavior: `// htmx adds the htmx-settling class during the swap settling phase`
- Section dividers with `// ──` decorators in large test files

## Function Design

**Size:** Functions are generally single-purpose and kept to one screen. Complex operations are decomposed into private `_helpers`.

**Parameters:**
- Dependencies injected via FastAPI `Depends()` pattern
- Service class instances take `client: TriplestoreClient` in `__init__`
- Async context manager pattern for lifespan management

**Return Values:**
- Async functions return typed values: `async def install(...) -> InstallResult`
- Optional returns use `X | None` (Python 3.10+ union syntax): `async def get_form_for_type(...) -> NodeShapeForm | None`
- Dataclasses used for structured multi-field returns instead of tuples

## Pydantic Models

- Pydantic v2 `BaseModel` for all API schemas
- `Literal[...]` discriminated union for command routing (`command: Literal["object.create"]`)
- `@dataclass` (stdlib) used for internal data structures that don't require validation (`Operation`, `InstallResult`, `PropertyShape`)
- `field(default_factory=list)` for mutable defaults in dataclasses
- `BaseSettings` + `SettingsConfigDict(env_file=".env")` for application config

## Template Conventions

**htmx Partials:**
- Routes that serve both full-page and htmx partial responses check `HX-Request` header: `_is_htmx_request(request)`
- `jinja2-fragments` library used for block-level rendering: `templates.TemplateResponse(block_name="content")`
- Template blocks named descriptively: `{% block content %}`, `{% block layout_class %}`

**IDs and Selectors:**
- DOM IDs use `kebab-case`: `#editor-area`, `#lint-content`, `#nav-tree`
- `data-testid` attributes added to key elements for E2E tests: `data-testid="settings-page"`
- CSS classes use `kebab-case` with BEM-inspired naming: `.workspace-layout`, `.card-grid`, `.event-log-container`

---

*Convention analysis: 2026-02-25*
