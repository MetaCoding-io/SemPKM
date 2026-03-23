---
estimated_steps: 8
estimated_files: 7
skills_used: []
---

# T01: Quadrant framework types — SWOT, BCG, Ansoff, Stakeholder Map, Risk Matrix

**Slice:** S04 — Extended Framework Library
**Milestone:** M036

## Description

Add 5 new quadrant-based framework types to the `business-planning` model archive. Each framework has a container class (subclassing `gist:Collection`) and an item class (subclassing `bp:QuadrantItem`), with two 2-value `sh:in` axis properties that the existing `_detect_quadrant_axes()` will auto-discover. Extend `_quadrant_label()` from a single Eisenhower dict to a multi-framework dispatch, and add keyword preferences so `_detect_quadrant_axes()` assigns x/y correctly for each framework.

## Steps

1. **Add 10 OWL classes to ontology JSON-LD.** 5 container types (bp:SWOTAnalysis, bp:BCGMatrix, bp:AnsoffMatrix, bp:StakeholderMap, bp:RiskMatrix — each subclassing gist:Collection) and 5 item types (bp:SWOTItem, bp:BCGItem, bp:AnsoffItem, bp:StakeholderItem, bp:RiskItem — each subclassing bp:QuadrantItem). Add ~10 axis properties: bp:swotNature (internal/external), bp:swotValence (positive/negative), bp:marketGrowth (high/low), bp:marketShare (high/low), bp:marketNovelty (existing/new), bp:productNovelty (existing/new), bp:stakeholderPower (high/low), bp:stakeholderInterest (high/low), bp:riskLikelihood (high/low), bp:riskImpact (high/low). Add container-linking properties (bp:belongsToSWOT, bp:belongsToBCG, etc.) and description properties. Update the ontology description string.

2. **Add 10+ NodeShapes to shapes JSON-LD.** For each container: shape with title, description, dcterms:created. For each item: shape with title, two axis properties (each with `sh:in` constraining to exactly 2 values), belongsTo relation, dcterms:created. Use PropertyGroups (BasicInfo, Classification, Relationships, Metadata) following the Eisenhower pattern exactly. The axis `sh:in` values are critical — they must have exactly 2 entries so `_detect_quadrant_axes()` picks them up.

3. **Add ~15 ViewSpecs to views JSON-LD.** For each item type: one ViewSpec with `sempkm:rendererType: "quadrant"` and one with `sempkm:rendererType: "table"`. For each container type: one table ViewSpec. Follow the exact format of the existing Eisenhower ViewSpecs.

4. **Add seed data.** For each framework: 1 container + 2–3 items spanning different quadrants. ~15 new seed entities total. Use realistic labels (e.g., SWOT: "Strong brand awareness" in Strengths, "Rising material costs" in Threats).

5. **Add 10 icon entries to manifest.yaml.** One entry per new type. Use distinct Lucide icons: SWOT (compass), BCG (pie-chart), Ansoff (expand), Stakeholder (users), Risk (alert-triangle), plus matching icons for items.

6. **Restructure `_EISENHOWER_QUADRANT_LABELS` → `_QUADRANT_LABELS`.** Change from a single flat dict to a nested dict keyed by framework identifier. The `_quadrant_label()` method derives the framework key from `x_name` and `y_name` (e.g., x_name contains "urgency" → "eisenhower", x_name contains "nature" or "swot" → "swot"). Fallback to generic label if framework key not found.

   Framework label mappings:
   - **SWOT:** (internal,positive)→Strengths, (external,positive)→Opportunities, (internal,negative)→Weaknesses, (external,negative)→Threats
   - **BCG:** (high,high)→Stars, (low,high)→Question Marks, (high,low)→Cash Cows, (low,low)→Dogs
   - **Ansoff:** (existing,existing)→Market Penetration, (existing,new)→Market Development, (new,existing)→Product Development, (new,new)→Diversification
   - **Stakeholder:** (high,high)→Manage Closely, (low,high)→Keep Satisfied, (high,low)→Keep Informed, (low,low)→Monitor
   - **Risk:** (high,high)→Critical, (low,high)→Monitor, (high,low)→Mitigate, (low,low)→Accept

7. **Extend `_detect_quadrant_axes()` keyword preferences.** Add keyword pairs so x/y assignment is correct: ("nature","valence") for SWOT, ("growth","share") for BCG, ("power","interest") for Stakeholder, ("likelihood","impact") for Risk. For Ansoff, use ("market","product") — since `marketNovelty` starts with "market" and `productNovelty` starts with "product", keyword matching should work. Keep existing ("urgency","importance") for Eisenhower. The keyword matching loop needs to check multiple pairs, not just urgency/importance.

8. **Add ~10 unit tests to `test_quadrant.py`.** In `TestQuadrantLabel`: tests for SWOT all-4, BCG high/high→Stars, Ansoff existing/new→Market Development, Stakeholder high/low→Keep Informed, Risk low/low→Accept. In `TestDetectQuadrantAxes`: test for SWOT keyword preference (nature→x, valence→y), test for BCG keywords (growth→x, share→y).

## Must-Haves

- [ ] 5 container + 5 item classes in ontology with correct subclass hierarchy
- [ ] 10 axis properties with rdfs:domain pointing to the correct item type
- [ ] 10 NodeShapes in shapes file with `sh:in` constraints having exactly 2 values each
- [ ] 15 ViewSpecs — quadrant + table for each item type, table for each container
- [ ] ~15 seed entities spanning different quadrants per framework
- [ ] 10 icon entries in manifest
- [ ] `_QUADRANT_LABELS` restructured as nested dict with 6 framework entries (Eisenhower + 5 new)
- [ ] `_detect_quadrant_axes()` keyword loop extended for all 6 frameworks
- [ ] `_quadrant_label()` dispatch logic updated to derive framework key from axis names
- [ ] ~10 new unit tests passing
- [ ] Existing 28 tests still pass

## Verification

- `cd backend && .venv/bin/python -m pytest tests/test_quadrant.py -v` — all tests pass (28 existing + ~10 new)
- `python3 -c "import rdflib; g=rdflib.Graph(); g.parse('models/business-planning/ontology/business-planning.jsonld', format='json-ld'); print(len(g))"` — parses without error, triple count > 49 (was 49 before)
- `python3 -c "import rdflib; g=rdflib.Graph(); g.parse('models/business-planning/shapes/business-planning.jsonld', format='json-ld'); print(len(g))"` — parses without error, triple count > 154

## Inputs

- `models/business-planning/ontology/business-planning.jsonld` — existing ontology (262 lines, 12 classes, 19 properties)
- `models/business-planning/shapes/business-planning.jsonld` — existing shapes (881 lines, 10 NodeShapes)
- `models/business-planning/views/business-planning.jsonld` — existing views (127 lines, 12 ViewSpecs)
- `models/business-planning/seed/business-planning.jsonld` — existing seed (370 lines, 38 entities)
- `models/business-planning/manifest.yaml` — existing manifest (153 lines, 10 icon entries)
- `backend/app/views/service.py` — `_EISENHOWER_QUADRANT_LABELS`, `_detect_quadrant_axes()`, `_quadrant_label()` (lines ~1984–2120)
- `backend/tests/test_quadrant.py` — existing 28 tests (649 lines)

## Expected Output

- `models/business-planning/ontology/business-planning.jsonld` — extended with 10 new classes + 10 axis properties + container-linking properties
- `models/business-planning/shapes/business-planning.jsonld` — extended with 10+ new NodeShapes
- `models/business-planning/views/business-planning.jsonld` — extended with ~15 new ViewSpecs
- `models/business-planning/seed/business-planning.jsonld` — extended with ~15 new seed entities
- `models/business-planning/manifest.yaml` — extended with 10 new icon entries
- `backend/app/views/service.py` — `_QUADRANT_LABELS` restructured, `_quadrant_label()` updated, `_detect_quadrant_axes()` extended
- `backend/tests/test_quadrant.py` — ~10 new tests for label mappings and axis detection
