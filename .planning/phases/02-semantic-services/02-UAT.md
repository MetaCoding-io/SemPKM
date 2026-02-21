---
status: complete
phase: 02-semantic-services
source: [02-01-SUMMARY.md, 02-02-SUMMARY.md]
started: 2026-02-21T19:40:00Z
updated: 2026-02-21T19:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. PrefixRegistry expand/compact round-trip
expected: Run `docker compose exec api python -c "from app.services.prefixes import PrefixRegistry; r = PrefixRegistry(); print(r.expand('dcterms:title')); print(r.compact('http://purl.org/dc/terms/title'))"` — expand returns full IRI, compact returns QName
result: pass

### 2. LabelService IRI fallback to QName
expected: Run `docker compose exec api python -c "import asyncio; from app.services.labels import LabelService; from app.services.prefixes import PrefixRegistry; from app.triplestore.client import TriplestoreClient; from app.config import settings; c = TriplestoreClient(settings.triplestore_url, settings.repository_id); svc = LabelService(c, PrefixRegistry()); print(asyncio.run(svc.resolve('http://www.w3.org/1999/02/22-rdf-syntax-ns#type')))"` — should return 'rdf:type' (QName fallback since no label in triplestore)
result: pass

### 3. Create object via command API
expected: Run `curl -s -X POST http://localhost:8001/api/commands -H "Content-Type: application/json" -d '{"command":"object.create","params":{"type":"Note","properties":{"rdfs:label":"UAT Test Note"}}}'` — returns JSON with event_iri and the created object IRI, HTTP 200
result: pass

### 4. Validation polling endpoint returns report
expected: After creating an object (test 3), wait 2-3 seconds, then run `curl -s http://localhost:8001/api/validation/latest | python3 -m json.tool` — returns JSON with conforms field (should be true with no shapes installed), plus violation_count, warning_count, info_count, timestamp, event_iri
result: pass

### 5. Validation is non-blocking
expected: Run `time curl -s -X POST http://localhost:8001/api/commands -H "Content-Type: application/json" -d '{"command":"object.create","params":{"type":"Note","properties":{"rdfs:label":"Speed Test"}}}'` — command returns in well under 2 seconds (validation runs async in background, not in the request path)
result: pass

### 6. Per-event validation report
expected: From the event_iri returned in test 3 or 5 (e.g. urn:sempkm:event:{uuid}), extract the UUID and run `curl -s http://localhost:8001/api/validation/{uuid}` — returns validation report for that specific event, or 404 if validation hasn't finished yet
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
