---
id: T01
parent: S02
milestone: M039
provides:
  - RDF parser module with format detection, subject extraction, blank node skolemization
  - Unit tests covering all parser functions (29 tests)
key_files:
  - backend/app/rdf_import/__init__.py
  - backend/app/rdf_import/models.py
  - backend/app/rdf_import/parser.py
  - backend/tests/test_rdf_import_parser.py
key_decisions: []
patterns_established:
  - SubjectInfo/RdfParseResult/RdfImportResult dataclass trio follows Obsidian ImportResult pattern
  - _LABEL_PREDICATES list for label resolution precedence (dcterms:title > rdfs:label > skos:prefLabel > schema:name > foaf:name > QName)
  - Top-level subject heuristic filters out BNodes/IRIs that appear only as objects
observability_surfaces:
  - Structured logging via rdf_import.parser logger (info on parse success, warning on failure)
  - RdfParseResult.errors captures parse failures as strings for user-facing display
duration: 15m
verification_result: passed
completed_at: 2026-03-22
blocker_discovered: false
---

# T01: Build RDF parser module with format detection, subject extraction, and unit tests

**Built RDF import parser with format detection (JSON-LD, Turtle, N-Triples), subject extraction with label precedence and top-level heuristic, blank node skolemization, and 29 passing unit tests.**

## What Happened

Created the `backend/app/rdf_import/` module with three files:

1. **models.py** — `SubjectInfo`, `RdfParseResult`, and `RdfImportResult` dataclasses. `RdfImportResult` includes a `to_dict()` method following the Obsidian `ImportResult` pattern.

2. **parser.py** — Four public functions:
   - `detect_format()` — Three-tier resolution: override → filename extension (via `rdflib.util.guess_format`) → content heuristic (`{`/`[` for JSON-LD, `@prefix`/`@base`/`PREFIX` for Turtle, `<IRI> <IRI>` regex for N-Triples) → fallback to turtle.
   - `parse_rdf()` — Wraps `Graph.parse()` with full error capture (never raises). On success, calls `extract_subjects()` to return structured results.
   - `extract_subjects()` — Groups triples by subject, resolves types via `rdf:type`, resolves labels via the 5-predicate precedence chain + QName fallback, counts distinct predicates. Applies top-level heuristic: subjects not appearing in object position (excluding `rdf:type` targets and vocab IRIs) are considered top-level. Falls back to all subjects if heuristic yields nothing.
   - `skolemize_bnodes()` — Single-pass BNode→`urn:sempkm:import:{uuid4}` mapping applied consistently in both subject and object positions. Preserves namespace bindings.

3. **tests/test_rdf_import_parser.py** — 29 tests across 7 test classes covering format detection (text, file extension, override), parsing (valid JSON-LD/Turtle/N-Triples, invalid input), subject extraction (types, labels, precedence, QName fallback, top-level heuristic, mutual-reference fallback), and skolemization (consistency, IRI format, non-BNode preservation, namespace bindings, multiple BNodes).

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rdf_import_parser.py -v` — 29/29 passed
- `cd backend && .venv/bin/python -c "from app.rdf_import.parser import detect_format, parse_rdf, skolemize_bnodes; print('imports OK')"` — imports OK

## Verification Evidence

| # | Command | Exit Code | Verdict | Duration |
|---|---------|-----------|---------|----------|
| 1 | `cd backend && .venv/bin/python -m pytest tests/test_rdf_import_parser.py -v` | 0 | ✅ pass | 0.12s |
| 2 | `cd backend && .venv/bin/python -c "from app.rdf_import.parser import detect_format, parse_rdf, skolemize_bnodes; print('imports OK')"` | 0 | ✅ pass | <1s |

## Diagnostics

- **Parser health:** `cd backend && .venv/bin/python -m pytest tests/test_rdf_import_parser.py -v`
- **Quick format check:** `cd backend && .venv/bin/python -c "from app.rdf_import.parser import detect_format; print(detect_format('{\"@context\": {}}'))"`
- **Logger:** `rdf_import.parser` — emits INFO on successful parse (format, triple/subject counts), WARNING on parse failure

## Deviations

- Added `PREFIX` (SPARQL-style uppercase) as a Turtle detection signal — the plan only mentioned `@prefix`/`@base` but the uppercase variant is common in real-world Turtle files.
- Added `to_dict()` on `RdfImportResult` to align with the Obsidian `ImportResult` serialization pattern.

## Known Issues

- rdflib 7.6.0 emits a `DeprecationWarning` about `ConjunctiveGraph` during JSON-LD parsing — this is upstream and doesn't affect functionality.

## Files Created/Modified

- `backend/app/rdf_import/__init__.py` — module init with docstring
- `backend/app/rdf_import/models.py` — SubjectInfo, RdfParseResult, RdfImportResult dataclasses
- `backend/app/rdf_import/parser.py` — detect_format, parse_rdf, extract_subjects, skolemize_bnodes
- `backend/tests/test_rdf_import_parser.py` — 29 unit tests across 7 test classes
- `.gsd/milestones/M039/slices/S02/tasks/T01-PLAN.md` — added Observability Impact section
