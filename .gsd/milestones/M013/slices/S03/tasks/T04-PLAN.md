---
estimated_steps: 4
estimated_files: 4
---

# T04: User guide documentation

**Slice:** S03 — Context-Query, E2E Tests, and User Guide
**Milestone:** M013

## Description

Write user guide Chapter 31 documenting the API surface for extension and integration developers. Covers all four endpoints with request/response examples, authentication methods, and CORS behavior.

## Steps

1. Create `docs/guide/31-api-surface.md` with sections:
   - **Overview** — What the API surface is for, who it's for (browser extensions, mobile apps, integrations)
   - **Authentication** — Two methods: session cookies (for web UI) and Bearer API tokens (for external clients). How to generate an API key from Settings.
   - **Instance Discovery** — `GET /.well-known/sempkm`: purpose, example request, example response JSON, field descriptions
   - **Available Types** — `GET /api/types`: purpose, example response, field descriptions (iri, label, icon, model)
   - **SHACL Shapes** — `GET /api/shapes/{type_iri}`: purpose, URL encoding note, example response, property field descriptions (path, name, datatype, constraints, groups, helptext)
   - **Context Query** — `POST /api/context-query`: purpose, request body fields, matching behavior (URL exact match + FTS keywords), example request/response
   - **CORS** — Browser extension cross-origin access, `Access-Control-Allow-Origin: *`
   - **Error Responses** — Standard error format (401, 403, 404, 400)
2. Update `docs/guide/README.md` — add Chapter 31 to table of contents
3. Update `docs/guide/30-personas.md` — navigation footer link to Chapter 31
4. Update `docs/guide/appendix-d-glossary.md` — add entries for "API Surface", "Context Query", "Instance Discovery"

## Must-Haves

- [ ] All four endpoints documented with request/response examples
- [ ] Authentication section covers both session and Bearer token methods
- [ ] Linked in README TOC and navigation chain
- [ ] Glossary entries added

## Verification

- `ls docs/guide/31-api-surface.md` — file exists
- `grep "31" docs/guide/README.md` — chapter in TOC
- `grep "API Surface\|Context Query\|Instance Discovery" docs/guide/appendix-d-glossary.md` — glossary entries exist

## Inputs

- `backend/app/api/router.py` — endpoint implementations for accurate documentation
- `docs/guide/30-personas.md` — preceding chapter for navigation link
- `docs/guide/README.md` — table of contents

## Expected Output

- `docs/guide/31-api-surface.md` — complete guide chapter
- `docs/guide/README.md` — updated TOC
- `docs/guide/30-personas.md` — updated navigation footer
- `docs/guide/appendix-d-glossary.md` — 3 new entries

## Observability Impact

This task is documentation-only and does not change runtime behavior.

- **No new runtime signals**: No endpoints, logs, or metrics are added or modified.
- **Inspection**: Verify documentation accuracy by comparing endpoint examples against `backend/app/api/router.py` response models.
- **Failure visibility**: Broken internal links in the guide can be detected by checking that all `](*.md)` references resolve to existing files in `docs/guide/`.
