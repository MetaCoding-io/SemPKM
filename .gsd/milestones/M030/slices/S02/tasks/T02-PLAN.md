---
estimated_steps: 6
estimated_files: 2
---

# T02: Write per-rule tests and update cross-model expected counts

**Slice:** S02 — Data Quality Rules (9 new SHACL-AF rules)
**Milestone:** M030

## Description

Write `test_data_quality_rules.py` with isolated positive and negative tests for each of the 9 new SHACL-AF rules, then update the `EXPECTED_PYSHACL` dict in `test_cross_model_validation.py` to reflect the new rules firing against existing seed data.

Each test follows the pattern from `test_basic_pkm_v2.py::test_pyshacl_no_warning_for_done_or_future_tasks`: create a minimal rdflib Graph with synthetic data, load the relevant rules file as shapes_graph, run pyshacl with `advanced=True, allow_infos=True, allow_warnings=True`, and assert the correct number/severity of results.

## Steps

1. **Create `backend/tests/test_data_quality_rules.py`** with module-level constants for model paths and namespaces (SH, BPKM, ZK, PPV, RES, DCTERMS, XSD, RDF, RDFS, SKOS, FOAF, SCHEMA).

2. **Write a shared helper `_run_rule_test(data_graph, rules_path, expected_warnings, expected_infos)`** that loads the rules file, runs pyshacl, and returns results for assertion. Pattern:
   ```python
   shapes_graph = Graph()
   shapes_graph.parse(str(rules_path), format="turtle")
   conforms, results_graph, results_text = pyshacl.validate(
       data_graph, shacl_graph=shapes_graph,
       advanced=True, allow_infos=True, allow_warnings=True,
   )
   warnings = list(results_graph.subjects(SH.resultSeverity, SH.Warning))
   infos = list(results_graph.subjects(SH.resultSeverity, SH.Info))
   return warnings, infos, results_text
   ```

3. **Write positive + negative test pairs for each rule** (9 pairs = 18 tests minimum):

   **Rule 1: comma-in-tags (Warning, basic-pkm)**
   - Positive: Object with `bpkm:tags "python, javascript"` → 1 warning
   - Negative: Object with `bpkm:tags "python"` and `bpkm:tags "javascript"` (separate triples) → 0 warnings

   **Rule 2: empty body for Note/Concept (Info, basic-pkm)**
   - Positive: `bpkm:Note` with no `<urn:sempkm:vocab:body>` triple → 1 info
   - Negative: `bpkm:Note` with `<urn:sempkm:vocab:body> "some text"` → 0 infos

   **Rule 3: concept with no definition (Info, basic-pkm)**
   - Positive: `bpkm:Concept` with no `skos:definition` → 1 info
   - Negative: `bpkm:Concept` with `skos:definition "..."` → 0 infos

   **Rule 4: titleless objects (Warning, basic-pkm)**
   - Positive: `bpkm:Note` with no dcterms:title/rdfs:label/skos:prefLabel/foaf:name → 1 warning
   - Negative: `bpkm:Note` with `dcterms:title "My Note"` → 0 warnings

   **Rule 5: orphan objects (Info, basic-pkm)**
   - Positive: `bpkm:Note` with only `rdf:type` triple → 1 info
   - Negative: `bpkm:Note` with outgoing edge to another typed object → 0 infos

   **Rule 6: duplicate URL (Info, basic-pkm)**
   - Positive: Two `bpkm:Note` objects both with `schema:url "https://example.com"` → 2 infos (one per object)
   - Negative: Two `bpkm:Note` objects with different `schema:url` values → 0 infos

   **Rule 7: empty body for zk note types (Info, zettelkasten)**
   - Positive: `zk:FleetingNote` with no body → 1 info
   - Negative: `zk:FleetingNote` with `<urn:sempkm:vocab:body> "..."` → 0 infos

   **Rule 8: stale project (Info, ppv)**
   - Positive: `ppv:Project` with no `dcterms:modified` → 1 info
   - Negative: `ppv:Project` with `dcterms:modified` set → 0 infos

   **Rule 9a: ActionItem no project (Warning, ppv)**
   - Positive: `ppv:ActionItem` with no `ppv:project` → 1 warning
   - Negative: `ppv:ActionItem` with `ppv:project` link → 0 warnings

   **Rule 9b: Project no goalOutcome (Warning, ppv)**
   - Positive: `ppv:Project` with no `ppv:goalOutcome` → 1 warning
   - Negative: `ppv:Project` with `ppv:goalOutcome` link → 0 warnings

   **Rule 10: claim no rationale (Info, research)**
   - Positive: `res:Claim` with no `res:rationale` → 1 info
   - Negative: `res:Claim` with `res:rationale "..."` → 0 infos

   **Important notes for test authors:**
   - The positive test data graphs must ALSO include enough triples to match the rule's `sh:target*` — e.g. for `sh:targetSubjectsOf bpkm:tags`, the object must have a `bpkm:tags` triple
   - When testing basic-pkm rules, the data graph will trigger OTHER existing rules too (e.g. overdue task). Filter assertions to only count results from the specific rule being tested by checking `sh:sourceShape` in the results graph
   - For rules using `sh:targetSubjectsOf rdf:type`, every typed object in the test graph becomes a focus node. Keep test graphs minimal.
   - Use the knowledge entry: "pyshacl: `allow_warnings=True` means warnings don't affect `conforms`" — check results_graph, not conforms boolean
   - For negative tests of rules that target broad patterns (e.g. titleless), you may still get warnings/infos from OTHER rules on the same NodeShape file. Assert specifically on the sourceShape IRI, not on total counts.

4. **Determine updated EXPECTED_PYSHACL counts** by running pyshacl against each model's seed data + shapes + updated rules and counting results. Key seed data analysis:
   - **basic-pkm**: Existing 1 warning (overdue task). New: 6 infos (empty body on 3 Notes + 3 Concepts that lack `<urn:sempkm:vocab:body>`), possibly 3 infos (concept no definition — but seed concepts DO have skos:definition, so 0 from this rule). Titleless: all basic-pkm seed objects have dcterms:title. Orphan: need to check connectivity. Comma-in-tags: seed tags are arrays, no commas. Duplicate URL: unlikely in seed. **Run pyshacl to get actual counts.**
   - **crm**: Existing 2 warnings. New rules from basic-pkm file won't fire against crm types because titleless/orphan are scoped to basic-pkm types. No new rules in crm.ttl.
   - **zettelkasten**: Existing 2 warnings + 1 info. New: empty body on all 2 FleetingNotes + 3 LiteratureNotes + 3 PermanentNotes + 1 StructureNote = 9 infos.
   - **ppv**: Existing 0 warnings, 0 infos. New: stale project infos (all 4 projects lack dcterms:modified = 4 infos), broken chain warnings (all seed ActionItems have ppv:project, all seed Projects have ppv:goalOutcome → 0 broken chain warnings).
   - **research**: Existing 2 warnings + 2 infos. New: claim no rationale — all 5 seed claims HAVE res:rationale → 0 new infos.

5. **Update `EXPECTED_PYSHACL` dict** in `test_cross_model_validation.py` with the actual counts discovered in step 4. Run `_run_pyshacl()` for each model with the updated rules files to get the exact numbers. **Do not guess — run the tests and adjust.**

6. **Run full test suite** to verify no regressions: `cd backend && .venv/bin/pytest -v`

## Must-Haves

- [ ] Per-rule positive test (rule fires) for all 9 rules
- [ ] Per-rule negative test (rule doesn't fire) for all 9 rules
- [ ] Tests use minimal synthetic data graphs (not seed data)
- [ ] EXPECTED_PYSHACL counts updated to actual values from running pyshacl against seed data with new rules
- [ ] Full test suite passes with zero failures

## Verification

- `cd backend && .venv/bin/pytest tests/test_data_quality_rules.py -v` — ≥18 tests pass
- `cd backend && .venv/bin/pytest tests/test_cross_model_validation.py -v` — all 10 existing tests pass with updated counts
- `cd backend && .venv/bin/pytest` — full suite green

## Inputs

- `models/basic-pkm/rules/basic-pkm.ttl` — T01 output with 5 new validation NodeShapes
- `models/zettelkasten/rules/zettelkasten.ttl` — T01 output with 1 new NodeShape
- `models/ppv/rules/ppv.ttl` — T01 output with 3 new NodeShapes
- `models/research/rules/research.ttl` — T01 output with 1 new NodeShape
- `backend/tests/test_cross_model_validation.py` — existing file with EXPECTED_PYSHACL dict
- `backend/tests/test_basic_pkm_v2.py` — reference pattern for per-rule tests
- Knowledge: "pyshacl: `allow_warnings=True` means warnings don't affect `conforms`" — check results_graph
- Knowledge: "basic-pkm shapes are JSON-LD, not Turtle" — shapes at `.jsonld`, rules at `.ttl`
- Seed data type counts: basic-pkm (3 Notes, 3 Concepts, 3 Persons, 2 Projects, 2 Milestones, 4 Tasks, 4 Events), crm (4 Contacts, 3 Companies, 3 Interactions, 2 Deals), zettelkasten (2 FleetingNotes, 3 LiteratureNotes, 3 PermanentNotes, 1 StructureNote, 3 Sources), research (3 Papers, 5 Claims, 5 Evidence, 2 ResearchQuestions, 1 Argument), ppv (4 Projects, 7 ActionItems, 5 GoalOutcomes, 5 ValueGoals, 3 Pillars, 3 PillarGroups, 4 Reviews)
- All seed Concepts have skos:definition (3/3). All seed Claims have res:rationale (5/5). No commas in seed tags. All seed PPV ActionItems have ppv:project. All seed PPV Projects have ppv:goalOutcome. All seed PPV Projects lack dcterms:modified.

## Expected Output

- `backend/tests/test_data_quality_rules.py` — new test file with ≥18 tests
- `backend/tests/test_cross_model_validation.py` — EXPECTED_PYSHACL dict updated with new counts

## Observability Impact

- **Signals changed:** No new runtime signals. This task adds offline test coverage — the validation rules themselves were added in T01.
- **Inspection surface:** `pytest tests/test_data_quality_rules.py -v` shows individual rule pass/fail status. Each test class name maps to a specific SHACL validation shape.
- **Failure visibility:** A failing test prints the full pyshacl results_text showing which violations fired, their severity, source shape, and focus node — enabling immediate diagnosis.
- **Updated expected counts:** `EXPECTED_PYSHACL` dict in `test_cross_model_validation.py` now reflects new rules firing against seed data. If seed data changes or rules are modified, these counts will need updating — test failures include the full validation report.
