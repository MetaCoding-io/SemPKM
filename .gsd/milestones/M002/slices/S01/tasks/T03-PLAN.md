---
estimated_steps: 3
estimated_files: 1
---

# T03: Document BASE_NAMESPACE production guidance

**Slice:** S01 — Security Hardening
**Milestone:** M002

## Description

Add a "Namespace Configuration" section to the production deployment guide explaining what `BASE_NAMESPACE` does, why the default `https://example.org/data/` is dangerous in production (IRI collisions across instances), and how to set it correctly. Add `BASE_NAMESPACE` to the production checklist.

## Steps

1. In `docs/guide/20-production-deployment.md`: add a new `## Namespace Configuration` section before `## Production Checklist`. Explain: what BASE_NAMESPACE controls (the IRI prefix for all objects and named graphs), what happens if left as default (all instances share the same IRI space → data collisions during federation or data migration), recommended pattern (e.g. `https://yourdomain.com/data/`), and that it should be set before creating any data (changing it later orphans existing objects).
2. Add `- [ ] \`BASE_NAMESPACE\` set to your domain (not the default \`example.org\`)` to the production checklist, after the SECRET_KEY item.
3. Verify the section exists and is correctly placed by checking heading order and grep output.

## Must-Haves

- [ ] "Namespace Configuration" section exists in the production deployment guide
- [ ] Section explains the IRI collision risk of the default namespace
- [ ] Section explains that BASE_NAMESPACE should be set before creating data
- [ ] `BASE_NAMESPACE` appears in the production checklist

## Verification

- `grep -c 'BASE_NAMESPACE' docs/guide/20-production-deployment.md` — returns ≥3
- `grep -A1 'Namespace Configuration' docs/guide/20-production-deployment.md` — section heading exists
- `grep 'BASE_NAMESPACE' docs/guide/20-production-deployment.md | grep -i 'checklist\|example.org\|collision\|set'` — content covers the key topics

## Observability Impact

- Signals added/changed: None (documentation only)
- How a future agent inspects this: read the production deployment guide
- Failure state exposed: None

## Inputs

- `docs/guide/20-production-deployment.md` — existing production guide with checklist at the bottom
- `backend/app/config.py` — default `base_namespace = "https://example.org/data/"` for reference
- S01-RESEARCH.md — notes on what to document

## Expected Output

- `docs/guide/20-production-deployment.md` — updated with Namespace Configuration section and checklist item
