---
estimated_steps: 3
estimated_files: 1
---

# T01: Stabilize validation report IRI with hashlib

**Slice:** S02 — Correctness Fixes
**Milestone:** M002

## Description

Replace Python's non-deterministic `hash()` with `hashlib.sha256` in the fallback path of `ValidationReport.report_iri`. Python 3.3+ randomizes `hash()` per-process via `PYTHONHASHSEED`, so validation report IRIs constructed via the fallback become unreachable after a process restart. The fix is a one-line change plus an import.

## Steps

1. Read `backend/app/validation/report.py` to confirm the exact fallback line (line ~175)
2. Add `import hashlib` to the imports section
3. Replace `hash(self.event_iri)` with `hashlib.sha256(self.event_iri.encode()).hexdigest()` in the `report_iri` property fallback
4. Verify by running inline Python that exercises the fallback path with a non-standard event IRI

## Must-Haves

- [ ] `hashlib` imported at top of file
- [ ] Fallback uses `hashlib.sha256(self.event_iri.encode()).hexdigest()` instead of `hash(self.event_iri)`
- [ ] Primary path (extracting UUID from `urn:sempkm:event:` prefix) is unchanged

## Verification

- Run: `docker compose exec backend python -c "from app.validation.report import ValidationReport; r = ValidationReport(event_iri='http://example.org/custom/123', conforms=True, results=[], timestamp='2026-01-01T00:00:00Z'); iri1 = r.report_iri; iri2 = r.report_iri; assert iri1 == iri2, 'IRIs differ'; assert 'urn:sempkm:validation:' in iri1, 'Missing prefix'; assert all(c in '0123456789abcdef' for c in iri1.split(':')[-1]), f'Non-hex chars in {iri1}'; print(f'OK: {iri1}')"`
- Confirm the primary path still works: event IRI `urn:sempkm:event:abc-123` → `urn:sempkm:validation:abc-123`

## Observability Impact

- Signals added/changed: None
- How a future agent inspects this: Read the `report_iri` property — the fallback branch is the second return statement
- Failure state exposed: None (fix eliminates the non-determinism failure mode)

## Inputs

- `backend/app/validation/report.py` — current implementation with `hash()` at line ~175

## Expected Output

- `backend/app/validation/report.py` — fallback IRI uses `hashlib.sha256().hexdigest()`, producing stable deterministic IRIs across process restarts
