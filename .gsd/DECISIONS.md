# Decisions Register

<!-- Append-only. Never edit or remove existing rows.
     To reverse a decision, add a new row that supersedes it.
     Read this file at the start of any planning or research phase. -->

| # | When | Scope | Decision | Choice | Rationale | Revisable? |
|---|------|-------|----------|--------|-----------|------------|
| D001 | M002 | scope | Items from CONCERNS.md already fixed | Close: datetime.now timezone, label cache invalidation, CORS conditional, IRI validation, debug SPARQL owner-only, EventStore DI, Alembic startup, SMTP, session cleanup, ViewSpec cache, cookie_secure | Verified in codebase — fixed in v2.1 through v2.6 | No |
| D002 | M002 | scope | MCP server for AI agent access | Defer to future milestone | Feature work, not polish — doesn't belong in hardening milestone | Yes — when hardening complete |
| D003 | M002 | scope | Admin model detail stats and charts | Defer to future milestone | Cosmetic admin enhancements, low priority | Yes |
| D004 | M002 | scope | Browser router refactor approach | Split into domain sub-routers, zero behavior change | Preserves all URL paths and htmx wiring; E2E tests are the safety net | No |
| D005 | M002 | scope | Federation testing approach | Dual-instance docker-compose for E2E testing | Single instance can't test federation; permanent dev setup not needed | Yes — if federation becomes daily workflow |
| D006 | M002 | scope | Obsidian import testing approach | Manual user-driven import of real Ideaverse vault, fix bugs found | Automated testing of 905-note vault import is fragile; user judgment needed for mapping quality | No |
| D007 | M002/S01 | tech | Rate limiting library | slowapi with in-memory backend, per-route decorators (no global default) | Battle-tested (wraps flask-limiter), no Redis needed for single-instance, supports `get_remote_address` for real client IP behind nginx | Yes — add Redis backend if scaling to multiple workers |
| D008 | M002/S01 | tech | SPARQL regex escaping placement | Standalone `backend/app/sparql/utils.py` module | Must be importable without pulling in views service; S03 will unit-test it directly | No |
