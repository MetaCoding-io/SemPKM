# Mental Model Installation Validation (v1)

This document defines validation rules enforced when installing a Mental Model.

## 1) Schema validation
SemPKM validates:
- `manifest.yaml` against `manifest.schema.json`
- each view/dashboard spec against the view schema(s)
- projection config against its schema (if one exists)

## 2) ID and namespacing rules
- View and dashboard IDs must be stable and unique within the model.
- SemPKM canonicalizes IDs as `modelId::localId` internally.
- Duplicate local IDs within a model are invalid.

## 3) Reference integrity
SemPKM verifies:
- all referenced `viewId` values exist (in dashboards, panels, and registries)
- dashboard registry targets exist
- embedded view parameters match declared params

## 4) Cross-model embedding enforcement (private-by-default)
- Cross-model references are allowed only if the referenced view/dashboard is explicitly exported by the other model.
- If a model references a non-exported item from another model, installation fails (v1 default).

## 5) Renderer compatibility
- All renderers in the model must be supported by the running SemPKM version.
- Unsupported renderers cause install failure.

## 6) Query parameter substitution rule
- Any `{{param}}` template substitution in SPARQL query text must reference a param declared as type `iri`.
- Non-IRI templating in query text is not allowed in v1.

## 7) Optional warnings (non-fatal)
SemPKM may warn (but not fail) on:
- missing labels/help text
- missing dashboards for major object types
- shapes without `sh:order`/`sh:group` when form UX is expected