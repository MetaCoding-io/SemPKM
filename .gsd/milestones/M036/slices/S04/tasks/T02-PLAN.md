---
estimated_steps: 6
estimated_files: 5
skills_used: []
---

# T02: Non-quadrant framework types — Porter, PESTLE, BSC, RACI, Value Chain, Lean Canvas

**Slice:** S04 — Extended Framework Library
**Milestone:** M036

## Description

Add 6 non-quadrant framework types to the model archive. These use existing table renderers exclusively — no backend code changes. Each framework gets a container class, an item class, properties with `sh:in` enum constraints, SHACL shapes, table ViewSpecs, seed data, and manifest icon entries.

The frameworks:
- **Porter's Five Forces:** PorterAnalysis + PorterForce (forceType: sh:in 5 forces)
- **PESTLE:** PESTLEAnalysis + PESTLEFactor (pestleCategory: sh:in 6 categories)
- **Balanced Scorecard:** BalancedScorecard + BSCItem (bscPerspective: sh:in 4 perspectives)
- **RACI Matrix:** RACIMatrix + RACIEntry (raciRole: sh:in R/A/C/I)
- **Value Chain:** ValueChain + VCActivity (activityType: sh:in primary/support)
- **Lean Canvas:** LeanCanvas + LeanCanvasSection (leanSectionType: sh:in 9 sections)

## Steps

1. **Add ~12 OWL classes to ontology JSON-LD.** 6 container types (bp:PorterAnalysis, bp:PESTLEAnalysis, bp:BalancedScorecard, bp:RACIMatrix, bp:ValueChain, bp:LeanCanvas — each subclassing gist:Collection) and 6 item types (bp:PorterForce, bp:PESTLEFactor, bp:BSCItem, bp:RACIEntry, bp:VCActivity, bp:LeanCanvasSection — each subclassing bp:FrameworkItem). Add ~12 properties: bp:forceType, bp:forceIntensity, bp:forceDescription, bp:pestleCategory, bp:factorImpact, bp:factorDescription, bp:bscPerspective, bp:bscMeasure, bp:bscTarget, bp:raciRole, bp:raciPerson, bp:raciActivity, bp:activityType, bp:activityCategory, bp:leanSectionType, bp:leanSectionContent. Add belongsTo linking properties for each pair. Update ontology description.

2. **Add ~12 NodeShapes to shapes JSON-LD.** Each container shape: title + description + dcterms:created. Each item shape: title + enum property (sh:in with the framework's categories) + description/detail properties + belongsTo relation + dcterms:created. sh:in values:
   - Porter: "Competitive Rivalry", "Supplier Power", "Buyer Power", "Threat of Substitution", "Threat of New Entry"
   - PESTLE: "Political", "Economic", "Social", "Technological", "Legal", "Environmental"
   - BSC: "Financial", "Customer", "Internal Process", "Learning & Growth"
   - RACI: "Responsible", "Accountable", "Consulted", "Informed"
   - Value Chain: "Primary", "Support"
   - Lean Canvas: "Problem", "Solution", "Key Metrics", "Unique Value Proposition", "Unfair Advantage", "Channels", "Customer Segments", "Cost Structure", "Revenue Streams"

3. **Add ~14 table ViewSpecs to views JSON-LD.** One table view per container type and one per item type. Follow existing format — `sempkm:rendererType: "table"` with `rdfs:label` like "Porter Force Table".

4. **Add seed data.** 2–3 items per framework type = ~15 seed entities. Use realistic examples (e.g., Porter: "Competitive Rivalry" force with "High intensity due to market saturation"). One container per framework with a descriptive title.

5. **Add 12 icon entries to manifest.yaml.** One per new type. Lucide icons: PorterAnalysis (shield), PorterForce (swords), PESTLEAnalysis (globe), PESTLEFactor (tag), BalancedScorecard (gauge), BSCItem (bar-chart-2), RACIMatrix (table-2), RACIEntry (user-check), ValueChain (link), VCActivity (cog), LeanCanvas (layout-template), LeanCanvasSection (file-text).

6. **Update ontology description** to list all framework types now covered by the model.

## Must-Haves

- [ ] 12 new OWL classes with correct subclass hierarchy (containers → gist:Collection, items → bp:FrameworkItem)
- [ ] ~12 new properties with rdfs:domain pointing to correct types
- [ ] 12 NodeShapes with sh:in enum constraints matching the framework categories
- [ ] 14 table ViewSpecs for all new types
- [ ] ~15 seed entities with realistic content
- [ ] 12 icon entries in manifest
- [ ] All 4 JSON-LD files parse via rdflib without error

## Verification

- `python3 -c "import rdflib; g=rdflib.Graph(); g.parse('models/business-planning/ontology/business-planning.jsonld', format='json-ld'); print(f'ontology: {len(g)} triples')"` — parses, triple count significantly higher than T01 output
- `python3 -c "import rdflib; g=rdflib.Graph(); g.parse('models/business-planning/shapes/business-planning.jsonld', format='json-ld'); print(f'shapes: {len(g)} triples')"` — parses without error
- `python3 -c "import rdflib; g=rdflib.Graph(); g.parse('models/business-planning/views/business-planning.jsonld', format='json-ld'); print(f'views: {len(g)} triples')"` — parses without error
- `python3 -c "import rdflib; g=rdflib.Graph(); g.parse('models/business-planning/seed/business-planning.jsonld', format='json-ld'); print(f'seed: {len(g)} triples')"` — parses without error

## Inputs

- `models/business-planning/ontology/business-planning.jsonld` — T01 output (extended with quadrant types)
- `models/business-planning/shapes/business-planning.jsonld` — T01 output (extended with quadrant shapes)
- `models/business-planning/views/business-planning.jsonld` — T01 output (extended with quadrant ViewSpecs)
- `models/business-planning/seed/business-planning.jsonld` — T01 output (extended with quadrant seed data)
- `models/business-planning/manifest.yaml` — T01 output (extended with quadrant icons)

## Expected Output

- `models/business-planning/ontology/business-planning.jsonld` — extended with 12 more classes + ~12 properties
- `models/business-planning/shapes/business-planning.jsonld` — extended with 12 more NodeShapes
- `models/business-planning/views/business-planning.jsonld` — extended with ~14 table ViewSpecs
- `models/business-planning/seed/business-planning.jsonld` — extended with ~15 seed entities
- `models/business-planning/manifest.yaml` — extended with 12 icon entries
