# View Parameters and Template Substitution (v1)

This document defines parameter types and how they may be used in view queries.

## Parameter types
Supported parameter types in v1 specs:
- `iri`
- `string`
- `number`
- `boolean`
- `dateTime`

## Query templating rule (v1 default)
In v1, SemPKM permits **template substitution only for parameters of type `iri`**.

Example:
- Param: `contextIri` (type `iri`)
- Query contains: `{{contextIri}}`

### Validation
- If a query contains `{{paramName}}`, then `paramName` MUST be declared as type `iri`.
- Param values must be absolute IRIs (reject otherwise).

### Rationale
This prevents SPARQL injection and keeps the query engine deterministic.

## Non-IRI params (v1)
Non-IRI params may exist for UI usage (filters, toggles) but MUST NOT be substituted into SPARQL query text in v1.

Future versions may add safe binding mechanisms for literal parameters (escaped or parameterized SPARQL).