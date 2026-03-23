---
estimated_steps: 5
estimated_files: 4
skills_used:
  - test
  - best-practices
---

# T01: Build RDF parser module with format detection, subject extraction, and unit tests

**Slice:** S02 — RDF Data Import Wizard
**Milestone:** M039

## Description

Build the core RDF parsing module that handles format detection, rdflib parsing with error capture, subject extraction with type/label/property-count grouping, top-level subject heuristic, and blank node skolemization. This is where all three key technical risks live (format detection for JSON-LD, consistent BNode mapping, typed literal preservation). Unit tests retire these risks immediately.

## Steps

1. **Create module structure and data models.** Create `backend/app/rdf_import/__init__.py` (empty) and `backend/app/rdf_import/models.py` with dataclasses:
   - `SubjectInfo(iri: str, types: list[str], label: str | None, property_count: int, is_blank_node: bool, triples: list[tuple])` — one parsed subject
   - `RdfParseResult(subjects: list[SubjectInfo], total_triples: int, format_used: str, errors: list[str], raw_graph: Graph | None)` — result of parsing
   - `RdfImportResult(created: int, skipped: int, errors: list[dict], duration_seconds: float)` — result of import execution

2. **Implement format detection heuristic** in `backend/app/rdf_import/parser.py`:
   - `detect_format(content: str, filename: str | None = None) -> str` — For file uploads: use `rdflib.util.guess_format(filename)` mapping `.jsonld`/`.json` → `json-ld`, `.ttl` → `turtle`, `.nt` → `nt`. For pasted text: strip whitespace, check `startswith('{')` or `startswith('[')` → `json-ld`; `startswith('@prefix')` or `startswith('@base')` → `turtle`; regex `^<[^>]+>\s+<[^>]+>` on first line → `nt`; fallback → `turtle`.
   - Accept optional `format_override: str | None` parameter — if set, return it directly.

3. **Implement RDF parsing with error capture** in `parser.py`:
   - `parse_rdf(content: str, format: str) -> RdfParseResult` — Call `Graph().parse(data=content, format=format)`, catch `Exception` and return `RdfParseResult(subjects=[], errors=[str(e)], ...)`. On success, call `extract_subjects()` and `skolemize_bnodes()`.
   - For `json-ld` format, rdflib requires the format string to be `"json-ld"` (with hyphen).

4. **Implement subject extraction and skolemization** in `parser.py`:
   - `extract_subjects(graph: Graph) -> list[SubjectInfo]` — Group all triples by subject. For each subject: extract `rdf:type` values, resolve label via precedence (`dcterms:title > rdfs:label > skos:prefLabel > schema:name > foaf:name > QName`), count distinct predicates, flag `is_blank_node`. Apply top-level subject heuristic: subjects that appear only in subject position (not object position, excluding rdf:type targets and vocabulary IRIs). If heuristic yields zero, show all subjects.
   - `skolemize_bnodes(graph: Graph) -> tuple[Graph, dict[BNode, URIRef]]` — Single pass over all triples, build `BNode → URIRef(urn:sempkm:import:{uuid4()})` mapping, reconstruct graph with all BNodes replaced in both subject AND object positions. Preserve namespace bindings.

5. **Write unit tests** in `backend/tests/test_rdf_import_parser.py`:
   - `test_detect_format_jsonld` — `{"@context": ...}` → `json-ld`
   - `test_detect_format_turtle` — `@prefix ex: <...>` → `turtle`
   - `test_detect_format_ntriples` — `<s> <p> "o" .` → `nt`
   - `test_detect_format_file_extension` — `.jsonld` → `json-ld`, `.ttl` → `turtle`, `.nt` → `nt`
   - `test_detect_format_override` — override always wins
   - `test_parse_valid_jsonld` — JSON-LD with 2 typed objects parses correctly
   - `test_parse_valid_turtle` — Turtle with `@prefix` and typed objects parses
   - `test_parse_valid_ntriples` — N-Triples format parses
   - `test_parse_invalid_returns_errors` — malformed Turtle returns error list, not exception
   - `test_extract_subjects_types_and_labels` — subjects have correct types, labels, property counts
   - `test_extract_subjects_top_level_heuristic` — nested blank node subjects excluded from top-level
   - `test_skolemize_consistency` — blank node used as both subject and object maps to same URI
   - `test_skolemize_iri_format` — skolemized IRIs start with `urn:sempkm:import:`
   - `test_skolemize_preserves_non_bnodes` — regular URIRefs unchanged after skolemization

## Must-Haves

- [ ] Format detection correctly identifies JSON-LD, Turtle, and N-Triples from pasted text
- [ ] File extension detection works for `.jsonld`, `.json`, `.ttl`, `.nt`
- [ ] `format_override` parameter bypasses heuristic
- [ ] Parse errors captured as strings in `RdfParseResult.errors`, never raised as exceptions
- [ ] Subject extraction groups by subject with correct type, label (precedence chain), and property count
- [ ] Top-level subject heuristic excludes nested structural blank nodes
- [ ] Blank node skolemization maps consistently across subject and object positions
- [ ] Skolemized IRIs use `urn:sempkm:import:{uuid}` format
- [ ] All unit tests pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_rdf_import_parser.py -v` — all tests pass
- `python -c "from app.rdf_import.parser import detect_format, parse_rdf, skolemize_bnodes; print('imports OK')"` — no import errors

## Inputs

- `backend/app/events/store.py` — `Operation` dataclass reference for `RdfImportResult` alignment
- `backend/app/obsidian/models.py` — `ImportResult` pattern reference for result dataclass design

## Expected Output

- `backend/app/rdf_import/__init__.py` — module init
- `backend/app/rdf_import/parser.py` — format detection, parsing, subject extraction, skolemization
- `backend/app/rdf_import/models.py` — `SubjectInfo`, `RdfParseResult`, `RdfImportResult` dataclasses
- `backend/tests/test_rdf_import_parser.py` — unit tests for all parser functions

## Observability Impact

- **Structured logging:** `parser.py` emits `logger.info` on successful parse (format, triple count, subject count) and `logger.warning` on parse failure (format, error message). Searchable via `rdf_import.parser` logger name.
- **Inspection:** `RdfParseResult.errors` captures parse failures as strings — callers can surface them to users without try/catch. `SubjectInfo.triples` carries raw triple data for downstream SHACL validation and import execution.
- **Future agent debugging:** Run `cd backend && .venv/bin/python -m pytest tests/test_rdf_import_parser.py -v` to verify parser integrity. Import the module directly to test format detection: `from app.rdf_import.parser import detect_format; detect_format('...')`.
