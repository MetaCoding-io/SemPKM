---
id: T01
parent: S02
milestone: M002
provides:
  - Deterministic validation report IRIs via hashlib.sha256 fallback
key_files:
  - backend/app/validation/report.py
key_decisions:
  - Used SHA-256 hex digest for fallback IRI — produces 64-char hex suffix, deterministic across processes and restarts
patterns_established:
  - none
observability_surfaces:
  - none
duration: 5m
verification_result: passed
completed_at: 2026-03-12
blocker_discovered: false
---

# T01: Stabilize validation report IRI with hashlib

**Replaced `hash()` with `hashlib.sha256().hexdigest()` in the `report_iri` fallback path, producing stable deterministic IRIs across process restarts.**

## What Happened

The `report_iri` property on `ValidationReport` had two paths: a primary path extracting a UUID from `urn:sempkm:event:` prefixed IRIs, and a fallback using Python's `hash()` for non-standard event IRIs. Since Python 3.3+, `hash()` is randomized per-process via `PYTHONHASHSEED`, making fallback IRIs non-deterministic across restarts.

Fixed by:
1. Adding `import hashlib` to the imports
2. Replacing `hash(self.event_iri)` with `hashlib.sha256(self.event_iri.encode()).hexdigest()`

The primary path (extracting UUID from `urn:sempkm:event:` prefix) is unchanged.

## Verification

Ran inline Python via `docker compose exec api`:

- **Fallback determinism**: Created a `ValidationReport` with `event_iri='http://example.org/custom/123'`, called `report_iri` twice — identical results ✅
- **Prefix present**: IRI starts with `urn:sempkm:validation:` ✅
- **Hex-only suffix**: All characters after the last `:` are `[0-9a-f]` ✅
- **Primary path unchanged**: `urn:sempkm:event:abc-123` → `urn:sempkm:validation:abc-123` ✅
- **SHA-256 consistency**: Output matches independently computed `hashlib.sha256(...).hexdigest()` ✅

Slice-level verification (partial — T01 only):
- COR-01 inline assertions: **PASS**
- COR-02 inline assertions: not yet (T02)
- COR-03 structural check: not yet (T03)
- Docker build: not yet (run after all fixes)
- E2E tests: not yet (run after all fixes)

## Diagnostics

None — this is a pure function fix. The fallback branch is the second return statement in the `report_iri` property. Failure would manifest as non-deterministic IRIs (detectable by comparing two calls with the same input).

## Deviations

None.

## Known Issues

None.

## Files Created/Modified

- `backend/app/validation/report.py` — Added `import hashlib`; replaced `hash(self.event_iri)` with `hashlib.sha256(self.event_iri.encode()).hexdigest()` in `report_iri` fallback
