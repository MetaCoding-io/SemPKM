---
estimated_steps: 3
estimated_files: 1
skills_used: []
---

# T03: Write M032 architecture design document

**Slice:** S02 — Data-Driven Widget Types (stat-card, chart, heading)
**Milestone:** M032

## Description

Write `M032-DESIGN.md` summarizing the architecture of the Block-Based Custom UI Builder implemented across S01-S02. This is a milestone deliverable that documents the system for future reference — how the BlockRegistry works, what widgets exist, how layout migration operates, and how data flows from SPARQL through server-side rendering to the browser.

The document should reference concrete file paths and explain the key patterns established so a developer unfamiliar with M032 can understand and extend the system. Draw from the S01 summary and the S02 implementation.

## Steps

1. **Read S01 summary and current codebase state** to gather accurate details about the registry pattern, migration logic, GridStack integration, and widget inventory.

2. **Write `M032-DESIGN.md`** at `.gsd/milestones/M032/M032-DESIGN.md` with sections:
   - **Overview** — Purpose of M032, what it replaced (fixed CSS Grid layouts → GridStack free-form canvas), the three-slice structure
   - **Architecture** — GridStack.js + BlockRegistry + htmx server-rendering pipeline, how dockview event isolation works, CDN loading strategy
   - **Block Registry** — `BlockTypeSpec` dataclass fields, `BLOCK_REGISTRY` singleton API (`register`, `get`, `validate_block`, `validate_position`, `all_types`, `by_category`), auto-derived `VALID_BLOCK_TYPES` in `models.py`, config schema validation approach (type-check present keys, all keys optional)
   - **Widget Inventory** — All 9 block types with: type_name, category, config keys, rendering approach (inline HTML vs Jinja2 template, client-side vs server-side data), default dimensions
   - **Layout Migration** — `migrate_layout_to_gridstack()` mapping for 5 legacy layouts, lazy migration on first dashboard access in `render_dashboard()`, idempotency guarantee
   - **Data Flow for SPARQL Widgets** — How stat-card and chart blocks execute SPARQL server-side in `render_block()`, extract bindings, pass to Jinja2 templates; Chart.js initialization post-htmx-swap via inline script; error handling producing user-visible error blocks
   - **Key Decisions** — Event isolation via stopPropagation, server-side rendering over client-side SPARQL execution, CDN loading (not yet vendored), Chart.js theme integration via CSS custom properties

3. **Self-review** — Verify all file paths mentioned exist, section count is ≥4, no TBD/TODO placeholders.

## Must-Haves

- [ ] Document exists at `.gsd/milestones/M032/M032-DESIGN.md`
- [ ] Contains at least 4 top-level sections (## headings)
- [ ] References concrete file paths for registry.py, router.py, migration.py, templates, CSS
- [ ] Covers all 9 block types in the widget inventory
- [ ] No TBD or TODO placeholders

## Verification

- `test -f .gsd/milestones/M032/M032-DESIGN.md` — file exists
- `grep -c "^## " .gsd/milestones/M032/M032-DESIGN.md` — returns >= 4
- `! grep -qi "TBD\|TODO" .gsd/milestones/M032/M032-DESIGN.md` — no placeholders

## Inputs

- `backend/app/dashboard/registry.py` — registry implementation with 9 types (T01 output)
- `backend/app/dashboard/router.py` — render_block() with all block type branches (T02 output)
- `backend/app/dashboard/migration.py` — layout migration logic (S01 output)
- `backend/app/templates/browser/dashboard_builder.html` — builder UI (S01 + T01 output)
- `backend/app/templates/browser/dashboard_page.html` — viewer template (S01 output)

## Observability Impact

This task is a documentation-only deliverable — no runtime signals, logs, or diagnostic surfaces change. The design document itself serves as a future-agent inspection surface: agents can read `M032-DESIGN.md` to understand registry API, widget inventory, data flow, and file locations without re-deriving from code.

## Expected Output

- `.gsd/milestones/M032/M032-DESIGN.md` — architecture design document for M032
