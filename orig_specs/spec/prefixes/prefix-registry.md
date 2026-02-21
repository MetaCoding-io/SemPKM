# Prefix Registry & QName Resolution (v1)

SemPKM provides a Prefix Registry and QName Resolver used consistently across:
- SPARQL editor
- SHACL shape inspection/authoring UX
- View execution/rendering
- UI rendering (tooltips, inspectors, debug panels)

This enables:
- rendering IRIs as compact QNames where possible
- expanding QNames back into full IRIs in editors and specs

---

## 1) Canonical behaviors

### 1.1 IRI → QName rendering
Given an absolute IRI `I`:
- if there exists a prefix mapping `p -> ns` such that `I` starts with `ns`,
  then render `p:local` where `local = I[len(ns):]`.
- If multiple prefixes match, choose the **longest namespace match**, then prefer:
  1) model-provided mapping
  2) user override
  3) SemPKM default

If no mapping applies:
- display label (if available) in normal UI
- show full IRI in hover/details/copy

### 1.2 QName → IRI expansion
Given `p:local`:
- look up `p` in the active registry
- expand to `ns + local`
- reject if prefix `p` is unknown in strict contexts (e.g., query validation)
- allow unknown prefixes in display-only contexts (but do not expand)

### 1.3 Reserved prefixes
SemPKM treats these as reserved and always available (unless explicitly overridden by user):
- `rdf`, `rdfs`, `xsd`, `sh`, `skos`, `dcterms`, `prov`, `schema`

---

## 2) Prefix sources and precedence

SemPKM constructs an **active registry** for a workspace/model context by merging sources in this order:

1) **Model-provided prefixes** (highest precedence)
   - Derived primarily from SHACL prefix declarations (`sh:declare` / `sh:prefixes`)
   - Mental Models are the authoritative place to define expected prefixes.

2) **User overrides**
   - Optional user config file conforming to `sempkm.user-prefixes.v1`
   - Intended for personalization, local conventions, and convenience.

3) **SemPKM defaults** (lowest precedence)
   - Built-in mappings for common vocabularies.

### 2.1 Conflict handling
If the same prefix appears in multiple sources:
- Use the mapping from the highest-precedence source.
- SemPKM MAY warn if:
  - a user override conflicts with a model prefix
  - a model prefix conflicts with SemPKM defaults

---

## 3) Extraction rules for model prefixes (v1)

### 3.1 SHACL-based extraction (preferred)
SemPKM extracts prefixes from SHACL graphs by searching for:
- `sh:prefixes` nodes containing one or more `sh:declare` entries with:
  - `sh:prefix` (string)
  - `sh:namespace` (xsd:anyURI literal)

Models should include these declarations in their `shapes.ttl` so that:
- the SPARQL editor can offer correct prefixes
- view specs can omit redundant prefix boilerplate (optional feature)

### 3.2 Non-SHACL sources (optional)
If a Mental Model includes a dedicated prefix file (future optional), SemPKM may ingest it,
but SHACL declarations are the normative v1 source.

---

## 4) SPARQL editor integration (v1)

### 4.1 Prefix injection (optional feature)
SemPKM MAY auto-inject `PREFIX` declarations in the editor based on the active registry.
This is a UX feature and does not change query semantics.

### 4.2 Execution semantics
When executing a query:
- if the query text includes explicit `PREFIX` lines, those apply
- otherwise, SemPKM MAY execute the query using the active registry mappings
  (implementation choice; must be consistent)

Recommended v1 approach:
- Keep execution explicit: require PREFIX lines in stored views
- Provide an editor convenience action: "Insert prefixes from active model"

---

## 5) Display conventions

- Default UI shows human labels.
- Inspector/debug views show:
  - QName (if available)
  - full IRI (always available on hover/copy)
- Tooltips and edge inspectors should prefer QNames for predicates when available.

---

## 6) Future considerations
- Namespace registries from external sources
- Per-view registry overrides
- Multi-model “workspace registries” that compose multiple models intentionally