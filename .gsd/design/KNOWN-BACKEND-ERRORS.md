# Known Backend Errors — Imported Data Quality & Validation

> Captured: 2026-03-13 during M003 testing
> Status: **Open** — queue for future data quality / import robustness milestone

## Error 1: Invalid ISO datetime strings from Obsidian import

**Severity:** Warning (non-fatal, logged by rdflib)  
**Source:** `rdflib.term._castLexicalToPython`  
**Root cause:** Obsidian import produced literals typed as `xsd:dateTime` that contain
text after the date portion (likely Obsidian note titles concatenated with dates during
the import mapping).

**Example error messages:**
```
WARNI [rdflib.term] Failed to convert Literal lexical form to value.
Datatype=http://www.w3.org/2001/XMLSchema#dateTime

ValueError: Invalid isoformat string: '2020-04-17 Event on Dataview w Tres Brenan'
ValueError: Invalid isoformat string: '2015-02-20 Habit Concepts and Theory'
ValueError: Invalid isoformat string: "2025-04-10 Emily's event for the LYT Community"
ValueError: Invalid isoformat string: '2025-04-10 Showcase the enhanced mobile experience with the LYT Wayfinders'
ValueError: Invalid isoformat string: '2023-11-28 LYT Team'
ValueError: Invalid isoformat string: '2023-11-29 LYT Team'
ValueError: Invalid isoformat string: '2024-07-12 LYT Team'
ValueError: Invalid isoformat string: '2025-04-07 Team Mtg'
ValueError: Invalid isoformat string: '2025-04-14 Mtg w Team'
ValueError: Invalid isoformat string: '2025-11-23 Mtg w LYT Team on IDV Pro 2.5 Launch'
```

**Fix options:**
1. Import sanitization: strip non-date text from datetime fields during import
2. Post-import data migration: SPARQL UPDATE to fix malformed dateTime literals
3. Defensive parsing: extract leading `YYYY-MM-DD` from strings that start with a valid date
4. Lint rule: flag objects with malformed dateTime values in the LINT panel

---

## Error 2: Validation store 415 Unsupported Media Type

**Severity:** Error (validation report not persisted to triplestore)  
**Source:** `app.validation.queue._worker` → `app.services.validation.validate` → `_store_report`  
**Root cause:** The validation service tries to store SHACL validation reports as RDF
in the triplestore, but the POST to `/rdf4j-server/repositories/sempkm/statements`
returns HTTP 415 (Unsupported Media Type), likely a content-type header mismatch.

**Error message:**
```
ERROR [app.validation.queue] Validation failed for event urn:sempkm:event:bebdf390-2184-48cb-907f-b519edcd0617
Traceback (most recent call last):
  File "/app/app/validation/queue.py", line 128, in _worker
    report = await self._validation_service.validate(...)
  File "/app/app/services/validation.py", line 116, in validate
    await self._store_report(report, results_graph=results_graph, trigger_source=trigger_source)
  ...
  File "/app/.venv/lib/python3.12/site-packages/httpx/_models.py", line 829, in raise_for_status
    raise HTTPStatusError(message, request=request, response=self)
httpx.HTTPStatusError: Client error '415 ' for url 'http://triplestore:8080/rdf4j-server/repositories/sempkm/statements'
```

**Fix options:**
1. Check Content-Type header in `_store_report()` — likely needs `application/x-turtle` or `application/n-triples`
2. May be a RDF4J version compatibility issue with the serialization format
3. Validation itself succeeds (lint shows "all pass") — only the report persistence fails
