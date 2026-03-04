# Phase 36: SHACL-AF Rules Support - Research

**Researched:** 2026-03-04
**Domain:** SHACL Advanced Features (SHACL-AF) rules execution via pyshacl
**Confidence:** HIGH

## Summary

Phase 36 adds SHACL-AF rule execution to the existing inference pipeline built in Phase 35. The primary library (pyshacl) already supports SHACL-AF rules via a dedicated `shacl_rules()` function and an `advanced=True` parameter on `validate()`. The architecture is straightforward: extend the manifest schema to declare an optional `rules` entrypoint, load the rules graph alongside shapes/ontology, execute rules via `pyshacl.shacl_rules()`, diff to extract new triples, and feed them into the existing inferred graph + triple state pipeline.

The basic-pkm model should ship at least one SHACL-AF rule demonstrating value beyond what OWL 2 RL already provides. Good candidates include: (1) an `sh:SPARQLRule` that computes `bpkm:topicCount` on Concepts by counting incoming `bpkm:isAbout` links, or (2) an `sh:SPARQLRule` that derives `bpkm:hasRelatedNote` on Projects by traversing `bpkm:relatedProject` inversely (Notes -> Projects). The inverse participant case is already handled by OWL 2 RL `owl:inverseOf`, so rules should target scenarios OWL cannot express.

**Primary recommendation:** Use `pyshacl.shacl_rules()` (not `validate(advanced=True)`) for rule execution to cleanly separate validation from inference, then diff the output graph against the input to extract rule-derived triples.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
No locked decisions -- all decisions delegated to Claude's discretion.

### Claude's Discretion
All decisions in this phase were delegated to Claude. The user trusts the builder to make choices consistent with Phase 35's patterns and the existing codebase conventions. Key areas where Claude has flexibility:

**Example rules for basic-pkm:**
- Claude selects which SHACL rules to ship (relationship expansion, computed properties, or both)
- Claude selects rule syntax (sh:SPARQLRule, sh:TripleRule, or both)
- Claude decides whether rules reuse existing bpkm: properties or introduce new derived-only properties
- Guidance: pick examples that demonstrate SHACL-AF value beyond what OWL 2 RL already handles

**Rule triples in the UI:**
- Claude decides whether rule-derived triples get the same "inferred" badge or a distinct "rule" badge
- Claude decides whether rule triples support dismiss/promote actions (same as OWL triples)
- Claude decides how rules appear in Inference panel entailment type filters
- Claude decides whether rule triples appear in the same inferred column on object read views or separately
- Guidance: prioritize consistency with Phase 35's established UX patterns

**Admin config granularity:**
- Claude decides toggle granularity (single per-model toggle vs per-rule toggles)
- Claude decides how manifest declares rule defaults (extend entailment_defaults vs separate section)
- Claude decides whether admin panel shows rule descriptions
- Claude decides whether to show/hide rules toggle for models without rules
- Guidance: match Phase 35's entailment config UX patterns

**Rules file format:**
- Claude decides file format (JSON-LD for consistency, Turtle for readability, or auto-detect both)
- Claude decides directory structure (dedicated rules/ dir vs inside shapes/)
- Claude decides loading strategy (merge with shapes graph vs separate graph)
- Claude decides where rule metadata lives (in the SHACL file via rdfs:label/rdfs:comment vs manifest.yaml)
- Guidance: keep model authoring simple and consistent with existing entrypoints

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| INF-02 | Mental Models can ship SHACL-AF rules (sh:TripleRule, sh:SPARQLRule) that pyshacl executes with `advanced=True`; inferred triples are stored in `urn:sempkm:inferred` named graph and visible in object views and graph visualization | pyshacl supports both rule types via `shacl_rules()` function; existing inference pipeline handles inferred graph storage and object view display; manifest/loader/registry extensions are well-understood |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pyshacl | >=0.31.0 (installed) | SHACL-AF rule execution | Already in pyproject.toml; only fully open-source validator with complete SHACL-AF support |
| rdflib | (existing) | RDF graph manipulation, diffing | Already used throughout inference pipeline |
| owlrl | 7.1.4 (existing) | OWL 2 RL closure (unchanged) | Phase 35 dependency, runs before SHACL rules |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| pyyaml | (existing) | manifest.yaml parsing | Loading rules entrypoint config |
| pydantic | (existing) | Manifest schema validation | Adding optional `rules` field to ManifestEntrypoints |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `shacl_rules()` | `validate(advanced=True)` | `validate()` focuses on conformance checking; `shacl_rules()` is purpose-built for inference/expansion and returns the enriched graph directly |
| Turtle rules file | JSON-LD rules file | Turtle is more natural for SHACL shapes/rules authoring and far more readable for complex SPARQL CONSTRUCT queries; JSON-LD requires awkward string escaping |

**Installation:**
```bash
# No new dependencies needed -- pyshacl already installed
```

## Architecture Patterns

### Recommended Project Structure
```
models/basic-pkm/
  rules/
    basic-pkm.ttl          # NEW: SHACL-AF rules in Turtle format
  ontology/
    basic-pkm.jsonld        # existing
  shapes/
    basic-pkm.jsonld        # existing
  views/
    basic-pkm.jsonld        # existing
  seed/
    basic-pkm.jsonld        # existing
  manifest.yaml             # modified: add rules entrypoint + shacl_rules entailment default

backend/app/
  inference/
    service.py              # modified: add SHACL rule execution step after OWL 2 RL
    entailments.py          # modified: add "sh:rule" entailment type
    models.py               # unchanged
    router.py               # modified: add sh:rule to filter options
  models/
    manifest.py             # modified: add optional rules field to ManifestEntrypoints
    loader.py               # modified: add rules graph to ModelArchive, support Turtle loading
    registry.py             # modified: add rules named graph to ModelGraphs
```

### Pattern 1: Two-Phase Inference Pipeline
**What:** Run OWL 2 RL closure first, then SHACL-AF rules second, on the same working graph.
**When to use:** Always -- OWL entailments may produce triples that SHACL rules need as input.
**Example:**
```python
# Source: existing inference/service.py pattern extended
async def run_inference(self, entailment_config):
    # Phase A: OWL 2 RL (existing)
    data_graph = await self._load_current_data()
    ontology_graph = await self._load_ontology_graphs()
    working = merge(data_graph, ontology_graph)
    owlrl.DeductiveClosure(owlrl.OWLRL_Semantics).expand(working)
    owl_new = set(working) - set(data_graph) - set(ontology_graph)

    # Phase B: SHACL-AF Rules (NEW)
    if entailment_config.get("shacl_rules", True):
        rules_graph = await self._load_rules_graphs()
        if len(rules_graph) > 0:
            pre_rules = set(working)
            expanded = await asyncio.to_thread(
                pyshacl.shacl_rules,
                working,
                shacl_graph=rules_graph,
                advanced=True,
                iterate_rules=True,
            )
            rule_new = set(expanded) - pre_rules
            # Merge rule-derived triples into working graph
            for t in rule_new:
                working.add(t)

    # Continue with existing diff/classify/filter/store pipeline...
```

### Pattern 2: Rules Graph Loading (Turtle Support)
**What:** Extend `load_archive()` to handle Turtle files for the rules entrypoint.
**When to use:** When the rules entrypoint points to a `.ttl` file.
**Example:**
```python
# Source: extending models/loader.py
def load_rdf_file(file_path: Path) -> Graph:
    """Load an RDF file (JSON-LD or Turtle) based on extension."""
    if not file_path.exists():
        raise FileNotFoundError(f"RDF file not found: {file_path}")

    g = Graph()
    suffix = file_path.suffix.lower()
    if suffix in ('.ttl', '.turtle'):
        g.parse(str(file_path), format="turtle")
    elif suffix in ('.jsonld', '.json'):
        _check_no_remote_context(file_path)
        g.parse(str(file_path), format="json-ld")
    else:
        raise ValueError(f"Unsupported RDF format: {suffix}")
    return g
```

### Pattern 3: Entailment Type Extension
**What:** Add `"sh:rule"` as a new entailment type in the classification system.
**When to use:** For all triples produced by SHACL-AF rules (not OWL 2 RL).
**Example:**
```python
# Source: extending inference/entailments.py
ENTAILMENT_TYPES = [
    "owl:inverseOf",
    "rdfs:subClassOf",
    "rdfs:subPropertyOf",
    "owl:TransitiveProperty",
    "rdfs:domain/rdfs:range",
    "sh:rule",               # NEW
]

MANIFEST_KEY_TO_TYPE = {
    # ... existing ...
    "shacl_rules": "sh:rule",  # NEW
}
```

### Anti-Patterns to Avoid
- **Merging rules into shapes graph:** Keep rules and shapes separate. pyshacl uses shapes for validation constraints; mixing rules in could cause unexpected validation failures or rule misfires during normal validation.
- **Using validate() for rule execution:** `validate()` returns conformance results, not an expanded graph. Use `shacl_rules()` which is purpose-built for the expansion use case.
- **Complex per-rule toggle granularity:** At this stage, a single `shacl_rules` toggle per model is sufficient. Per-rule toggles add manifest complexity without clear user value for a PKM tool.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SHACL rule execution | Custom SPARQL-based rule engine | `pyshacl.shacl_rules()` | Handles sh:order, sh:condition, iterate_rules, all rule types |
| Triple diffing | Manual set operations with bugs | `set(expanded) - set(pre_rules)` | rdflib Graph iteration produces hashable tuples; set diffing is correct and fast |
| Turtle file parsing | Custom parser | `rdflib.Graph.parse(format="turtle")` | Production-grade Turtle parser already in rdflib |
| Blank node filtering | Complex BNode tracking | Reuse existing `isinstance(x, BNode)` filter | Phase 35 already has this pattern |

**Key insight:** pyshacl's `shacl_rules()` handles the full SHACL-AF rules spec including rule ordering, conditions, and iterative execution. Do not attempt to manually process `sh:rule` triples.

## Common Pitfalls

### Pitfall 1: shacl_rules() Modifies the Data Graph
**What goes wrong:** `shacl_rules()` may modify the input data graph in-place depending on the version and parameters.
**Why it happens:** Some versions of pyshacl expand triples directly into the input graph.
**How to avoid:** Snapshot the input graph (`pre_rules = set(working)`) before calling `shacl_rules()`, then diff against the returned graph. Use the returned graph (not the input) for extracting new triples.
**Warning signs:** Triple counts don't match expectations; "new" triples seem to include pre-existing data.

### Pitfall 2: Rule Triples Classified as None by OWL Classifier
**What goes wrong:** `classify_entailment()` returns `None` for rule-derived triples because they don't match any OWL axiom pattern.
**Why it happens:** The existing classifier only checks OWL 2 RL entailment patterns (inverseOf, subClassOf, etc.). SHACL rule triples don't match these.
**How to avoid:** Skip `classify_entailment()` for rule-derived triples. Tag them directly as `"sh:rule"` entailment type.
**Warning signs:** Rule-derived triples silently dropped during classification step.

### Pitfall 3: Turtle File Remote Context Check
**What goes wrong:** The `_check_no_remote_context()` function from `loader.py` only handles JSON-LD files. Calling it on a Turtle file causes a JSON parse error.
**Why it happens:** Turtle format doesn't use `@context`.
**How to avoid:** Only run the remote context check for JSON-LD files, not Turtle files.
**Warning signs:** `json.JSONDecodeError` when loading Turtle rules files.

### Pitfall 4: Rules Depending on OWL-Inferred Triples
**What goes wrong:** A SHACL rule that references triples only available after OWL 2 RL expansion produces no results.
**Why it happens:** If rules run before or independently of OWL closure, the working graph lacks inverse/subclass triples.
**How to avoid:** Run OWL 2 RL closure FIRST, then SHACL rules on the expanded graph.
**Warning signs:** Rules produce fewer triples than expected; rules targeting inverse properties yield nothing.

### Pitfall 5: Named Graph Collision for Rules
**What goes wrong:** Using the same named graph IRI pattern for rules as other artifacts causes data overlap.
**Why it happens:** `ModelGraphs` already defines ontology/shapes/views/seed graph IRIs.
**How to avoid:** Add a dedicated `rules` property to `ModelGraphs`: `urn:sempkm:model:{modelId}:rules`.
**Warning signs:** Rules triples appearing in shapes queries or vice versa.

## Code Examples

### Example 1: SHACL-AF SPARQLRule (Turtle format for basic-pkm)
```turtle
# Source: W3C SHACL-AF spec pattern, adapted for basic-pkm ontology
@prefix sh:    <http://www.w3.org/ns/shacl#> .
@prefix bpkm:  <urn:sempkm:model:basic-pkm:> .
@prefix rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd:   <http://www.w3.org/2001/XMLSchema#> .

# Rule: Derive bpkm:hasRelatedNote inverse on Projects
# When a Note has bpkm:relatedProject pointing to a Project,
# infer that the Project bpkm:hasRelatedNote the Note.
# This is NOT covered by OWL inverseOf (no inverse declaration exists).
bpkm:ProjectRelatedNoteRule
    a sh:NodeShape ;
    sh:targetClass bpkm:Note ;
    sh:rule [
        a sh:SPARQLRule ;
        sh:order 0 ;
        rdfs:label "Derive hasRelatedNote inverse" ;
        rdfs:comment "Projects gain hasRelatedNote links from Notes' relatedProject" ;
        sh:prefixes bpkm:PrefixDeclarations ;
        sh:construct """
            CONSTRUCT {
                ?project bpkm:hasRelatedNote $this .
            }
            WHERE {
                $this bpkm:relatedProject ?project .
            }
        """ ;
    ] .

# Prefix declarations for SPARQL rules
bpkm:PrefixDeclarations
    a owl:Ontology ;
    sh:declare [
        sh:prefix "bpkm" ;
        sh:namespace "urn:sempkm:model:basic-pkm:"^^xsd:anyURI ;
    ] .
```

### Example 2: Calling pyshacl.shacl_rules()
```python
# Source: pyshacl README + GitHub docs
import asyncio
import pyshacl
from rdflib import Graph

async def execute_shacl_rules(working_graph: Graph, rules_graph: Graph) -> set:
    """Execute SHACL-AF rules and return only new triples."""
    pre_triples = set(working_graph)

    expanded = await asyncio.to_thread(
        pyshacl.shacl_rules,
        working_graph,
        shacl_graph=rules_graph,
        advanced=True,
        iterate_rules=True,  # iterate until steady state
    )

    # Diff: only triples added by rules
    new_triples = set(expanded) - pre_triples
    return new_triples
```

### Example 3: Extended ManifestEntrypoints
```python
# Source: extending existing models/manifest.py
class ManifestEntrypoints(BaseModel):
    ontology: str = "ontology/{modelId}.jsonld"
    shapes: str = "shapes/{modelId}.jsonld"
    views: str = "views/{modelId}.jsonld"
    seed: str | None = "seed/{modelId}.jsonld"
    rules: str | None = None  # NEW: optional rules entrypoint
```

### Example 4: Extended ModelArchive
```python
# Source: extending existing models/loader.py
@dataclass
class ModelArchive:
    manifest: ManifestSchema
    ontology: Graph
    shapes: Graph
    views: Graph
    seed: Graph | None
    rules: Graph | None  # NEW
```

### Example 5: Extended ModelGraphs
```python
# Source: extending existing models/registry.py
@dataclass
class ModelGraphs:
    model_id: str

    @property
    def rules(self) -> str:
        return f"urn:sempkm:model:{self.model_id}:rules"

    @property
    def all_graphs(self) -> list[str]:
        return [self.ontology, self.shapes, self.views, self.seed, self.rules]
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `validate(advanced=True)` for rules | `shacl_rules()` dedicated function | pyshacl 0.27.0 (Oct 2024) | Cleaner separation of validation vs inference |
| Manual SPARQL-based rule execution | SHACL-AF standard rules | W3C SHACL-AF spec (2017, stable) | Declarative, portable, tool-agnostic rules |

**Deprecated/outdated:**
- Nothing relevant deprecated. pyshacl maintains backward compatibility with `advanced=True` on `validate()`, but `shacl_rules()` is the preferred API for rule expansion.

## Open Questions

1. **Does `shacl_rules()` accept `iterate_rules` parameter?**
   - What we know: README documents it as a parameter. pyshacl 0.27.0 introduced "SHACL Rules Expander Mode."
   - What's unclear: Exact function signature for the installed version (>=0.31.0).
   - Recommendation: Test at implementation time; fall back to single-pass if parameter not accepted. For PKM-scale data, single-pass is likely sufficient.

2. **bpkm:hasRelatedNote property existence**
   - What we know: The ontology declares `bpkm:relatedProject` (Note -> Project) but no inverse.
   - What's unclear: Whether to add `bpkm:hasRelatedNote` to the ontology as a formal property or let it exist only as a rule-derived predicate.
   - Recommendation: Add it to the ontology as an `owl:ObjectProperty` with domain Project and range Note, but WITHOUT `owl:inverseOf` (since the rule handles it, not OWL). This gives the property a label for the UI.

## Sources

### Primary (HIGH confidence)
- [W3C SHACL Advanced Features](https://www.w3.org/TR/shacl-af/) - Rule types (sh:SPARQLRule, sh:TripleRule), sh:order, sh:condition
- [pyshacl GitHub README](https://github.com/RDFLib/pySHACL) - `shacl_rules()` function, `advanced=True`, `iterate_rules`
- [pyshacl FEATURES.md](https://github.com/RDFLib/pySHACL/blob/master/FEATURES.md) - Full SHACL-AF support confirmation

### Secondary (MEDIUM confidence)
- [pyshacl 0.27.0 Release](https://github.com/RDFLib/pySHACL/releases/tag/v0.27.0) - SHACL Rules Expander Mode introduction
- [pyshacl PyPI](https://pypi.org/project/pyshacl/) - Version info

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - pyshacl already installed and used; SHACL-AF support confirmed by official docs
- Architecture: HIGH - Direct extension of Phase 35 patterns; all integration points identified in codebase
- Pitfalls: HIGH - Based on direct code analysis of existing pipeline + pyshacl API docs
- Example rules: MEDIUM - Rule syntax verified against W3C spec; specific bpkm property choices are recommendations

**Research date:** 2026-03-04
**Valid until:** 2026-04-04 (stable spec, stable library)
