# Phase 43: Inference E2E Test Gap - Research

**Researched:** 2026-03-06
**Domain:** Inference bug fix + Playwright E2E testing
**Confidence:** HIGH

## Summary

Phase 43 addresses two tightly coupled issues: (1) a bug in `_store_inferred_triples` that causes SPARQL 400 errors when processing triples with Literal objects (produced by rdfs:domain/rdfs:range entailment), and (2) a missing E2E test that verifies the full inference user story -- create a one-sided relationship, run inference, see the inverse triple appear.

The bug is in `backend/app/inference/service.py` line 495, where all triple components are wrapped as `<{value}>` (URI syntax). When owlrl produces triples where the object is an rdflib `Literal` (e.g., from `rdfs:range xsd:string` producing `?val rdf:type xsd:string`), the resulting SPARQL like `<active>` is invalid and the triplestore returns 400. The fix is straightforward: filter out triples with Literal subjects/objects before storing, since those are schema-level assertions not useful for user-facing inference.

The E2E test gap exists because seed data pre-populates both sides of all `owl:inverseOf` relationships (every `hasParticipant` has a matching `participatesIn`), so running inference on seed data produces 0 new owl:inverseOf triples. The test must create a new one-sided relationship via the command API and verify inference materializes the inverse.

**Primary recommendation:** Fix the Literal-in-SPARQL bug with a type check filter, then add a single focused E2E test that creates a fresh `hasParticipant` triple (via `object.patch`), runs inference, and asserts the inverse `participatesIn` triple appears in the API response.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| TEST-05 | Playwright E2E tests cover all v2.4 user-visible features (inference bidirectional links, lint dashboard filtering/sorting, edit form helptext, bug fix verifications) | Bug fix enables inference to run cleanly; new E2E test covers the "create edge -> run inference -> inverse appears" flow that existing tests miss |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Playwright | (from e2e/package.json) | E2E browser testing | Already used for all SemPKM E2E tests |
| rdflib | (from backend requirements) | RDF triple handling | Already used in inference service |
| owlrl | 7.1.4 | OWL 2 RL forward-chaining | Already integrated in inference pipeline |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| Playwright request API | built-in | Direct API calls for test arrangement | Creating objects, triggering inference, asserting results |

## Architecture Patterns

### Bug Fix Pattern: Literal Filtering in _store_inferred_triples

The core bug is at `service.py:495`:
```python
triple_lines.append(f"  <{s}> <{p}> <{o}> .")
```

This treats all triple components as URIs. owlrl's rdfs:domain/rdfs:range entailment produces triples like:
- `"active" rdf:type xsd:string` (subject is a Literal)
- Or other triples where subject or object is a Literal

The BNode filter at step 6 (line 175) only checks `isinstance(s, BNode)`, not `isinstance(s, Literal)`.

**Fix approach:** Add a Literal filter alongside the BNode filter, or add it in `_store_inferred_triples` itself. The cleanest approach is to extend the existing BNode filter at step 6:

```python
from rdflib import Literal

new_triples = {
    (s, p, o)
    for s, p, o in new_triples
    if not isinstance(s, BNode) and not isinstance(o, BNode)
    and not isinstance(s, Literal) and not isinstance(o, Literal)
}
```

**Why filter Literals entirely:** Inferred triples with Literal subjects/objects are schema-level type assertions (e.g., "the string 'active' is of type xsd:string"). These are:
1. Not meaningful to users as inference results
2. Not storable as `<uri>` in SPARQL INSERT DATA
3. Would require N-Triples literal serialization (`"value"^^<datatype>`) which adds complexity for zero user value

### E2E Test Pattern: API-Driven Inference Flow

The test should use the API directly (not UI interactions) for reliability:

1. **Arrange:** Create a new Person via `object.create`, then add `hasParticipant` to an existing Project via `object.patch` -- creating only ONE side of the inverse
2. **Act:** Call `POST /api/inference/run` to trigger inference
3. **Assert:** Call `GET /api/inference/triples` and verify an `owl:inverseOf` triple appears linking the new Person back to the Project via `participatesIn`

**Why object.patch, not edge.create:** The `edge.create` command creates reified edge resources (`sempkm:Edge` with `sempkm:source`, `sempkm:target`, `sempkm:predicate` triples). The inference engine reads direct triples from `urn:sempkm:current` and does NOT dereference reified edges. Only `object.patch` creates direct triples like `<project> <hasParticipant> <person>` that owlrl can reason over.

**Why API-driven:** The inference panel UI tests already exist (infrastructure verification). The gap is specifically the data-level flow. API tests are faster, more deterministic, and directly verify the backend logic.

### Seed Data Constraint

The seed data has both sides pre-populated:
- Project "SemPKM Development" has `bpkm:hasParticipant` pointing to Alice and Bob
- Alice and Bob both have `bpkm:participatesIn` pointing back to SemPKM Development
- Same pattern for Carol/Knowledge Garden

So `owl:inverseOf` inference produces 0 new triples on seed data. The test MUST create a net-new one-sided relationship.

### Anti-Patterns to Avoid
- **Do NOT use edge.create for inference testing:** Reified edges are invisible to owlrl. Only direct triples work.
- **Do NOT rely on UI for the inference flow test:** The UI test for panel infrastructure already exists. This test needs to verify DATA correctness.
- **Do NOT enable rdfs:domain/rdfs:range entailment without the bug fix:** It will cause SPARQL 400 errors and break the inference run.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Literal detection | Custom string parsing | `isinstance(x, rdflib.Literal)` | rdflib's type system handles all edge cases |
| API auth in tests | Manual cookie management | Existing `ownerSessionToken` fixture | Already handles setup, login, cookie injection |
| SPARQL assertions | Raw SPARQL queries in tests | `/api/inference/triples` endpoint | Already returns structured JSON with filters |

## Common Pitfalls

### Pitfall 1: Seed Data Masks the Bug
**What goes wrong:** Running inference on seed data returns 0 new triples, making it seem like inference "works" when in reality the owl:inverseOf path is never tested.
**Why it happens:** Both sides of every inverse relationship are pre-populated in `seed/basic-pkm.jsonld`.
**How to avoid:** The E2E test MUST create a fresh one-sided relationship that does not exist in seed data.
**Warning signs:** `total_inferred: 0` with `owl:inverseOf` enabled.

### Pitfall 2: rdfs:domain/rdfs:range Entailment is Disabled by Default
**What goes wrong:** The bug in `_store_inferred_triples` only triggers when rdfs:domain/rdfs:range produces Literal-subject triples, but this entailment is disabled in the manifest defaults (`rdfs_domain_range: false`).
**Why it happens:** The manifest `entailment_defaults` for basic-pkm disables rdfs:domain/rdfs:range.
**How to avoid:** Fix the bug defensively (filter Literals regardless of config), but do NOT need to enable rdfs:domain/rdfs:range for the E2E test -- owl:inverseOf is sufficient.
**Warning signs:** Bug only manifests when `rdfs_domain_range: true` is explicitly set.

### Pitfall 3: object.patch Replaces ALL Values for a Predicate
**What goes wrong:** Using `object.patch` to add a `hasParticipant` to a project will DELETE all existing `hasParticipant` values (Alice, Bob) and replace them with only the new value.
**Why it happens:** `object_patch.py` line 47 creates `materialize_deletes` with a Variable pattern that removes ALL old values for the predicate.
**How to avoid:** Either (a) create a brand new Project first, then patch its `hasParticipant`, or (b) use the existing create-edge test's freshly created objects.
**Warning signs:** Seed data relationships disappear after patch.

### Pitfall 4: Test Ordering Dependencies
**What goes wrong:** The inference test depends on objects created in earlier test files if it reuses them.
**Why it happens:** Tests run sequentially (1 worker) and share Docker state.
**How to avoid:** Create fresh objects within the inference test itself. Do not depend on objects from other test suites.

## Code Examples

### Bug Fix: Filter Literals from Inferred Triples

```python
# In service.py, modify step 6 (around line 174-179)
# Current:
new_triples = {
    (s, p, o)
    for s, p, o in new_triples
    if not isinstance(s, BNode) and not isinstance(o, BNode)
}

# Fixed (add Literal filter):
from rdflib import Literal

new_triples = {
    (s, p, o)
    for s, p, o in new_triples
    if not isinstance(s, BNode) and not isinstance(o, BNode)
    and not isinstance(s, Literal) and not isinstance(o, Literal)
}
```

### E2E Test: Inference Flow

```typescript
test('create relationship and verify inference materializes inverse', async ({ ownerPage, ownerSessionToken }) => {
  const api = ownerPage.context().request;
  const headers = { Cookie: `sempkm_session=${ownerSessionToken}` };

  // 1. Create a fresh Project and Person
  const createResp = await api.post(`${BASE_URL}/api/commands`, {
    headers,
    data: [
      {
        command: 'object.create',
        params: {
          type: 'Project',
          properties: { 'http://purl.org/dc/terms/title': 'Inference Test Project' },
        },
      },
      {
        command: 'object.create',
        params: {
          type: 'Person',
          properties: { 'http://xmlns.com/foaf/0.1/name': 'Inference Test Person' },
        },
      },
    ],
  });
  const createData = await createResp.json();
  const projectIri = createData.results[0].iri;
  const personIri = createData.results[1].iri;

  // 2. Add hasParticipant (one side only) via object.patch
  const patchResp = await api.post(`${BASE_URL}/api/commands`, {
    headers,
    data: {
      command: 'object.patch',
      params: {
        iri: projectIri,
        properties: {
          'urn:sempkm:model:basic-pkm:hasParticipant': personIri,
        },
      },
    },
  });
  expect(patchResp.ok()).toBeTruthy();

  // 3. Run inference
  const inferResp = await api.post(`${BASE_URL}/api/inference/run`, { headers });
  expect(inferResp.ok()).toBeTruthy();
  const inferData = await inferResp.json();

  // 4. Verify inverse triple was inferred
  expect(inferData.total_inferred).toBeGreaterThan(0);

  const triplesResp = await api.get(`${BASE_URL}/api/inference/triples`, { headers });
  const triples = await triplesResp.json();

  // Find the participatesIn inverse triple
  const inverseTriple = triples.find(
    (t: any) =>
      t.subject === personIri &&
      t.predicate.includes('participatesIn') &&
      t.object === projectIri
  );
  expect(inverseTriple).toBeTruthy();
  expect(inverseTriple.entailment_type).toBe('owl:inverseOf');
});
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Test only infrastructure (panel UI, API endpoints) | Test full data flow (create -> infer -> verify) | Phase 43 | Validates inference actually works end-to-end |
| All triple objects treated as URIs | Filter Literals before SPARQL INSERT | Phase 43 | Prevents SPARQL 400 errors with rdfs:domain/rdfs:range |

## Open Questions

1. **object.patch value format for object properties**
   - What we know: `object.patch` accepts `properties: { predicate: value }` and `_to_rdf_value()` converts values
   - What's unclear: Does passing a raw IRI string like `"urn:sempkm:model:basic-pkm:seed-person-alice"` get correctly converted to a `URIRef`? Or does it become a Literal string?
   - Recommendation: Check `_to_rdf_value()` implementation. If it treats plain strings as Literals, may need to use a different format or directly use SPARQL INSERT to create the test triple.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Playwright (from e2e/package.json) |
| Config file | `e2e/playwright.config.ts` |
| Quick run command | `cd e2e && npx playwright test tests/09-inference/ --project=chromium` |
| Full suite command | `cd e2e && npx playwright test --project=chromium` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEST-05 (inference flow) | Create relationship -> run inference -> inverse appears | e2e (API) | `cd e2e && npx playwright test tests/09-inference/ --project=chromium` | Partial (infrastructure only) |
| TEST-05 (bug fix) | _store_inferred_triples handles Literals without SPARQL error | e2e (implicit) | Covered by inference run not returning 500 | No dedicated test |

### Sampling Rate
- **Per task commit:** `cd e2e && npx playwright test tests/09-inference/ --project=chromium`
- **Per wave merge:** `cd e2e && npx playwright test --project=chromium`
- **Phase gate:** Inference tests pass + no SPARQL 400 errors in API logs

### Wave 0 Gaps
- None -- existing test infrastructure (fixtures, helpers, config) covers all needs. Only new test code within existing `09-inference/inference.spec.ts` is required.

## Sources

### Primary (HIGH confidence)
- `backend/app/inference/service.py` -- Bug location at line 495 (`_store_inferred_triples`), Literal filter gap at line 174-179
- `models/basic-pkm/ontology/basic-pkm.jsonld` -- `owl:inverseOf` between `participatesIn` and `hasParticipant`
- `models/basic-pkm/seed/basic-pkm.jsonld` -- Both inverse sides pre-populated in seed data
- `models/basic-pkm/manifest.yaml` -- `rdfs_domain_range: false` default, `owl_inverseOf: true`
- `e2e/tests/09-inference/inference.spec.ts` -- Existing tests cover infrastructure, NOT data flow
- `backend/app/commands/handlers/edge_create.py` -- Creates reified edges, NOT direct triples
- `backend/app/commands/handlers/object_patch.py` -- Creates direct triples, replaces all values for predicate
- `backend/app/inference/entailments.py` -- Classification and filter logic

### Secondary (MEDIUM confidence)
- `e2e/tests/01-objects/create-edge.spec.ts` -- Pattern for API-driven edge/object creation in tests

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - All tools already in use, no new dependencies
- Architecture: HIGH - Bug root cause identified from source code analysis
- Pitfalls: HIGH - Seed data masking verified by reading actual data files

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable -- internal code, no external dependency changes)
