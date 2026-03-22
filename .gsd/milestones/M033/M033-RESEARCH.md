# M033 Research Summary

Federated SPARQL, New View Renderers, App Catalog & Deployment Overhaul — 7 feature areas spanning triplestore layer, view system, graph visualization, app platform, and deployment infrastructure.

## Key Findings
- `scope_to_current_graph()` regex-based FROM injection is the #1 risk — will mangle SERVICE clauses
- RDF4J 5.0.1 natively supports SPARQL 1.1 SERVICE — backend just needs to not break queries
- ViewSpecService has clean extension points for Calendar + Map renderers
- bpkm:Event has schema:startDate/endDate — calendar data exists in the model
- No geo data exists in any model — Map view needs ontology additions
- Isometric should be a custom Cytoscape layout (2D projection), NOT CSS 3D transforms
- 11 app manifests with rich metadata for catalog; screenshot capture infra exists
- Deployment design doc (566 lines) is thorough and approved
- Recommended 6-phase slice ordering: prove federation first, then parallel renderers, then catalog, small features, deployment last
