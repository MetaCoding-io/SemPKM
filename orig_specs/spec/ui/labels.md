# Label Service and Display Conventions (v1)

SemPKM provides a label service to render IRIs in a human-friendly way across the UI.

## Global label precedence (v1 default)
When rendering an object IRI, SemPKM attempts these predicates in order:

1. `dcterms:title`
2. `rdfs:label`
3. `skos:prefLabel`
4. `schema:name`
5. Fallback: derive from IRI (last path segment; decode safe characters)

## Mental Model overrides
Mental Models may override label precedence per class/type.

Example override conceptually:
- For `ex:Person`, prefer `rdfs:label`
- For `ex:Concept`, prefer `skos:prefLabel`

## Display behavior
- UI typically shows the resolved label.
- UI should allow users to:
  - copy full IRI
  - view IRI on hover or in a details panel
- When no label exists, fallback should be stable and deterministic.