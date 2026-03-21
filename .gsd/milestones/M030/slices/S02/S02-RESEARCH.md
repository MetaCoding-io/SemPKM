# S02: Data Quality Rules (9 new SHACL-AF rules) — Research

**Date:** 2026-03-20
**Status:** Complete

## Summary

S02 adds 9 new SHACL-AF SPARQLConstraint validation rules across the 5 Mental Model `rules/*.ttl` files. All 9 rules follow the identical pattern proven by the 11 existing rules in M011 — a `sh:NodeShape` with `sh:severity` and `sh:sparql` containing a `sh:SPARQLConstraint` with `sh:select`, `sh:message`, and `sh:prefixes`. Per D153, each validation rule lives on its own dedicated NodeShape, separate from inference rules.

Per D278, cross-model rules (comma-in-tags, titleless objects, orphan objects) are attached to basic-pkm's rules file with broad target patterns. The remaining 6 rules go into their respective model-specific rules files.

This is straightforward work applying well-established patterns. The main risk is getting the SPARQL correct for each rule and ensuring the existing pyshacl warning/info counts in `test_cross_model_validation.py` are updated to reflect the new rules.

## Recommendation

**Write all 9 rules as Turtle additions to existing `rules/*.ttl` files. Write one test file `test_data_quality_rules.py` with targeted tests per rule.**

Build order:
1. Write the 3 cross-model rules in `basic-pkm/rules/basic-pkm.ttl` (comma-in-tags, titleless, orphan)
2. Write the model-specific rules in their respective files (stale project/goal, PPV broken chain, concept no definition, claim no rationale, empty body, duplicate URL)
3. Write `test_data_quality_rules.py` with per-rule tests using minimal test data graphs
4. Update expected counts in `test_cross_model_validation.py` to reflect new rules firing against existing seed data
5. Run all tests to confirm

## Implementation Landscape

### Key Files

- `models/basic-pkm/rules/basic-pkm.ttl` — Currently has 2 inference rules + 1 validation rule (overdue task). **Add 3 cross-model rules:** comma-in-tags, titleless objects, orphan objects. Also add: empty body (targets Note, Concept), concept with no definition. The PrefixDeclarations need `schema`, `skos`, `foaf`, `rdfs` prefixes added.

- `models/ppv/rules/ppv.ttl` — Currently has 2 inference rules, 0 validation rules. **Add 2 rules:** stale project/goal (dcterms:modified > 30 days), PPV broken chain (ActionItem/Project not linked to GoalOutcome/Pillar). Needs a PrefixDeclarations block (currently only has ppv prefix — needs `dcterms`, `xsd`).

- `models/research/rules/research.ttl` — Currently has 4 validation rules. **Add 1 rule:** claim with no rationale.

- `models/crm/rules/crm.ttl` — No new rules needed (stale contact already exists).

- `models/zettelkasten/rules/zettelkasten.ttl` — No new rules needed directly, but empty body rule for FleetingNote/LiteratureNote/PermanentNote/StructureNote could go here OR in basic-pkm with broad targeting. **Decision: put empty body for zk note types in zettelkasten.ttl** alongside existing rules.

- `backend/tests/test_data_quality_rules.py` — **New file.** Per-rule tests following the `test_pyshacl_no_warning_for_done_or_future_tasks` pattern from `test_basic_pkm_v2.py`: create minimal data graph → load rules → run pyshacl → assert warnings/infos.

- `backend/tests/test_cross_model_validation.py` — **Update expected counts.** The `EXPECTED_PYSHACL` dict has `(warnings, infos)` per model. After adding new rules, these counts change because some existing seed data will trigger the new rules.

### Rule Details

**Rule 1: Comma-in-tags (Warning) — `basic-pkm/rules/basic-pkm.ttl`**
- Target: `rdfs:Resource` (broad — only objects with `bpkm:tags` will match the WHERE)
- SPARQL: `SELECT $this ?tagVal WHERE { $this bpkm:tags ?tagVal . FILTER(CONTAINS(STR(?tagVal), ",")) }`
- Message: "Tag value contains a comma — split into individual tags."
- Note: `schema:keywords` is not used in any current model shapes (grep confirmed no hits). Only `bpkm:tags` exists. The CRM model also uses `bpkm:tags` (cross-namespace reference). Target `sh:targetSubjectsOf bpkm:tags` instead of `rdfs:Resource` for efficiency.

**Rule 2: Empty body (Info) — split across `basic-pkm/rules/basic-pkm.ttl` and `zettelkasten/rules/zettelkasten.ttl`**
- In basic-pkm: target `bpkm:Note` and `bpkm:Concept`
- In zettelkasten: target `zk:FleetingNote`, `zk:LiteratureNote`, `zk:PermanentNote`, `zk:StructureNote`
- Body predicate: `<urn:sempkm:vocab:body>` (the `sempkm:body` predicate used by body_set.py)
- SPARQL: `SELECT $this WHERE { FILTER NOT EXISTS { $this <urn:sempkm:vocab:body> ?body } }`
- Note: Need to verify exact body predicate IRI. The codebase uses `urn:sempkm:vocab:body` based on the `sempkm:` prefix being `urn:sempkm:vocab:`.
- **Seed data impact:** Seed Notes/Concepts don't have bodies set (body is set via body.set command, not in seed JSON-LD). This means ALL seed notes/concepts will trigger this rule. This is fine — it's sh:Info severity, and it proves the rule works. But the expected counts in `test_cross_model_validation.py` will increase significantly.

**Rule 3: Duplicate URL on same type (Info) — `basic-pkm/rules/basic-pkm.ttl`**
- Complex — needs to find two objects of the same type sharing the same `schema:url` or `dcterms:source`.
- `schema:url` is used in basic-pkm (Person, Concept) and zettelkasten (Source) shapes.
- `dcterms:source` is used in zettelkasten (LiteratureNote) shapes.
- This rule is tricky because SPARQLConstraint `$this` binds to one focus node but the violation involves two nodes.
- **Recommendation: Defer or simplify.** A SPARQLConstraint that compares pairs of objects is awkward in SHACL-AF because `$this` is per-focus-node. The rule would need to check "does another object of my same type share my URL?" which is valid but produces N warnings (one per object sharing the URL), not 1.
- Pattern: `SELECT $this ?url WHERE { $this schema:url ?url . $this a ?type . ?other a ?type . ?other schema:url ?url . FILTER(?other != $this) }`
- Target: `sh:targetSubjectsOf <http://schema.org/url>` — only objects with URLs.

**Rule 4: Titleless objects (Warning) — `basic-pkm/rules/basic-pkm.ttl`**
- Target: `sh:targetSubjectsOf rdf:type` — broad, matches anything typed.
- SPARQL: Check that none of `dcterms:title`, `skos:prefLabel`, `foaf:name`, `rdfs:label` exist.
- This is cross-model — basic-pkm placement per D278.
- **Seed data impact:** All seed objects have `dcterms:title`. No false positives expected.
- Need full IRIs in SPARQL (not prefixed) or add prefixes to PrefixDeclarations.

**Rule 5: Orphan objects (Info) — `basic-pkm/rules/basic-pkm.ttl`**
- Target: `sh:targetSubjectsOf rdf:type` — broad.
- SPARQL: `NOT EXISTS { $this ?p ?other . ?other a ?anyType }` AND `NOT EXISTS { ?other2 ?p2 $this . ?other2 a ?anyType2 }` — no typed edges in either direction.
- Per D282: implement as SHACL-AF, monitor performance.
- **Seed data impact:** Some seed objects may be orphans. Need to check.
- **Performance note:** The double NOT EXISTS scans the full graph. On seed data (~50-100 triples per model) this is instant. Performance concern is for production with 1000+ objects — measured as acceptable in S01 (0.266s for validation).

**Rule 6: Stale project/goal (Info) — `ppv/rules/ppv.ttl`**
- Targets: `ppv:Project` and separately `bpkm:Project` (in basic-pkm rules).
- Uses K001 pattern: `STRDT(SUBSTR(STR(NOW()), 1, 10), xsd:date)` for today's date.
- SPARQL: Check `dcterms:modified < (today - 30 days)`. But rdflib doesn't support date subtraction (K001). Use: `BIND(STRDT(SUBSTR(STR(NOW()), 1, 10), xsd:date) AS ?today)` then construct 30-days-ago manually... this is actually hard.
- **Alternative (simpler):** Use NOT EXISTS for dcterms:modified, or check if modified date year is before current year minus 1. Actually, the K001 pattern works for comparing dates — the issue is duration subtraction. Can use: compare the modified date string directly: `FILTER(?mod < "2026-02-18"^^xsd:date)` won't work because the date is dynamic.
- **Best approach:** Construct a 30-day-ago date using SUBSTR arithmetic on NOW(): extract year/month/day, subtract 30 from day (handling month rollover is impossible in pure SPARQL without extensions). 
- **Pragmatic approach:** Check `dcterms:modified` exists and is older than a static threshold. Since rdflib can't do date arithmetic, use the same "just check it exists" pattern used for stale contacts (crm.ttl), with a TODO for future date arithmetic. OR: use `BIND(STRDT(CONCAT(SUBSTR(STR(NOW()), 1, 8), "01"), xsd:date) AS ?monthAgo)` — approximate 30 days as "before the 1st of this month". Not great.
- **Final decision:** Follow the crm:StaleContactValidationShape pattern. Simply check: project has status active/in-progress but dcterms:modified is more than 30 days old. Since we CAN compare dates (xsd:date < xsd:date works in rdflib), we just need to construct "30 days ago" as a date. We can use: extract year+month from NOW(), subtract 1 from month, handle January→December rollover. This is ugly but workable. **Simplest viable: just check modified exists and do a rough comparison.** Actually, the overdue task rule proves `?dueDate < ?today` works in rdflib with xsd:date. The problem from K001 is only duration subtraction. We can hardcode a comparison like `?mod < ?threshold` where threshold is computed. BUT we can't compute 30-days-ago dynamically in SPARQL without duration math. **Use a SavedQuery-style workaround or accept the limitation.** For v1, let's check if dcterms:modified is older than the beginning of the current month (approximate): `BIND(STRDT(CONCAT(SUBSTR(STR(NOW()),1,8), "01"), xsd:date) AS ?threshold)` — this gives us "the 1st of this month" which is roughly 30 days ago (varies 28-31). Good enough for an info-severity nudge.

**Rule 7: PPV broken chain (Warning) — `ppv/rules/ppv.ttl`**
- Target: `ppv:ActionItem` and `ppv:Project` (separate NodeShapes).
- ActionItem chain: `ppv:project` → Project → `ppv:goalOutcome` → GoalOutcome. Missing = broken.
- Simplest check: ActionItem has no `ppv:project`, OR its project has no `ppv:goalOutcome`.
- Actually, the simplest meaningful check: ActionItem has no `ppv:project` link at all. That's the most common break.
- For Project: no `ppv:goalOutcome` link.
- SPARQL for ActionItem: `SELECT $this WHERE { FILTER NOT EXISTS { $this ppv:project ?proj } }`
- SPARQL for Project: `SELECT $this WHERE { FILTER NOT EXISTS { $this ppv:goalOutcome ?go } }`

**Rule 8: Concept with no definition (Info) — `basic-pkm/rules/basic-pkm.ttl`**
- Target: `bpkm:Concept`
- SPARQL: `SELECT $this WHERE { FILTER NOT EXISTS { $this skos:definition ?def } }`
- Straightforward NOT EXISTS pattern.

**Rule 9: Research claim with no rationale (Info) — `research/rules/research.ttl`**
- Target: `res:Claim`
- SPARQL: `SELECT $this WHERE { FILTER NOT EXISTS { $this res:rationale ?rat } }`
- Straightforward NOT EXISTS pattern.

### PrefixDeclarations Updates

Each rules file has its own PrefixDeclarations. New rules need additional prefixes:

- `basic-pkm.ttl` PrefixDeclarations: Add `schema`, `skos`, `foaf`, `rdfs`, `rdf` sh:declare entries for cross-model rules.
- `ppv.ttl` PrefixDeclarations: Add `dcterms`, `xsd`, `bpkm` sh:declare entries for stale project rule.
- `research.ttl` PrefixDeclarations: Already has `res` — sufficient for claim no-rationale.
- `zettelkasten.ttl` PrefixDeclarations: Already has `zk` — add `sempkm` for body predicate if needed, but can use full IRI in SPARQL instead.

### Expected Count Updates

After adding rules, existing seed data will trigger some of them. Need to audit:

- **basic-pkm seed:** 4 Tasks, 2 Milestones, 2 Projects, 2 Persons, 2 Notes, 2 Concepts. Notes/Concepts likely have no body → empty body fires. Concepts likely have no `skos:definition` → concept-no-definition fires. Check for comma-in-tags and titleless (unlikely — seed is well-formed).
- **crm seed:** 2 Contacts, 2 Companies, 2 Interactions, 2 Deals. All have `bpkm:tags` — need to check for commas.
- **zettelkasten seed:** FleetingNote, LiteratureNote, PermanentNote, StructureNote, Source. Likely no bodies → empty body fires.
- **research seed:** Claims, Evidence, Papers, ResearchQuestion, Argument. Claims may lack rationale.
- **ppv seed:** Check if Projects have goalOutcome, ActionItems have project link.

The test file `test_data_quality_rules.py` should test each rule in isolation with synthetic data to avoid coupling to seed data contents. The `test_cross_model_validation.py` updates are a separate concern — update the expected counts to match whatever the seed data actually produces.

### Build Order

1. **Write rules in basic-pkm.ttl** (comma-in-tags, titleless, orphan, empty body for Note/Concept, concept no definition) — 5 validation NodeShapes + PrefixDeclarations update
2. **Write rules in zettelkasten.ttl** (empty body for 4 zk note types) — 1 validation NodeShape (can target multiple types via SPARQL UNION or use `sh:targetClass` per type — SPARQL UNION in one shape is simpler)
3. **Write rules in ppv.ttl** (stale project/goal, broken chain) — 3-4 validation NodeShapes + PrefixDeclarations update
4. **Write rule in research.ttl** (claim no rationale) — 1 validation NodeShape
5. **Write test_data_quality_rules.py** — per-rule tests with synthetic data
6. **Update test_cross_model_validation.py** — adjust EXPECTED_PYSHACL counts
7. **Run tests** — `cd backend && .venv/bin/pytest tests/test_data_quality_rules.py tests/test_cross_model_validation.py -v`

### Verification Approach

1. **Per-rule isolation test:** Create minimal data graph with violation, run pyshacl, assert warning/info fires.
2. **Negative test:** Create data graph WITHOUT violation, run pyshacl, assert NO warning/info fires.
3. **Cross-model regression:** Run existing `test_cross_model_validation.py` with updated expected counts.
4. **Full test suite:** `cd backend && .venv/bin/pytest` — all existing tests still pass.

## Constraints

- SPARQL date arithmetic limited by rdflib (K001) — stale project/goal rule uses approximate "1st of this month" threshold instead of exact 30-day window.
- Each validation rule must be on its own NodeShape (D153) — cannot mix validation rules on inference-rule NodeShapes.
- Cross-model rules in basic-pkm.ttl must use full IRIs or add prefixes to PrefixDeclarations for non-bpkm namespaces.
- `schema:keywords` is not used in any current model — comma-in-tags rule only needs to target `bpkm:tags`.
- Body predicate is `urn:sempkm:vocab:body` — must use full IRI in SPARQL since sempkm vocab prefix varies.

## Common Pitfalls

- **pyshacl `$this` binding with `sh:targetSubjectsOf`** — When using `sh:targetSubjectsOf` as the target, `$this` binds to every subject that has the specified predicate. If the predicate is very common (like `rdf:type`), the rule runs against every typed resource. Keep the WHERE clause efficient.
- **Full IRIs vs prefixes in SPARQL** — The `sh:prefixes` declaration must include every prefix used in the SPARQL string. Missing prefixes cause silent failures (pyshacl can't resolve them). Use full IRIs when in doubt.
- **Seed data triggering new rules** — New info-severity rules (empty body, concept no definition, orphan) will fire against existing seed data. This changes the expected counts in `test_cross_model_validation.py`. Must audit seed data to get correct counts.
- **Duplicate URL rule produces N warnings** — One per object sharing the URL, not one per duplicate pair. Accept this behavior or skip the rule if confusing.

## Open Risks

- **Orphan object rule false positives on seed data** — Seed objects are interconnected via edges set in seed JSON-LD, but the body predicate and some metadata predicates (dcterms:created, dcterms:modified) create typed connections to literal values, not other objects. The orphan rule must check for edges to OTHER typed objects, not just any triple.
- **Empty body rule triggers on ALL seed objects** — Bodies are set via the `body.set` command, not in seed data. Every Note/Concept/FleetingNote etc. in seed data will trigger the empty-body info. This is correct behavior but changes test counts significantly.
