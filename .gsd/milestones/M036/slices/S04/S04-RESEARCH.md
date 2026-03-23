# S04 Research: Extended Framework Library

**Depth:** Light — extending an established model archive with additional types, shapes, views, and seed data using patterns proven in S01-S03. The only backend code change is extending `_quadrant_label()` for framework-specific quadrant cell names.

## Summary

S04 adds ~13 new framework types to the `business-planning` model archive. Five of these (SWOT, BCG, Ansoff, Stakeholder Map, Risk Matrix) reuse the quadrant renderer from S01 — they need types subclassing `bp:QuadrantItem` with two 2-value `sh:in` axis properties, which the existing `_detect_quadrant_axes()` will auto-discover. The remaining ~8 types (Porter's Five Forces, PESTLE, Balanced Scorecard, RACI, Value Chain, Lean Canvas, Gantt-ready project types, Kanban board) use existing renderers (table, kanban) and need only ontology/shapes/views/seed data — zero platform code.

The sole backend change: extend `_quadrant_label()` with framework-specific label dicts (SWOT: "Strengths"/"Weaknesses"/"Opportunities"/"Threats"; BCG: "Stars"/"Cash Cows"/"Question Marks"/"Dogs"; etc.) keyed by axis value tuples, plus keyword hints in `_detect_quadrant_axes()` for proper x/y assignment.

## Recommendation

Split into 3 tasks:
1. **T01 — Quadrant framework types + label mappings** (~40% of work): Add SWOT, BCG, Ansoff, Stakeholder Map, Risk Matrix types to ontology/shapes/views/seed. Extend `_quadrant_label()` and `_detect_quadrant_axes()` keyword preferences. Add icon entries to manifest. Unit tests for new label mappings.
2. **T02 — Non-quadrant framework types** (~40%): Add Porter, PESTLE, Balanced Scorecard, RACI, Value Chain, Lean Canvas types to ontology/shapes/views/seed. These use table/kanban renderers — no backend code changes.
3. **T03 — Verification** (~20%): Run full test suite, verify JSON-LD parses, shapes generate valid forms, quadrant views render for all 5 new types, manifest validates.

## Implementation Landscape

### Current State (post S01-S03)

| File | Lines | Content |
|------|-------|---------|
| `ontology/business-planning.jsonld` | 262 | 12 classes, 19 properties, 7-key `@context` |
| `shapes/business-planning.jsonld` | 881 | 10 NodeShapes (Eisenhower×2, BMC×2, OKR×2, DecisionMatrix×3+Score) |
| `views/business-planning.jsonld` | 127 | 12 ViewSpecs (3 custom renderers + 9 table views) |
| `seed/business-planning.jsonld` | 370 | 38 seed entities across 4 framework types |
| `manifest.yaml` | 132 | 10 type icon entries |

### What S04 Adds

**Quadrant-renderer types (subclass `bp:QuadrantItem`):**

| Type | X-Axis Property | X Values | Y-Axis Property | Y Values | Quadrant Labels |
|------|----------------|----------|----------------|----------|-----------------|
| SWOTItem | bp:swotNature | internal, external | bp:swotValence | positive, negative | Strengths, Weaknesses, Opportunities, Threats |
| BCGItem | bp:marketGrowth | high, low | bp:marketShare | high, low | Stars, Question Marks, Cash Cows, Dogs |
| AnsoffItem | bp:marketNovelty | existing, new | bp:productNovelty | existing, new | Market Penetration, Market Development, Product Development, Diversification |
| StakeholderItem | bp:stakeholderPower | high, low | bp:stakeholderInterest | high, low | Manage Closely, Keep Satisfied, Keep Informed, Monitor |
| RiskItem | bp:riskLikelihood | high, low | bp:riskImpact | high, low | Critical, Monitor, Mitigate, Accept |

Each also needs a container type (bp:SWOTAnalysis, bp:BCGMatrix, etc.) subclassing `gist:Collection`.

**Non-quadrant types (table/kanban renderers):**

| Type | Renderer | Key Properties |
|------|----------|---------------|
| bp:PorterForce | table | bp:forceType (sh:in: 5 forces), bp:intensity, bp:forceDescription |
| bp:PESTLEFactor | table | bp:pestleCategory (sh:in: 6 categories), bp:factorImpact, bp:factorDescription |
| bp:BalancedScorecardItem | table | bp:bscPerspective (sh:in: 4 perspectives), bp:bscMeasure, bp:bscTarget |
| bp:RACIEntry | table | bp:raciRole (sh:in: R/A/C/I), bp:raciPerson, bp:raciActivity |
| bp:ValueChainActivity | table | bp:activityType (sh:in: primary/support), bp:activityCategory |
| bp:LeanCanvasSection | bmc | bp:leanSectionType (sh:in: 9 lean canvas sections) |

Lean Canvas reuses the BMC renderer — it's the same 9-box layout concept.

### Backend Changes

**`backend/app/views/service.py`** — Two changes:

1. **`_EISENHOWER_QUADRANT_LABELS`** → rename to `_QUADRANT_LABELS` and restructure as a nested dict keyed by a framework identifier derived from axis property keywords:

```python
_QUADRANT_LABELS: dict[str, dict[tuple[str, str], str]] = {
    "eisenhower": {  # matched when x has "urgency", y has "importance"
        ("high", "high"): "Do First",
        ("low", "high"): "Schedule",
        ("high", "low"): "Delegate",
        ("low", "low"): "Eliminate",
    },
    "swot": {  # matched when x has "nature", y has "valence"
        ("internal", "positive"): "Strengths",
        ("external", "positive"): "Opportunities",
        ("internal", "negative"): "Weaknesses",
        ("external", "negative"): "Threats",
    },
    "bcg": { ... },
    "ansoff": { ... },
    "stakeholder": { ... },
    "risk": { ... },
}
```

The `_quadrant_label()` method already receives x_name and y_name — it can derive the framework key from those names (e.g., x_name contains "urgency" → "eisenhower"). The fallback to generic labels still works for unrecognized frameworks.

2. **`_detect_quadrant_axes()`** — Add keyword pairs for new frameworks so x/y are assigned correctly:
   - "nature"/"valence" (SWOT)
   - "growth"/"share" (BCG)
   - "market"/"product" (Ansoff — need care since both start with different keywords)
   - "power"/"interest" (Stakeholder)
   - "likelihood"/"impact" (Risk)

### Model Archive Changes

All 4 JSON-LD files grow:
- **ontology**: +~10 classes (5 quadrant containers + 5 quadrant items + ~6 non-quadrant), +~15 properties
- **shapes**: +~13 NodeShapes with PropertyGroups
- **views**: +~15 ViewSpecs (5 quadrant + ~8 table + Lean Canvas BMC)
- **seed**: +~50-60 entities (2-4 per new type)
- **manifest**: +~13 icon entries

### No Changes Needed

- `registry.py` — `quadrant` already registered, `bmc` already registered, `table`/`kanban` are built-in
- `router.py` — elif branches for `quadrant`, `bmc`, `table`, `kanban` already exist
- Frontend JS/CSS — `quadrant.js`, `quadrant.css`, `bmc.js`, `bmc.css` already work generically
- Templates — `quadrant_view.html` renders from data, not hardcoded to Eisenhower

### Constraints

- **Lean Canvas reuses BMC renderer**: The BMC renderer keys on `bp:sectionType` values. Lean Canvas uses different section names. Either: (a) make BMC renderer dispatch on the type to choose section labels, or (b) just use table view for Lean Canvas. Given BMC renderer already renders from `sectionType` field values, Lean Canvas sections with their own `bp:leanSectionType` could just use a table view — simpler and avoids coupling.
  - **Recommendation:** Use table view for Lean Canvas, not BMC renderer. The BMC 9-box layout has specific grid-area assignments hardcoded to BMC section names. Adapting it for Lean Canvas is scope creep.

- **File size**: The shapes file will likely exceed 2000 lines. This is fine — PPV's shapes file is 1059 lines with 11 types, and we're adding ~13 types.

- **Seed data balance**: 2-3 seed entities per type is sufficient for demonstrating the framework. Don't seed full examples (e.g., don't populate all 5 Porter forces for a seed analysis — 2-3 is enough to show the pattern).

### Test Expectations

- Extend `test_quadrant.py` with tests for SWOT, BCG, Ansoff, Stakeholder, and Risk label mappings
- Add a test for the restructured `_QUADRANT_LABELS` dict dispatch
- Verify all JSON-LD files parse: `rdflib.Graph().parse(file, format="json-ld")` for all 4 files
- Verify manifest validates: `parse_manifest()` on manifest.yaml
- Total unit test count: existing 28 + ~8-10 new = ~36-38
