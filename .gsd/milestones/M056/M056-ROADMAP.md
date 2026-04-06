# M056: Ontology Visualization Overhaul

## Vision
Replace the tree-only TBox view in the Ontology Viewer with a Cytoscape.js hierarchical graph showing all installed model classes with gist as the upper ontology, interactive multi-model filtering, click-to-detail, and persistent graph state across tab switches.

## Slice Overview
| ID | Slice | Risk | Depends | Done | After this |
|----|-------|------|---------|------|------------|
| S01 | TBox Graph API + Hierarchical Rendering + Detail Panel | high | — | ✅ | Open Ontology Viewer → TBox tab shows a hierarchical Cytoscape graph with gist classes at top, model types below. Toggle between graph/tree view. Click a node → detail panel shows class properties and instance count. |
| S02 | Multi-Model Filter + Visual Polish + Persistence | low | S01 | ⬜ | Filter graph by model (checkboxes) → graph updates live. Per-model color coding distinguishes sources. Switch tabs → graph persists. Hover nodes → popovers anchored correctly. |
