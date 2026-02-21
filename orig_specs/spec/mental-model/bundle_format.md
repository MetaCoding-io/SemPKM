# Mental Model Bundle Format (v1)

A Mental Model is distributed as a `.sempkm-model` archive (ZIP internally).

## Required contents
- `manifest.yaml` (required)
- RDF graphs (one or more): ontology, shapes, optional seed
- `views/` with `*.view.yaml` and `*.dashboard.yaml`
- `projections/` projection configs (YAML)
- Optional assets: icons/images/docs

## Installation
SemPKM validates:
- manifest schema
- unique IDs and namespacing rules
- exports policy (private-by-default)
- referenced view/dashboard IDs exist