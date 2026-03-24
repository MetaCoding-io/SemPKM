---
estimated_steps: 8
estimated_files: 1
skills_used: []
---

# T03: Type safety, SPARQL construction, async patterns, and FastAPI audit

**Slice:** S01 — Backend Code Quality Audit
**Milestone:** M041

## Description

Complete backend audit coverage: type annotation gaps, f-string SPARQL injection risks, sync/async boundary violations, and FastAPI-specific pattern inconsistencies.

## Steps

1. Type safety: `rg "^def |^    def " backend/app/ -n | rg -v "->"` to find functions without return type annotations. Sample 10 modules to estimate annotation coverage percentage for routers vs services vs utilities.
2. SPARQL construction: `rg 'f".*(?:SELECT|INSERT|DELETE|CONSTRUCT|ASK)' backend/app/ -n` and `rg "f'.*(?:SELECT|INSERT|DELETE|CONSTRUCT|ASK)'" backend/app/ -n` to find all f-string SPARQL. Check whether any shared escaping/parameterization utility exists.
3. Check for SQL injection patterns: `rg 'f".*(?:SELECT|INSERT|UPDATE|DELETE).*FROM' backend/app/ -n` for raw SQL (vs SQLAlchemy ORM usage).
4. Async boundary: `rg "^def [a-z]" backend/app/*/router*.py -n` to find sync functions in async router modules. `rg "time\.sleep|open\(" backend/app/ -n` in async-capable modules for blocking calls.
5. FastAPI patterns: check Depends() consistency across routers, router prefix conventions, response_model usage, status code annotation coverage.
6. Check Pydantic model patterns: `rg "class.*BaseModel" backend/app/ -n` to find all Pydantic models. Check for any using dict() instead of model_dump().
7. Check for deprecated patterns: `rg "\.dict\(\)" backend/app/ -n` (Pydantic v1 pattern).
8. Append Type Safety, SPARQL Construction, Async Patterns, and FastAPI Patterns sections to findings doc.

## Must-Haves

- [ ] All f-string SPARQL construction sites identified
- [ ] Type annotation coverage estimated for each layer (routers, services, utilities)
- [ ] Any blocking calls in async contexts flagged

## Verification

- `grep -c "^### " .gsd/milestones/M041/S01-BACKEND-FINDINGS.md` returns >= 8

## Inputs

- `.gsd/milestones/M041/S01-BACKEND-FINDINGS.md` — append to existing findings doc
- `backend/app/` — all Python source modules

## Expected Output

- `.gsd/milestones/M041/S01-BACKEND-FINDINGS.md` — complete with all 8 backend dimension sections
