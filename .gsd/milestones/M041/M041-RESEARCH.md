# M041 Research: Code Quality Audit — Backend & Frontend

## Codebase Metrics Summary

| Dimension | Files | LOC | Largest File |
|-----------|-------|-----|-------------|
| Backend Python | 233 | 60,069 | `views/service.py` (3,663) |
| Frontend JS | 28 | 18,587 | `workspace.js` (5,409) |
| Frontend CSS | 16 | 20,495 | `workspace.css` (9,203) |
| Jinja2 Templates | 165 | 18,323 | `dashboard_builder.html` (749) |
| **Total** | **442** | **117,474** | |

## Key Findings

1. **God modules:** views/service.py (3,663 LOC, 55 funcs), workspace.js (5,409 LOC, 188 funcs), views/router.py (generic_view 1,020 lines), admin/router.py (1,400 LOC, 7 swallowed exceptions)
2. **Zero SPARQL escaping utility** despite 20+ modules doing f-string SPARQL construction
3. **15 swallowed exceptions** (except Exception + pass with no logging)
4. **Zero linting configuration** — no ruff, eslint, stylelint, or prettier
5. **87/167 modules (52%) have no test file**
6. **Event listener imbalance:** 197 addEventListener vs. 20 removeEventListener across JS
7. **CSS 85% tokenized:** 201 hardcoded hex colors remain alongside 1,205 var() references
8. **Type annotation gap:** Services 100%, routers 5-25%

## Recommended Slice Order

Backend structural → Error handling → SPARQL safety → Frontend → Tests → Report consolidation
