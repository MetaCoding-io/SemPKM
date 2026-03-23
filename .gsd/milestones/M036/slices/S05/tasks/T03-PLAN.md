---
estimated_steps: 4
estimated_files: 1
skills_used: []
---

# T03: User guide documentation for all business planning frameworks

**Slice:** S05 — Cross-Model Integration, E2E Tests & Documentation
**Milestone:** M036

## Observability Impact

- **No runtime signals change.** This task modifies only a static documentation markdown file.
- **Verification:** `rg "^## 5\. Business Planning" docs/guide/39-mental-model-catalog.md` confirms section exists. `rg "Eisenhower|SWOT|OKR|..." | wc -l` confirms all frameworks are documented (≥15 matches). `wc -l` confirms sufficient content (≥900 lines).
- **Failure visibility:** Missing or incomplete documentation is detectable via the grep/wc checks above. No runtime diagnostics affected.

## Description

Add a comprehensive "5. Business Planning" section to `docs/guide/39-mental-model-catalog.md` documenting all 16 business planning frameworks. Follow the exact format of existing sections (1–4) with type reference tables, field descriptions, and installation instructions. Include custom renderer descriptions, cross-model edge documentation, and SPARQL query examples. Update the Model Comparison table at the bottom.

Per KNOWLEDGE entry "User guide has THREE files that must stay in sync": chapter 39 already exists in all three locations (README.md, index.html, guide.html). The change is within the chapter content, not a new chapter addition — no cross-file sync needed.

## Steps

1. **Read the existing chapter structure** in `docs/guide/39-mental-model-catalog.md` to match heading conventions, table formats, and navigation links used in sections 1–4.

2. **Add section `## 5. Business Planning` before the `## Model Comparison` heading.** Include:
   - Model metadata block: `**Model ID:** business-planning · **Version:** 1.0.0 · **Namespace:** urn:sempkm:model:business-planning:`
   - Overview paragraph explaining the model's purpose (strategic analysis frameworks as typed RDF data with custom visual renderers)
   - **Sub-sections grouped by framework category:**
     - `### Prioritization & Decision-Making` — Eisenhower Matrix (2 types), Decision Matrix (4 types)
     - `### Strategy Analysis` — SWOT Analysis (2 types), Porter's Five Forces (2 types), PESTLE Analysis (2 types), BCG Matrix (2 types), Ansoff Matrix (2 types)
     - `### Business Design` — Business Model Canvas (2 types), Lean Canvas (2 types), Value Chain (2 types)
     - `### Goal Tracking` — OKR (2 types: Objective, Key Result), Balanced Scorecard (2 types)
     - `### Resource Management` — RACI Matrix (2 types), Stakeholder Map (2 types), Risk Matrix (2 types)
   - Each framework sub-section has a type reference table with columns: Field, Type, Required, Description
   - **Custom Renderers section** describing the 4 custom view types (quadrant, bmc, okr, decision-matrix) and what they do
   - **Cross-Model Edges section** listing bp:relatedTask, bp:relatedGoalOutcome, bp:relatedProject and what they link to
   - **SPARQL Query Examples** — 2-3 useful queries (e.g., high-urgency/high-importance Eisenhower items, OKR progress aggregation)
   - Installation instructions (same pattern as other models: Admin > Mental Models > Install, path `/app/models/business-planning`)

3. **Update the Model Comparison table** at the bottom of the file to add a Business Planning row:
   - Types: 32, Focus: Strategic analysis frameworks, Validation rules: 0, Saved queries: 0, Key concept: Multi-framework analysis with custom renderers

4. **Verify the documentation:**
   - `wc -l docs/guide/39-mental-model-catalog.md` — should be ≥ 900 lines (was 608)
   - `rg "^## 5\. Business Planning" docs/guide/39-mental-model-catalog.md` — section exists
   - `rg "Business Planning" docs/guide/39-mental-model-catalog.md | wc -l` — ≥ 5 mentions

## Must-Haves

- [ ] Section "## 5. Business Planning" exists in the document
- [ ] All 16 frameworks documented with type reference tables
- [ ] Custom renderer descriptions (quadrant, bmc, okr, decision-matrix) included
- [ ] Cross-model edges section documents bp:relatedTask, bp:relatedGoalOutcome, bp:relatedProject
- [ ] At least 2 SPARQL query examples
- [ ] Model Comparison table updated with Business Planning row
- [ ] Installation instructions present

## Verification

- `rg "^## 5\. Business Planning" docs/guide/39-mental-model-catalog.md` — section heading found
- `wc -l docs/guide/39-mental-model-catalog.md` — ≥ 900 lines
- `rg "Eisenhower|SWOT|Business Model Canvas|OKR|Decision Matrix|Porter|PESTLE|BCG|Ansoff|Stakeholder|Risk Matrix|Balanced Scorecard|RACI|Value Chain|Lean Canvas" docs/guide/39-mental-model-catalog.md | wc -l` — ≥ 15 (all frameworks mentioned)
- `rg "relatedTask|relatedGoalOutcome|relatedProject" docs/guide/39-mental-model-catalog.md | wc -l` — ≥ 3

## Inputs

- `docs/guide/39-mental-model-catalog.md` — existing chapter with 608 lines covering 4 models
- `models/business-planning/ontology/business-planning.jsonld` — source of truth for type names and properties
- `models/business-planning/shapes/business-planning.jsonld` — source of truth for field constraints (sh:in values, required fields)

## Expected Output

- `docs/guide/39-mental-model-catalog.md` — updated with section 5 (Business Planning) and updated Model Comparison table
